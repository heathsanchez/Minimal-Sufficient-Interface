"""ARC3 Global Flash Closure V1.

A falsification experiment for non-linear, cross-game developmental search.

Compare three arms under the same frozen MG-ARC5 and the same total
environment-step budget across public ls20, ft09 and vc33:

1. sequential_local
   Each game receives an equal contiguous budget. Proposal statistics are local.
2. market_local
   A global probe market reallocates the same total budget dynamically, but
   proposal statistics remain game-local.
3. flash_shared
   The same global market additionally shares consequence *proposal* evidence
   across games. Every returned observation triggers immediate global
   revaluation ("flash") of matching action schemas in the other games.

Authority boundary:
- Raw public-state/action consequences are always game-local.
- Cross-game evidence may rank proposals only.
- Exact equivalence, fatal closure, ambiguity, and compiled routes are computed
  from exact same-game evidence only.
- No cross-game consequence is installed as an edge or certificate without
  destination execution.

Local closure after every new exact edge:
- retain deterministic/ambiguous exact edges;
- group known same-state actions by identical consequence;
- propagate fully-observed fatal states backward to a fixed point;
- recompute shortest exact routes from RESET to the highest-level unresolved
  frontier so discovery can be replayed by a shorter known path.

The experiment asks whether simultaneous revaluation reduces acquisition waste
or increases protected/novel consequence per paid environment interaction.
A negative result is useful: it names the smallest obstruction to global Flash.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
from typing import Any

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "global-flash-closure-results"
AGENT = OUT / "agent.py"

sys.path.insert(0, str(ROOT / "kaggle" / "src"))
from metalogic_arc3.consequence_controller import settled_grid

GAMES = ("ls20-9607627b", "ft09-0d8bbf25", "vc33-5430563c")
SHORTS = tuple(game.split("-")[0] for game in GAMES)
TOTAL_BUDGET = 1200
WARMUP_PER_GAME = 24
COORD_BINS = 4


def plain_state(frame: Any) -> str:
    return audit.state_name(frame)


def action_key(token: Any) -> tuple[int, int | None, int | None]:
    return (int(token.action_id), token.x, token.y)


def make_action(key: tuple[int, int | None, int | None], source: str):
    from arcengine import GameAction

    aid, x, y = key
    action = GameAction.from_id(int(aid))
    if action.is_complex():
        if x is None or y is None:
            raise AssertionError("complex action missing coordinates")
        action.set_data({"x": int(x), "y": int(y)})
        action.reasoning = {"source": source, "x": int(x), "y": int(y)}
    else:
        action.reasoning = {"source": source}
    return action, action.action_data.model_dump()


def schema_for(
    key: tuple[int, int | None, int | None],
    obs: Any,
) -> tuple[Any, ...]:
    aid, x, y = key
    if x is None or y is None:
        return ("primitive", int(aid))
    width = max(1, int(obs.width))
    height = max(1, int(obs.height))
    xb = min(COORD_BINS - 1, max(0, int(x) * COORD_BINS // width))
    yb = min(COORD_BINS - 1, max(0, int(y) * COORD_BINS // height))
    return ("complex", int(aid), int(xb), int(yb))


def outcome_signature(before: Any, after: Any) -> str:
    if int(after.levels_completed) > int(before.levels_completed):
        return "PROGRESS"
    if str(after.state) == "WIN":
        return "WIN"
    if str(after.state) == "GAME_OVER":
        return "GAME_OVER"
    if str(after.evidence_sha256) == str(before.evidence_sha256):
        return "NOOP"
    return "CHANGE"


class ProposalModel:
    def __init__(self) -> None:
        self.counts: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)
        self.games: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)
        self.local: dict[str, dict[tuple[Any, ...], Counter[str]]] = defaultdict(
            lambda: defaultdict(Counter)
        )

    def add(self, game: str, schema: tuple[Any, ...], signature: str) -> None:
        self.counts[schema][signature] += 1
        self.games[schema][game] += 1
        self.local[game][schema][signature] += 1

    @staticmethod
    def _features(counter: Counter[str]) -> dict[str, float]:
        n = float(sum(counter.values()))
        if n <= 0:
            return {
                "n": 0.0,
                "progress": 0.0,
                "change": 0.0,
                "terminal": 0.0,
                "noop": 0.0,
                "uncertainty": 1.0,
            }
        top = max(counter.values())
        return {
            "n": n,
            "progress": (counter["PROGRESS"] + counter["WIN"]) / n,
            "change": (
                counter["CHANGE"]
                + counter["PROGRESS"]
                + counter["WIN"]
                + counter["GAME_OVER"]
            ) / n,
            "terminal": counter["GAME_OVER"] / n,
            "noop": counter["NOOP"] / n,
            "uncertainty": 1.0 - float(top) / n,
        }

    def score(
        self,
        game: str,
        schema: tuple[Any, ...],
        *,
        shared: bool,
    ) -> tuple[float, dict[str, Any]]:
        local_counter = self.local[game].get(schema, Counter())
        local = self._features(local_counter)

        if shared:
            evidence = self.counts.get(schema, Counter())
            feat = self._features(evidence)
            other_obs = int(
                sum(
                    count
                    for source_game, count in self.games.get(schema, Counter()).items()
                    if source_game != game
                )
            )
            games_seen = len(self.games.get(schema, {}))
        else:
            feat = local
            other_obs = 0
            games_seen = int(bool(sum(local_counter.values())))

        n = feat["n"]
        # Proposal score only. Positive consequences are attractive, terminal
        # evidence is costly, and uncertain schemas receive information value.
        score = (
            2.0
            + 7.0 * feat["progress"]
            + 1.75 * feat["change"]
            - 4.5 * feat["terminal"]
            - 1.5 * feat["noop"]
            + 1.8 * feat["uncertainty"]
            + 1.25 / math.sqrt(1.0 + n)
            + 0.35 * math.log1p(other_obs)
            + 0.15 * max(0, games_seen - 1)
            + 0.75 / math.sqrt(1.0 + local["n"])
        )
        return score, {
            "schema_observations": int(n),
            "local_schema_observations": int(local["n"]),
            "other_game_observations": other_obs,
            "games_seen": games_seen,
            "schema_features": feat,
        }


@dataclass
class Candidate:
    game: str
    kind: str
    key: tuple[int, int | None, int | None] | None
    schema: tuple[Any, ...] | None
    score: float
    metadata: dict[str, Any]


class World:
    def __init__(
        self,
        module: Any,
        game_id: str,
        envdir: str,
        arm: str,
    ) -> None:
        from arc_agi import Arcade, OperationMode

        self.module = module
        self.game_id = game_id
        self.short = game_id.split("-")[0]
        self.arm = arm
        self.arc = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=envdir,
            logger=audit.quiet_logger(),
        )
        self.env = self.arc.make(game_id, seed=0)
        if self.env is None:
            raise RuntimeError("offline game unavailable: " + game_id)

        self.adapter = module.MyAgent(
            card_id=f"global-flash-{arm}-{self.short}",
            game_id="source-blind",
            agent_name="frozen-mg-arc5",
            ROOT_URL="",
            record=False,
            arc_env=None,
        )
        self.adapter.controller.archived_capabilities = ()
        self.controller = self.adapter.controller

        self.latest = self.adapter._convert_raw_frame_data(self.env.observation_space)
        self.root = str(module.normalize_frame(self.latest).evidence_sha256)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.catalogs: dict[
            str, tuple[tuple[int, int | None, int | None], ...]
        ] = {}
        self.edges: dict[
            tuple[str, tuple[int, int | None, int | None]],
            set[tuple[str, str]],
        ] = defaultdict(set)
        self.deterministic: dict[
            tuple[str, tuple[int, int | None, int | None]], str
        ] = {}
        self.ambiguous: set[
            tuple[str, tuple[int, int | None, int | None]]
        ] = set()
        self.prefixes: dict[
            str, tuple[tuple[int, int | None, int | None], ...]
        ] = {self.root: ()}
        self.visits = Counter()
        self.fatal: set[str] = set()
        self.replay_queue: deque[tuple[int, int | None, int | None]] = deque()
        self.replay_expected: deque[str] = deque()

        self.env_steps = 0
        self.probe_steps = 0
        self.replay_steps = 0
        self.reset_steps = 0
        self.zero_change = 0
        self.terminal_failures = 0
        self.max_level = int(module.normalize_frame(self.latest).levels_completed)
        self.milestones: list[dict[str, int]] = []
        self.distinct = {self.root}
        self.new_edges = 0
        self.new_nodes = 1
        self.local_action_collapses = 0
        self.compiled_route_actions: int | None = None
        self.closure_events = 0
        self.exhausted = False
        self.last_event: dict[str, Any] | None = None

        self._observe_current()

    def close(self) -> None:
        self.arc.close_scorecard()

    def current_obs(self):
        return self.module.normalize_frame(self.latest)

    def current_digest(self) -> str:
        return str(self.current_obs().evidence_sha256)

    def _observe_current(self) -> tuple[Any, tuple[Any, ...]]:
        obs = self.current_obs()
        digest = str(obs.evidence_sha256)
        self.distinct.add(digest)
        if digest not in self.nodes:
            self.new_nodes += int(bool(self.nodes))
        self.nodes[digest] = {
            "state": str(obs.state),
            "level": int(obs.levels_completed),
            "legal": tuple(int(v) for v in obs.available_actions),
            "width": int(obs.width),
            "height": int(obs.height),
        }
        self.visits[digest] += 1

        self.controller._grid = settled_grid(self.latest)
        self.controller._raster_cache = None
        catalog = self.controller._catalog(obs)
        allowed_keys = {action_key(token) for token in catalog}
        primary = tuple(
            token
            for token in getattr(self.controller, "_primary", ())
            if action_key(token) in allowed_keys
        ) or tuple(catalog)

        seen = set()
        keys = []
        tokens = []
        for token in primary:
            key = action_key(token)
            if key in seen:
                continue
            seen.add(key)
            keys.append(key)
            tokens.append(token)
        self.catalogs[digest] = tuple(keys)
        return obs, tuple(tokens)

    def edge_known(
        self,
        source: str,
        key: tuple[int, int | None, int | None],
    ) -> bool:
        pair = (source, key)
        return pair in self.deterministic or pair in self.ambiguous

    def unresolved_actions(self, node: str) -> tuple[
        tuple[int, int | None, int | None], ...
    ]:
        return tuple(
            key
            for key in self.catalogs.get(node, ())
            if not self.edge_known(node, key)
        )

    def _record_edge(
        self,
        source: str,
        key: tuple[int, int | None, int | None],
        target: str,
        signature: str,
    ) -> bool:
        pair = (source, key)
        frozen = (signature, target)
        before = set(self.edges.get(pair, set()))
        self.edges[pair].add(frozen)
        is_new = frozen not in before
        if is_new:
            self.new_edges += 1

        if len(self.edges[pair]) == 1:
            _sig, only_target = next(iter(self.edges[pair]))
            self.deterministic[pair] = only_target
            self.ambiguous.discard(pair)
        else:
            self.deterministic.pop(pair, None)
            self.ambiguous.add(pair)
        return is_new

    def _exact_groups(self) -> int:
        groups = 0
        for node, keys in self.catalogs.items():
            buckets = defaultdict(list)
            for key in keys:
                pair = (node, key)
                if pair not in self.deterministic:
                    continue
                rows = self.edges.get(pair, set())
                if len(rows) != 1:
                    continue
                signature, target = next(iter(rows))
                buckets[(signature, target)].append(key)
            groups += sum(max(0, len(values) - 1) for values in buckets.values())
        return groups

    def _fatal_closure(self) -> int:
        fatal = {
            node
            for node, row in self.nodes.items()
            if row["state"] == "GAME_OVER"
        }
        changed = True
        while changed:
            changed = False
            for node, row in self.nodes.items():
                if node in fatal or row["state"] != "NOT_FINISHED":
                    continue
                keys = self.catalogs.get(node, ())
                if not keys:
                    continue
                targets = []
                complete = True
                for key in keys:
                    pair = (node, key)
                    target = self.deterministic.get(pair)
                    if target is None:
                        complete = False
                        break
                    targets.append(target)
                if complete and targets and all(target in fatal for target in targets):
                    fatal.add(node)
                    changed = True
        self.fatal = fatal
        return len(fatal)

    def _bfs_route(
        self,
        start: str,
        *,
        prefer_max_level: bool = True,
    ) -> tuple[
        tuple[tuple[int, int | None, int | None], ...],
        tuple[str, ...],
    ] | None:
        if start not in self.nodes:
            return None
        target_level = self.max_level if prefer_max_level else 0
        queue = deque([(start, (), ())])
        seen = {start}
        fallback = None
        while queue:
            node, actions, targets = queue.popleft()
            row = self.nodes.get(node, {})
            unresolved = self.unresolved_actions(node)
            if (
                unresolved
                and node not in self.fatal
                and row.get("state") == "NOT_FINISHED"
            ):
                if int(row.get("level", 0)) >= target_level:
                    return actions, targets
                if fallback is None:
                    fallback = (actions, targets)

            for key in self.catalogs.get(node, ()):
                target = self.deterministic.get((node, key))
                if target is None or target in seen or target in self.fatal:
                    continue
                target_row = self.nodes.get(target, {})
                if target_row.get("state") in ("GAME_OVER", "WIN"):
                    continue
                seen.add(target)
                queue.append(
                    (
                        target,
                        actions + (key,),
                        targets + (target,),
                    )
                )
        return fallback

    def closure(self) -> dict[str, Any]:
        self.closure_events += 1
        fatal_count = self._fatal_closure()
        collapses = self._exact_groups()
        self.local_action_collapses = max(self.local_action_collapses, collapses)

        route = self._bfs_route(self.root, prefer_max_level=True)
        if route is not None:
            self.compiled_route_actions = len(route[0])
        return {
            "fatal_states": fatal_count,
            "exact_action_collapses": collapses,
            "compiled_route_actions": self.compiled_route_actions,
        }

    def _route_from_current(self) -> bool:
        current = self.current_digest()
        route = self._bfs_route(current, prefer_max_level=True)
        if route is None or not route[0]:
            return False
        self.replay_queue = deque(route[0])
        self.replay_expected = deque(route[1])
        return True

    def _route_from_root(self) -> None:
        route = self._bfs_route(self.root, prefer_max_level=True)
        if route is None:
            self.replay_queue.clear()
            self.replay_expected.clear()
            return
        self.replay_queue = deque(route[0])
        self.replay_expected = deque(route[1])

    def candidates(
        self,
        model: ProposalModel,
        *,
        shared: bool,
    ) -> list[Candidate]:
        obs, tokens = self._observe_current()
        digest = str(obs.evidence_sha256)
        state = str(obs.state)

        if state in ("GAME_OVER", "NOT_PLAYED"):
            return [
                Candidate(
                    self.game_id,
                    "reset",
                    None,
                    None,
                    1000.0,
                    {},
                )
            ]
        if state == "WIN":
            self.exhausted = True
            return []

        if self.replay_queue:
            key = self.replay_queue[0]
            expected = self.replay_expected[0] if self.replay_expected else None
            return [
                Candidate(
                    self.game_id,
                    "replay",
                    key,
                    schema_for(key, obs),
                    900.0,
                    {"expected": expected},
                )
            ]

        token_by_key = {action_key(token): token for token in tokens}
        unknown = [
            key
            for key in self.catalogs.get(digest, ())
            if key in token_by_key and not self.edge_known(digest, key)
        ]
        if unknown:
            rows = []
            for key in unknown:
                schema = schema_for(key, obs)
                score, meta = model.score(
                    self.game_id,
                    schema,
                    shared=shared,
                )
                rows.append(
                    Candidate(
                        self.game_id,
                        "probe",
                        key,
                        schema,
                        score,
                        meta,
                    )
                )
            rows.sort(
                key=lambda row: (
                    row.score,
                    tuple(
                        -1 if value is None else value
                        for value in (row.key or ())
                    ),
                ),
                reverse=True,
            )
            return rows

        if self._route_from_current():
            return self.candidates(model, shared=shared)

        if digest != self.root:
            return [
                Candidate(
                    self.game_id,
                    "reset",
                    None,
                    None,
                    500.0,
                    {"reason": "frontier_unreachable_from_current"},
                )
            ]

        # No exact unresolved frontier remains reachable from RESET.
        self.exhausted = True
        return []

    def execute(self, candidate: Candidate) -> dict[str, Any]:
        from arcengine import GameAction

        before = self.current_obs()
        before_digest = str(before.evidence_sha256)

        if candidate.kind == "reset":
            action = GameAction.RESET
            data = action.action_data.model_dump()
            raw = self.env.step(
                action,
                data=data,
                reasoning={"source": "flash_reset"},
            )
            self.env_steps += 1
            self.reset_steps += 1
            self.latest = self.adapter._convert_raw_frame_data(raw)
            after = self.current_obs()
            if str(after.evidence_sha256) != self.root:
                # Some environments may use level-scoped reset. Treat the
                # returned observation as the current episode root but never
                # alter exact historical edges.
                self.root = str(after.evidence_sha256)
                self.prefixes.setdefault(self.root, ())
            self._observe_current()
            self._route_from_root()
            event = {
                "kind": "reset",
                "game": self.game_id,
                "before": before_digest,
                "after": str(after.evidence_sha256),
                "paid_step": True,
                "new_evidence": False,
            }
            self.last_event = event
            return event

        if candidate.key is None:
            raise AssertionError("non-reset candidate missing exact action")

        key = candidate.key
        action, data = make_action(
            key,
            "flash_probe" if candidate.kind == "probe" else "flash_replay",
        )
        raw = self.env.step(
            action,
            data=data,
            reasoning={"source": action.reasoning.get("source", "flash")},
        )
        self.env_steps += 1
        if candidate.kind == "probe":
            self.probe_steps += 1
        else:
            self.replay_steps += 1

        self.latest = self.adapter._convert_raw_frame_data(raw)
        after = self.current_obs()
        after_digest = str(after.evidence_sha256)
        self.distinct.add(after_digest)
        self.zero_change += int(after_digest == before_digest)

        signature = outcome_signature(before, after)
        is_new = False
        replay_match = True

        if candidate.kind == "probe":
            is_new = self._record_edge(
                before_digest,
                key,
                after_digest,
                signature,
            )
        else:
            expected = (
                self.replay_expected.popleft()
                if self.replay_expected
                else candidate.metadata.get("expected")
            )
            self.replay_queue.popleft()
            replay_match = expected is None or after_digest == expected
            if not replay_match:
                # New destination under a supposedly exact replay makes the edge
                # ambiguous rather than silently trusting either observation.
                self._record_edge(
                    before_digest,
                    key,
                    after_digest,
                    signature,
                )
                self.replay_queue.clear()
                self.replay_expected.clear()

        source_prefix = self.prefixes.get(before_digest)
        if source_prefix is not None:
            candidate_prefix = source_prefix + (key,)
            old_prefix = self.prefixes.get(after_digest)
            if old_prefix is None or len(candidate_prefix) < len(old_prefix):
                self.prefixes[after_digest] = candidate_prefix

        self._observe_current()

        if int(after.levels_completed) > self.max_level:
            self.max_level = int(after.levels_completed)
            self.milestones.append(
                {
                    "level": self.max_level,
                    "paid_step": self.env_steps,
                }
            )
            self.replay_queue.clear()
            self.replay_expected.clear()

        if str(after.state) == "GAME_OVER":
            self.terminal_failures += 1
            self.replay_queue.clear()
            self.replay_expected.clear()

        event = {
            "kind": candidate.kind,
            "game": self.game_id,
            "before": before_digest,
            "after": after_digest,
            "action": list(key),
            "schema": list(candidate.schema) if candidate.schema is not None else None,
            "signature": signature,
            "paid_step": True,
            "new_evidence": bool(is_new),
            "replay_match": replay_match,
            "level": int(after.levels_completed),
            "state": str(after.state),
        }
        self.last_event = event
        return event

    def summary(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "env_steps": self.env_steps,
            "probe_steps": self.probe_steps,
            "replay_steps": self.replay_steps,
            "reset_steps": self.reset_steps,
            "max_level": self.max_level,
            "milestones": self.milestones,
            "final_state": plain_state(self.latest),
            "distinct_states": len(self.distinct),
            "exact_edge_keys": len(self.edges),
            "deterministic_edges": len(self.deterministic),
            "ambiguous_edges": len(self.ambiguous),
            "zero_change": self.zero_change,
            "terminal_failures": self.terminal_failures,
            "fatal_states": len(self.fatal),
            "exact_action_collapses": self.local_action_collapses,
            "compiled_route_actions": self.compiled_route_actions,
            "closure_events": self.closure_events,
            "exhausted": self.exhausted,
        }


def fresh_worlds(module: Any, manifest: dict[str, Any], arm: str) -> dict[str, World]:
    envdir = manifest["environments_dir"]
    return {
        game_id: World(module, game_id, envdir, arm)
        for game_id in GAMES
    }


def close_worlds(worlds: dict[str, World]) -> None:
    for world in worlds.values():
        world.close()


def current_schema_matches(
    worlds: dict[str, World],
    source_game: str,
    schema: tuple[Any, ...],
) -> int:
    count = 0
    for game_id, world in worlds.items():
        if game_id == source_game or world.exhausted:
            continue
        try:
            obs, tokens = world._observe_current()
        except Exception:
            continue
        digest = str(obs.evidence_sha256)
        for token in tokens:
            key = action_key(token)
            if world.edge_known(digest, key):
                continue
            if schema_for(key, obs) == schema:
                count += 1
    return count


def select_market_candidate(
    worlds: dict[str, World],
    models: dict[str, ProposalModel],
    shared_model: ProposalModel | None,
    *,
    shared: bool,
    total_steps: int,
) -> Candidate | None:
    rows = []
    for game_id, world in worlds.items():
        if world.exhausted:
            continue
        model = shared_model if shared else models[game_id]
        assert model is not None
        candidates = world.candidates(model, shared=shared)
        if not candidates:
            continue
        candidate = candidates[0]
        fairness = 0.35 / math.sqrt(1.0 + world.env_steps)
        # Forced local replay/reset operations remain dominant and are not
        # reinterpreted by cross-game evidence.
        score = candidate.score if candidate.kind in ("reset", "replay") else candidate.score + fairness
        rows.append((score, -world.env_steps, game_id, candidate))

    if not rows:
        return None
    rows.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return rows[0][3]


def execute_and_close(
    world: World,
    candidate: Candidate,
    *,
    local_model: ProposalModel,
    shared_model: ProposalModel | None,
    worlds: dict[str, World],
    shared: bool,
    metrics: Counter[str],
) -> dict[str, Any]:
    if candidate.kind == "probe" and candidate.schema is not None and shared:
        if candidate.metadata.get("other_game_observations", 0):
            metrics["cross_game_prior_uses"] += 1

    revalued = 0
    if (
        shared
        and candidate.kind == "probe"
        and candidate.schema is not None
    ):
        revalued = current_schema_matches(
            worlds,
            world.game_id,
            candidate.schema,
        )

    event = world.execute(candidate)

    if candidate.kind == "probe" and candidate.schema is not None:
        signature = str(event["signature"])
        local_model.add(world.game_id, candidate.schema, signature)
        if shared_model is not None:
            shared_model.add(world.game_id, candidate.schema, signature)

        metrics["evidence_returns"] += 1
        metrics["flash_events"] += int(shared)
        metrics["cross_game_revaluations"] += revalued
        if revalued:
            metrics["flash_events_with_cross_game_effect"] += 1

        # A shared schema that has materially different observed consequences
        # across games creates a named proposal obstruction rather than an
        # authority-level merge.
        if shared_model is not None:
            counter = shared_model.counts[candidate.schema]
            if len(counter) > 1 and len(shared_model.games[candidate.schema]) > 1:
                metrics["cross_game_obstruction_events"] += 1

    closure = world.closure()
    metrics["local_closure_events"] += 1
    metrics["fatal_states_total_snapshot"] = sum(
        len(item.fatal) for item in worlds.values()
    )
    metrics["compiled_routes_total_snapshot"] = sum(
        int(item.compiled_route_actions is not None)
        for item in worlds.values()
    )

    event["closure"] = closure
    return event


def run_sequential(
    module: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    arm = "sequential_local"
    worlds = fresh_worlds(module, manifest, arm)
    models = {game: ProposalModel() for game in GAMES}
    metrics = Counter()
    trace = []
    budget_per_game = TOTAL_BUDGET // len(GAMES)

    try:
        initial = {
            game: world.root for game, world in worlds.items()
        }
        for game_id in GAMES:
            world = worlds[game_id]
            model = models[game_id]
            while world.env_steps < budget_per_game and not world.exhausted:
                candidates = world.candidates(model, shared=False)
                if not candidates:
                    break
                event = execute_and_close(
                    world,
                    candidates[0],
                    local_model=model,
                    shared_model=None,
                    worlds=worlds,
                    shared=False,
                    metrics=metrics,
                )
                if len(trace) < 160:
                    trace.append(event)

        return arm_report(arm, worlds, metrics, trace, initial)
    finally:
        close_worlds(worlds)


def run_market(
    module: Any,
    manifest: dict[str, Any],
    *,
    shared: bool,
) -> dict[str, Any]:
    arm = "flash_shared" if shared else "market_local"
    worlds = fresh_worlds(module, manifest, arm)
    local_models = {game: ProposalModel() for game in GAMES}
    shared_model = ProposalModel() if shared else None
    metrics = Counter()
    trace = []

    try:
        initial = {
            game: world.root for game, world in worlds.items()
        }

        # Same small warmup per game so Flash cannot obtain an advantage simply
        # by never touching a difficult game.
        for game_id in GAMES:
            world = worlds[game_id]
            for _ in range(WARMUP_PER_GAME):
                if sum(item.env_steps for item in worlds.values()) >= TOTAL_BUDGET:
                    break
                model = shared_model if shared else local_models[game_id]
                assert model is not None
                candidates = world.candidates(model, shared=shared)
                if not candidates:
                    break
                event = execute_and_close(
                    world,
                    candidates[0],
                    local_model=local_models[game_id],
                    shared_model=shared_model,
                    worlds=worlds,
                    shared=shared,
                    metrics=metrics,
                )
                if len(trace) < 160:
                    trace.append(event)

        while sum(item.env_steps for item in worlds.values()) < TOTAL_BUDGET:
            candidate = select_market_candidate(
                worlds,
                local_models,
                shared_model,
                shared=shared,
                total_steps=sum(item.env_steps for item in worlds.values()),
            )
            if candidate is None:
                break
            world = worlds[candidate.game]
            event = execute_and_close(
                world,
                candidate,
                local_model=local_models[candidate.game],
                shared_model=shared_model,
                worlds=worlds,
                shared=shared,
                metrics=metrics,
            )
            if len(trace) < 160:
                trace.append(event)

        report = arm_report(arm, worlds, metrics, trace, initial)
        if shared_model is not None:
            report["shared_model"] = {
                "schema_count": len(shared_model.counts),
                "multi_game_schema_count": sum(
                    len(shared_model.games[schema]) > 1
                    for schema in shared_model.counts
                ),
                "schema_observations": sum(
                    sum(counter.values())
                    for counter in shared_model.counts.values()
                ),
                "obstructed_schema_count": sum(
                    len(counter) > 1
                    and len(shared_model.games[schema]) > 1
                    for schema, counter in shared_model.counts.items()
                ),
            }
        return report
    finally:
        close_worlds(worlds)


def arm_report(
    arm: str,
    worlds: dict[str, World],
    metrics: Counter[str],
    trace: list[dict[str, Any]],
    initial: dict[str, str],
) -> dict[str, Any]:
    rows = {
        game: world.summary()
        for game, world in worlds.items()
    }
    total_steps = sum(row["env_steps"] for row in rows.values())
    total_probes = sum(row["probe_steps"] for row in rows.values())
    total_distinct = sum(row["distinct_states"] for row in rows.values())
    total_edges = sum(row["exact_edge_keys"] for row in rows.values())
    total_levels = sum(row["max_level"] for row in rows.values())
    zero_change = sum(row["zero_change"] for row in rows.values())
    terminals = sum(row["terminal_failures"] for row in rows.values())
    consequence_yield = (
        total_distinct
        + 0.25 * total_edges
        + 100.0 * total_levels
    ) / max(1, total_steps)

    return {
        "arm": arm,
        "initial_digests": initial,
        "budget": TOTAL_BUDGET,
        "total_env_steps": total_steps,
        "total_probe_steps": total_probes,
        "total_distinct_states": total_distinct,
        "total_exact_edge_keys": total_edges,
        "total_levels": total_levels,
        "zero_change_steps": zero_change,
        "terminal_failures": terminals,
        "consequence_yield_per_step": consequence_yield,
        "metrics": dict(metrics),
        "games": rows,
        "trace_head": trace,
    }


def compare(arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    seq = arms["sequential_local"]
    market = arms["market_local"]
    flash = arms["flash_shared"]

    protected = {
        arm: {
            game: row["games"][game]["max_level"]
            for game in GAMES
        }
        for arm, row in arms.items()
    }

    return {
        "protected_levels": protected,
        "market_vs_sequential": {
            "consequence_yield_ratio": (
                market["consequence_yield_per_step"]
                / max(seq["consequence_yield_per_step"], 1e-12)
            ),
            "zero_change_delta": (
                market["zero_change_steps"] - seq["zero_change_steps"]
            ),
            "distinct_state_delta": (
                market["total_distinct_states"] - seq["total_distinct_states"]
            ),
            "level_delta": market["total_levels"] - seq["total_levels"],
        },
        "flash_vs_market": {
            "consequence_yield_ratio": (
                flash["consequence_yield_per_step"]
                / max(market["consequence_yield_per_step"], 1e-12)
            ),
            "zero_change_delta": (
                flash["zero_change_steps"] - market["zero_change_steps"]
            ),
            "distinct_state_delta": (
                flash["total_distinct_states"] - market["total_distinct_states"]
            ),
            "level_delta": flash["total_levels"] - market["total_levels"],
            "cross_game_prior_uses": flash["metrics"].get(
                "cross_game_prior_uses", 0
            ),
            "cross_game_revaluations": flash["metrics"].get(
                "cross_game_revaluations", 0
            ),
            "cross_game_obstruction_events": flash["metrics"].get(
                "cross_game_obstruction_events", 0
            ),
        },
        "flash_vs_sequential": {
            "consequence_yield_ratio": (
                flash["consequence_yield_per_step"]
                / max(seq["consequence_yield_per_step"], 1e-12)
            ),
            "zero_change_delta": (
                flash["zero_change_steps"] - seq["zero_change_steps"]
            ),
            "distinct_state_delta": (
                flash["total_distinct_states"] - seq["total_distinct_states"]
            ),
            "level_delta": flash["total_levels"] - seq["total_levels"],
        },
    }


def main() -> None:
    manifest = json.loads((OUT / "public.json").read_text())
    exact_games = tuple(row["game_id"] for row in manifest["games"])
    if set(exact_games) != set(GAMES):
        raise AssertionError(
            f"unexpected public game set: {exact_games}"
        )

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    arms = {}
    arms["sequential_local"] = run_sequential(module, manifest)
    print(
        "FLASH_ARM="
        + json.dumps(
            {
                k: v
                for k, v in arms["sequential_local"].items()
                if k != "trace_head"
            },
            sort_keys=True,
        ),
        flush=True,
    )

    arms["market_local"] = run_market(
        module,
        manifest,
        shared=False,
    )
    print(
        "FLASH_ARM="
        + json.dumps(
            {
                k: v
                for k, v in arms["market_local"].items()
                if k != "trace_head"
            },
            sort_keys=True,
        ),
        flush=True,
    )

    arms["flash_shared"] = run_market(
        module,
        manifest,
        shared=True,
    )
    print(
        "FLASH_ARM="
        + json.dumps(
            {
                k: v
                for k, v in arms["flash_shared"].items()
                if k != "trace_head"
            },
            sort_keys=True,
        ),
        flush=True,
    )

    initials = {
        tuple(sorted(row["initial_digests"].items()))
        for row in arms.values()
    }
    if len(initials) != 1:
        raise AssertionError("arms did not start from identical exact public states")

    for row in arms.values():
        if row["total_env_steps"] > TOTAL_BUDGET:
            raise AssertionError("arm exceeded equal environment-step budget")
        if any(
            game_row["ambiguous_edges"] < 0
            for game_row in row["games"].values()
        ):
            raise AssertionError("invalid ambiguity accounting")

    comparison = compare(arms)
    report = {
        "schema": "arc3-global-flash-closure-v1",
        "interpretation": (
            "three-game public developmental falsification: local exact closure "
            "is held common while scheduling and cross-game proposal evidence "
            "are added separately"
        ),
        "claim_boundary": (
            "cross-game information can rank experiments only; exact edges, "
            "fatality, equivalence and compiled routes remain destination-local "
            "and require destination execution"
        ),
        "games": list(GAMES),
        "total_budget_per_arm": TOTAL_BUDGET,
        "warmup_per_game": WARMUP_PER_GAME,
        "arms": arms,
        "comparison": comparison,
        "hypothesis_status": {
            "flash_protected_not_worse_than_sequential": all(
                arms["flash_shared"]["games"][game]["max_level"]
                >= arms["sequential_local"]["games"][game]["max_level"]
                for game in GAMES
            ),
            "flash_consequence_yield_gt_sequential": (
                arms["flash_shared"]["consequence_yield_per_step"]
                > arms["sequential_local"]["consequence_yield_per_step"]
            ),
            "flash_cross_game_revaluation_activated": (
                arms["flash_shared"]["metrics"].get(
                    "cross_game_revaluations", 0
                ) > 0
            ),
        },
    }
    audit.write_json(OUT / "global-flash-closure-v1.json", report)

    print(
        "GLOBAL_FLASH_CLOSURE_RESULT="
        + json.dumps(
            {
                "comparison": comparison,
                "hypothesis_status": report["hypothesis_status"],
                "arm_summaries": {
                    name: {
                        k: row[k]
                        for k in (
                            "total_env_steps",
                            "total_probe_steps",
                            "total_distinct_states",
                            "total_exact_edge_keys",
                            "total_levels",
                            "zero_change_steps",
                            "terminal_failures",
                            "consequence_yield_per_step",
                        )
                    }
                    for name, row in arms.items()
                },
            },
            sort_keys=True,
        ),
        flush=True,
    )
    print("ARC3_GLOBAL_FLASH_CLOSURE_V1=PASS", flush=True)


if __name__ == "__main__":
    main()
