from __future__ import annotations

from collections import OrderedDict, deque
import hashlib
from typing import Any

from .causal_affordance import AffordanceMemory, effect_signature
from .memory_controller import MemoryGraphController
from .memory_graph import ActionKey
from .runtime import ActionToken, Observation, normalize_frame
from .contextual_quotient import ContextualQuotient


class EffectMemory:
    """Bounded observations of nonterminal action consequences.

    These rows are evidence only. Conflicting successors remain explicit and an
    unchanged raster never becomes a universal no-op claim.
    """

    def __init__(self, limit: int = 2048) -> None:
        if limit < 1:
            raise ValueError("positive effect-memory bound required")
        self.limit = int(limit)
        self.edges: OrderedDict[tuple[str, ActionKey], dict[str, Any]] = OrderedDict()
        self.descriptors: OrderedDict[str, list[int]] = OrderedDict()
        self.catalogs: OrderedDict[str, tuple[ActionKey, ...]] = OrderedDict()
        self.total_observations = 0

    def record(
        self,
        context: str,
        action: ActionKey,
        outcome: str,
        descriptor: str,
        changed: int,
        history: str,
        terminal: bool,
    ) -> None:
        key = (str(context), tuple(action))
        row = self.edges.setdefault(
            key,
            {
                "n": 0,
                "changed": 0,
                "outcomes": {},
                "histories": [],
                "terminal": False,
                "ambiguous": False,
            },
        )
        row["n"] += 1
        row["changed"] += int(changed > 0)
        if outcome not in row["outcomes"] and row["outcomes"]:
            row["ambiguous"] = True
        if outcome in row["outcomes"] or len(row["outcomes"]) < 8:
            row["outcomes"][str(outcome)] = row["outcomes"].get(str(outcome), 0) + 1
        witness = [str(history), str(outcome), int(changed)]
        if witness not in row["histories"]:
            row["histories"] = (row["histories"] + [witness])[-8:]
        row["terminal"] = row["terminal"] or bool(terminal)
        self.edges.move_to_end(key)
        if len(self.edges) > self.limit:
            self.edges.popitem(last=False)

        stats = self.descriptors.setdefault(str(descriptor), [0, 0])
        stats[0] += 1
        stats[1] += int(changed > 0)
        self.descriptors.move_to_end(str(descriptor))
        if len(self.descriptors) > self.limit:
            self.descriptors.popitem(last=False)
        self.total_observations += 1

    def attempts(self, context: str, action: ActionKey) -> int:
        return int(self.edges.get((str(context), tuple(action)), {}).get("n", 0))

    def rate(self, descriptor: str) -> float:
        n, changed = self.descriptors.get(str(descriptor), (0, 0))
        return (changed + 1) / (n + 2)

    def descriptor_attempts(self, descriptor: str) -> int:
        return int(self.descriptors.get(str(descriptor), (0, 0))[0])

    def note_catalog(self, context: str, actions: tuple[ActionKey, ...]) -> None:
        self.catalogs[str(context)] = tuple(tuple(action) for action in actions)
        self.catalogs.move_to_end(str(context))
        if len(self.catalogs) > min(self.limit, 512):
            self.catalogs.popitem(last=False)

    def successors(self, context: str) -> list[tuple[ActionKey, str]]:
        out: list[tuple[ActionKey, str]] = []
        for (source, action), row in self.edges.items():
            if source != str(context) or row["terminal"] or row["ambiguous"]:
                continue
            if len(row["outcomes"]) == 1:
                target = next(iter(row["outcomes"]))
                if target != source:
                    out.append((action, target))
        return sorted(out, key=repr)

    def frontier_action(self, context: str) -> ActionKey | None:
        queue = deque([(str(context), None)])
        seen = {str(context)}
        while queue and len(seen) <= 128:
            state, first = queue.popleft()
            catalog = self.catalogs.get(state, ())
            if first is not None and any(self.attempts(state, action) == 0 for action in catalog):
                return first
            for action, target in self.successors(state):
                if target not in seen:
                    seen.add(target)
                    queue.append((target, action if first is None else first))
        return None


def settled_grid(frame: Any) -> tuple[tuple[int, ...], ...]:
    raw = frame.get("frame", []) if isinstance(frame, dict) else getattr(frame, "frame", [])
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    layers = list(raw) if isinstance(raw, (list, tuple)) else []
    if not layers:
        return ()
    grid = layers[-1]
    if hasattr(grid, "tolist"):
        grid = grid.tolist()
    if not isinstance(grid, (list, tuple)) or not grid:
        return ()
    width = len(grid[0]) if isinstance(grid[0], (list, tuple)) else 0
    if not width or len(grid) > 128 or width > 128:
        raise ValueError("unsupported public raster dimensions")
    if any(not isinstance(row, (list, tuple)) or len(row) != width for row in grid):
        raise ValueError("ragged public raster")
    return tuple(tuple(int(value) for value in row) for row in grid)


def visual_components(
    grid: tuple[tuple[int, ...], ...]
) -> tuple[list[tuple[int, int]], dict[tuple[int, int], tuple[int, int, int]]]:
    if not grid:
        return [], {}
    height, width = len(grid), len(grid[0])
    visited: set[tuple[int, int]] = set()
    regions: list[tuple[int, tuple[int, int]]] = []
    attributes: dict[tuple[int, int], tuple[int, int, int]] = {}
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            value = grid[y][x]
            stack = [(x, y)]
            visited.add((x, y))
            cells: list[tuple[int, int]] = []
            while stack:
                px, py = stack.pop()
                cells.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and (nx, ny) not in visited
                        and grid[ny][nx] == value
                    ):
                        visited.add((nx, ny))
                        stack.append((nx, ny))
            n = len(cells)
            sx = sum(px for px, _ in cells)
            sy = sum(py for _, py in cells)
            representative = min(
                cells,
                key=lambda point: (
                    (point[0] * n - sx) ** 2 + (point[1] * n - sy) ** 2,
                    point[1],
                    point[0],
                ),
            )
            bbox_w = max(px for px, _ in cells) - min(px for px, _ in cells) + 1
            bbox_h = max(py for _, py in cells) - min(py for _, py in cells) + 1
            shape = (n, bbox_w, bbox_h)
            for point in cells:
                attributes[point] = shape
            regions.append((n, representative))
    largest = max(n for n, _ in regions)
    regions.sort(key=lambda row: (row[0] == largest, row[1][1], row[1][0]))
    return [point for _, point in regions], attributes


class ConsequenceController(MemoryGraphController):
    """MemoryGraph controller with reward-independent causal-affordance probes."""

    def __init__(
        self,
        *args: Any,
        consequence_enabled: bool = True,
        visual_grounding: bool = True,
        contextual_quotient_enabled: bool = True,
        effect_limit: int = 2048,
        **kwargs: Any,
    ) -> None:
        self.consequence_enabled = bool(consequence_enabled)
        self.visual_grounding = bool(visual_grounding)
        self.contextual_quotient_enabled = bool(contextual_quotient_enabled)
        self.effects = EffectMemory(effect_limit)
        self.affordances = AffordanceMemory(effect_limit)
        self.contextual_quotient = ContextualQuotient()
        self._decision_tick = 0
        self._probe_serial = 0
        super().__init__(*args, **kwargs)

    def reset_episode(self) -> None:
        super().reset_episode()
        self._pending_effect: tuple[str, ActionKey, tuple[tuple[int, ...], ...], str, str] | None = None
        self._grid: tuple[tuple[int, ...], ...] = ()
        self._shape_attributes: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._primary: tuple[ActionToken, ...] = ()
        self._repeat: ActionKey | None = None
        self._repeat_left = 0
        self._raster_cache: tuple[Any, ...] | None = None

    def _descriptor(self, action: ActionToken) -> str:
        if action.action_id != 6 or not self._grid or action.x is None or action.y is None:
            return f"primitive:{action.action_id}"
        x, y = action.x, action.y
        height, width = len(self._grid), len(self._grid[0])
        values: dict[int, int] = {}
        pattern: list[int] = []
        for ny in range(y - 1, y + 2):
            for nx in range(x - 1, x + 2):
                if not (0 <= nx < width and 0 <= ny < height):
                    pattern.append(-1)
                else:
                    value = self._grid[ny][nx]
                    if value not in values:
                        values[value] = len(values)
                    pattern.append(values[value])
        shape = self._shape_attributes.get((x, y), ())
        return repr((6, shape, tuple(pattern)))

    def _catalog(self, obs: Observation) -> tuple[ActionToken, ...]:
        base = super()._action_catalog(obs)
        if not self.visual_grounding or 6 not in self._legal_ids(obs) or not self._grid:
            self._primary = base
            self._shape_attributes = {}
            return base
        if self._raster_cache is None or self._raster_cache[0] != self._grid:
            points, attributes = visual_components(self._grid)
            self._raster_cache = (self._grid, points, attributes)
        _, points, self._shape_attributes = self._raster_cache
        primary = [token for token in base if token.action_id != 6]
        primary += [ActionToken(6, x, y, "consequence") for x, y in points[:64]]
        seen: set[ActionKey] = set()
        catalog: list[ActionToken] = []
        for token in primary + list(base):
            key = self._action_key(token)
            if key not in seen:
                seen.add(key)
                catalog.append(token)
            if len(catalog) >= self.max_grounded_actions:
                break
        self._primary = tuple(catalog[: len(primary)])
        return tuple(catalog)

    def _consequence_context(
        self,
        obs: Observation,
        grid: tuple[tuple[int, ...], ...],
    ) -> str:
        if not self.contextual_quotient_enabled:
            return obs.evidence_sha256
        return self.contextual_quotient.context(
            obs.levels_completed,
            grid,
            obs.evidence_sha256,
        )

    def _record_effect(self, frame: Any, obs: Observation) -> None:
        grid = settled_grid(frame)
        if self._pending_effect is not None:
            context, action, before, descriptor, history = self._pending_effect
            previous_level = (
                self._previous.levels_completed
                if self._previous is not None
                else obs.levels_completed
            )
            if obs.levels_completed > previous_level:
                protected_outcome = "LEVEL_INCREMENT"
            elif obs.state == "GAME_OVER":
                protected_outcome = "GAME_OVER"
            elif obs.state == "WIN":
                protected_outcome = "WIN"
            else:
                protected_outcome = "CONTINUE"
            if self.contextual_quotient_enabled:
                self.contextual_quotient.observe(
                    previous_level,
                    before,
                    grid,
                    action,
                    protected_outcome,
                )
            source_context = (
                self.contextual_quotient.context(
                    previous_level,
                    before,
                    context,
                )
                if self.contextual_quotient_enabled
                else context
            )
            target_context = self._consequence_context(obs, grid)
            if len(before) == len(grid) and (not grid or not before or len(before[0]) == len(grid[0])):
                changed = sum(
                    left != right
                    for row_before, row_after in zip(before, grid)
                    for left, right in zip(row_before, row_after)
                )
                signature = effect_signature(before, grid, action)
            else:
                changed = max(
                    sum(len(row) for row in before),
                    sum(len(row) for row in grid),
                )
                signature = (changed, 0, 0, 0, 0, 0)
            terminal = obs.state in ("WIN", "GAME_OVER")
            self.effects.record(
                source_context,
                action,
                target_context,
                descriptor,
                changed,
                history,
                terminal,
            )
            directness = getattr(signature, "directness", 0.0)
            self.affordances.record(
                source_context,
                action,
                descriptor,
                signature,
                directness=directness,
                target=target_context,
            )
            self._pending_effect = None
        self._grid = grid

    def observe_terminal(self, frame: Any) -> None:
        obs = normalize_frame(frame)
        self._record_effect(frame, obs)
        self._process_previous_outcome(obs)
        self._previous = obs
        self._last_action = None

    def _select_probe(
        self, obs: Observation, catalog: tuple[ActionToken, ...]
    ) -> ActionToken:
        context = self._consequence_context(obs, self._grid)
        allowed_keys = {self._action_key(token) for token in catalog}
        primary = tuple(
            token for token in self._primary if self._action_key(token) in allowed_keys
        ) or catalog
        self.effects.note_catalog(
            context, tuple(self._action_key(token) for token in primary)
        )
        if not self.consequence_enabled:
            guard = self._exploration_guard(obs)
            return min(
                catalog,
                key=lambda token: self._visits.get((guard, self._action_key(token)), 0),
            )
        if self._repeat is not None and self._repeat_left and self._repeat in allowed_keys:
            self._repeat_left -= 1
            return self._token(self._repeat, "consequence_delayed_probe")
        self._repeat = None
        self._repeat_left = 0

        # Explicit duration probes preserve the possibility of delayed effects.
        if self._decision_tick % 16 == 8:
            index = self._probe_serial
            token = primary[index % len(primary)]
            length = 2 ** (1 + (index // len(primary)) % 3)
            self._probe_serial += 1
            self._repeat = self._action_key(token)
            self._repeat_left = length - 1
            return self._token(self._repeat, "consequence_delayed_probe")

        # Keep systematic coverage so an early false causal story cannot lock in.
        if self._decision_tick % 8 == 0:
            token = min(
                catalog,
                key=lambda candidate: (
                    self.effects.descriptor_attempts(self._descriptor(candidate)),
                    self.effects.attempts(context, self._action_key(candidate)),
                    self._candidate_key(candidate),
                ),
            )
            return self._token(self._action_key(token), "consequence_fair_probe")

        # A certified quotient has earned a reusable state graph. Once such a
        # context is active, deterministic reachability to an unexplored
        # successor outranks generic affordance preference. Explicit fair and
        # delayed probes above still retain priority.
        if context.startswith("cq:"):
            first = self.effects.frontier_action(context)
            if first in allowed_keys:
                return self._token(first, "consequence_frontier")

        # Once there is repeated controllability evidence, prefer it over raw
        # change frequency. This is still a proposal score, not a goal claim.
        scored = [
            (
                self.affordances.affordance_score(self._descriptor(token))
                / (1 + self.effects.attempts(context, self._action_key(token))),
                -self.effects.descriptor_attempts(self._descriptor(token)),
                tuple(-1 if value is None else value for value in self._candidate_key(token)),
                token,
            )
            for token in primary
        ]
        if scored and max(row[0] for row in scored) > 0.0:
            token = max(scored, key=lambda row: row[:3])[3]
            return self._token(self._action_key(token), "affordance")

        if all(self.effects.attempts(context, self._action_key(token)) for token in primary):
            first = self.effects.frontier_action(context)
            if first in allowed_keys:
                return self._token(first, "consequence_frontier")

        token = max(
            primary,
            key=lambda candidate: (
                self.effects.rate(self._descriptor(candidate))
                / (1 + self.effects.attempts(context, self._action_key(candidate))),
                -self.effects.descriptor_attempts(self._descriptor(candidate)),
            ),
        )
        return self._token(self._action_key(token), "consequence")

    def observe_and_choose(self, frame: Any) -> ActionToken | None:
        obs = normalize_frame(frame)
        self._record_effect(frame, obs)
        previous_level = self._previous.levels_completed if self._previous is not None else None
        self._process_previous_outcome(obs)
        if previous_level is not None and obs.levels_completed > previous_level:
            self._repeat = None
            self._repeat_left = 0
        if self._episode_context is None:
            self._episode_context = self._memory_context(obs)
        if self._level_start_guard is None:
            self._level_start_guard = self._retention_guard(obs)
        if obs.state == "WIN":
            self._previous = obs
            self._last_action = None
            return None

        token = self._next_archive(obs)
        if token is None:
            token = self._next_continuation(obs)
        if token is None:
            token = self._next_retained(obs)
        self._decision_tick += 1

        if token is None or token.source == "transfer":
            catalog = self._catalog(obs)
            prefix = tuple(self._episode_program)
            self.memory.note_legal(
                self._episode_context,
                prefix,
                tuple(self._action_key(candidate) for candidate in catalog),
            )
            forbidden = self.memory.forbidden_next(self._episode_context, prefix)
            allowed = tuple(
                candidate
                for candidate in catalog
                if self._action_key(candidate) not in forbidden
            )
            candidates = allowed or catalog
            if token is None or self._action_key(token) in forbidden:
                self._clear_transfer()
                token = self._select_probe(obs, candidates)
            key = self._action_key(token)
            guard = self._exploration_guard(obs)
            self._visits[(guard, key)] = self._visits.get((guard, key), 0) + 1
            self.memory.note_attempt(self._memory_context(obs), key)

        key = self._action_key(token)
        history = hashlib.sha256(repr(tuple(self._episode_program[-8:])).encode()).hexdigest()
        self._pending_effect = (
            self._consequence_context(obs, self._grid),
            key,
            self._grid,
            self._descriptor(token),
            history,
        )
        self._episode_program.append(key)
        self._previous = obs
        self._last_action = token
        return token
