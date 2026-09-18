"""ARC3 Global Flash Closure V7.

V6 proved that cross-game contradiction can activate representation change, but
activating every global obstruction immediately was harmful: the refinement
over-fragmented local evidence and lost protected progress.

V7 compiles that failure into the authority rule.

A cross-game obstruction may now only PROPOSE a representation refinement.
The destination promotes it only when its own accumulated exact evidence shows
that the finer public representation materially reduces consequence impurity.
The destination continuously revalidates the split and revokes it if the gain
falls below threshold.

Past observations are shadow-indexed in both coarse and refined schemas, so
promotion does not reset local knowledge. No foreign outcome enters a local
score; cross-game evidence changes only which representation is eligible.

Arms:
1. sequential_local
2. market_local
3. flash_validated_refinement

The test is whether globally proposed, locally validated and revocable
representation changes can preserve the market's wins while extracting genuine
cross-lens compounding.
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
from metalogic_arc3.flash_ledger import (
    EvidenceRef,
    FlashLedger,
    GlobalCapability,
    stable_id,
)

GAMES = ("ls20-9607627b", "ft09-0d8bbf25", "vc33-5430563c")
SHORTS = tuple(game.split("-")[0] for game in GAMES)
TOTAL_BUDGET = 1200
WARMUP_PER_GAME = 24
MIN_GAME_SHARE = 0.12
LOCAL_NOOP_CONFIRMATIONS = 2
STRUCTURAL_PROBE_BONUS = 0.90
LOCAL_REFINEMENT_MIN_OBS = 6
MIN_REFINEMENT_GAIN = 0.10
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
    # Transfer is typed by the public intervention language and coarse protected
    # phase. This prevents action-id coincidence from becoming a false shared
    # capability across unrelated games.
    context_type = (
        "L0" if int(obs.levels_completed) == 0 else "L+",
        tuple(int(v) for v in obs.available_actions),
    )
    if x is None or y is None:
        return ("primitive", int(aid), context_type)
    width = max(1, int(obs.width))
    height = max(1, int(obs.height))
    xb = min(COORD_BINS - 1, max(0, int(x) * COORD_BINS // width))
    yb = min(COORD_BINS - 1, max(0, int(y) * COORD_BINS // height))
    return ("complex", int(aid), int(xb), int(yb), context_type)


def refined_schema_for(
    key: tuple[int, int | None, int | None],
    obs: Any,
) -> tuple[Any, ...]:
    """A deterministic refinement of the coarse public intervention schema.

    The refinement adds only public geometric/context facts. It does not import
    a consequence from another game.
    """
    coarse = schema_for(key, obs)
    aid, x, y = key
    width = max(1, int(obs.width))
    height = max(1, int(obs.height))
    level = int(obs.levels_completed)
    geometry = ("shape", width, height, "level", level)
    if x is None or y is None:
        return coarse + ("refined", geometry)
    xb8 = min(7, max(0, int(x) * 8 // width))
    yb8 = min(7, max(0, int(y) * 8 // height))
    x_role = "left" if int(x) == 0 else "right" if int(x) == width - 1 else "inner"
    y_role = "top" if int(y) == 0 else "bottom" if int(y) == height - 1 else "inner"
    return coarse + (
        "refined",
        geometry,
        ("bin8", xb8, yb8),
        ("boundary", x_role, y_role),
    )


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

    def portable_noop_constructor(
        self,
        destination_game: str,
        schema: tuple[Any, ...],
    ) -> dict[str, Any] | None:
        """Return a cross-game NOOP-family constructor, never an exact edge.

        The constructor must be independently supported in both *other* games.
        Destination-local confirmation is checked separately by World before any
        acquisition pruning is permitted.
        """
        support = []
        for source_game in GAMES:
            if source_game == destination_game:
                continue
            counter = Counter(self.local[source_game].get(schema, Counter()))
            n = sum(counter.values())
            if n <= 0 or counter["NOOP"] != n:
                return None
            support.append((source_game, int(n)))
        if len(support) != len(GAMES) - 1:
            return None
        return {
            "kind": "portable_noop_family",
            "support_games": [game for game, _count in support],
            "support_observations": sum(count for _game, count in support),
        }

    def refinement_obstruction(
        self,
        schema: tuple[Any, ...],
    ) -> dict[str, Any] | None:
        """Compile cross-game contradiction into a representation refinement."""
        rows: dict[str, Counter[str]] = {}
        signatures: set[str] = set()
        for game in GAMES:
            counter = Counter(self.local[game].get(schema, Counter()))
            if not counter:
                continue
            rows[game] = counter
            signatures.update(sig for sig, count in counter.items() if count > 0)
        if len(rows) < 2 or len(signatures) < 2:
            return None
        return {
            "kind": "representation_refinement",
            "source_games": sorted(rows),
            "signatures": sorted(signatures),
            "observations": int(sum(sum(counter.values()) for counter in rows.values())),
        }

    def local_refinement_validation(
        self,
        game: str,
        coarse_schema: tuple[Any, ...],
    ) -> dict[str, Any] | None:
        """Require destination evidence that the proposed split earns its cost."""
        coarse = Counter(self.local[game].get(coarse_schema, Counter()))
        n = int(sum(coarse.values()))
        active_signatures = [sig for sig, count in coarse.items() if count > 0]
        if n < LOCAL_REFINEMENT_MIN_OBS or len(active_signatures) < 2:
            return None

        children: list[tuple[tuple[Any, ...], Counter[str]]] = []
        prefix_len = len(coarse_schema)
        for schema, counter in self.local[game].items():
            if (
                len(schema) > prefix_len
                and schema[:prefix_len] == coarse_schema
                and schema[prefix_len] == "refined"
                and sum(counter.values()) > 0
            ):
                children.append((schema, Counter(counter)))
        if len(children) < 2:
            return None

        child_n = int(sum(sum(counter.values()) for _schema, counter in children))
        if child_n < n:
            return None

        coarse_impurity = 1.0 - max(coarse.values()) / max(1, n)
        weighted_child_impurity = 0.0
        for _schema, counter in children:
            cn = int(sum(counter.values()))
            if cn <= 0:
                continue
            impurity = 1.0 - max(counter.values()) / cn
            weighted_child_impurity += (cn / child_n) * impurity
        gain = coarse_impurity - weighted_child_impurity
        if gain < MIN_REFINEMENT_GAIN:
            return None
        return {
            "kind": "destination_validated_refinement",
            "observations": n,
            "children": len(children),
            "coarse_impurity": coarse_impurity,
            "refined_impurity": weighted_child_impurity,
            "gain": gain,
        }

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
        local_counter = Counter(self.local[game].get(schema, Counter()))
        local = self._features(local_counter)

        # The market-local score is the floor. Shared evidence is never allowed
        # to replace local evidence; it can only add a bounded typed term.
        base = (
            2.0
            + 7.0 * local["progress"]
            + 1.75 * local["change"]
            - 4.5 * local["terminal"]
            - 1.5 * local["noop"]
            + 1.8 * local["uncertainty"]
            + 1.25 / math.sqrt(1.0 + local["n"])
            + 0.75 / math.sqrt(1.0 + local["n"])
        )

        if not shared:
            return base, {
                "schema_observations": int(local["n"]),
                "local_schema_observations": int(local["n"]),
                "other_game_observations": 0,
                "games_seen": int(bool(local["n"])),
                "cross_mode": "local_only",
                "schema_features": local,
            }

        total_counter = Counter(self.counts.get(schema, Counter()))
        other_counter = Counter(total_counter)
        for sig, count in local_counter.items():
            other_counter[sig] -= count
            if other_counter[sig] <= 0:
                del other_counter[sig]

        other_games = {
            source_game: count
            for source_game, count in self.games.get(schema, Counter()).items()
            if source_game != game and count > 0
        }
        other = self._features(other_counter)
        other_obs = int(other["n"])
        local_obs = int(local["n"])

        cross_mode = "none"
        cross_term = 0.0
        dominant_other = (
            other_counter.most_common(1)[0][0]
            if other_counter
            else None
        )
        dominant_local = (
            local_counter.most_common(1)[0][0]
            if local_counter
            else None
        )
        other_agreement = (
            other_counter[dominant_other] / max(1, sum(other_counter.values()))
            if dominant_other is not None
            else 0.0
        )
        local_agreement = (
            local_counter[dominant_local] / max(1, sum(local_counter.values()))
            if dominant_local is not None
            else 0.0
        )

        corroborated = False
        # V3: shared evidence is a prior only before this destination has
        # purchased any direct evidence for the schema.  Once local evidence
        # exists, it becomes the sole ranking authority for that schema.
        if other_obs and local_obs == 0:
            corroborated = (
                len(other_games) >= 2
                and other_agreement >= 0.90
            )

        if local_obs > 0 and other_obs:
            cross_mode = "local_authority"
            cross_term = 0.0
        elif corroborated:
            utility = (
                4.0 * other["progress"]
                + 0.8 * other["change"]
                - 2.5 * other["terminal"]
                - 0.8 * other["noop"]
            )
            # Ephemeral near-tie prior only: enough to choose which unseen
            # schema to test first, never enough to dominate the local market.
            cross_term = max(-0.50, min(0.50, 0.25 * utility))
            cross_mode = "promoted"
        elif other_obs:
            # V2 showed that rewarding obstruction splits can itself distort
            # the market. Preserve the obstruction as information, but do not
            # pay an exploration bonus merely because other games disagree.
            cross_term = 0.0
            cross_mode = "obstruction_split"

        return base + cross_term, {
            "schema_observations": int(sum(total_counter.values())),
            "local_schema_observations": local_obs,
            "other_game_observations": other_obs,
            "games_seen": len(self.games.get(schema, {})),
            "other_games_seen": len(other_games),
            "cross_mode": cross_mode,
            "cross_term": cross_term,
            "other_agreement": other_agreement,
            "schema_features": self._features(total_counter),
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

        # V4 structural Flash state. Pruned actions are excluded from future
        # acquisition only; they are never inserted into the exact edge graph.
        self.schemas: dict[
            tuple[str, tuple[int, int | None, int | None]], tuple[Any, ...]
        ] = {}
        self.structural_pruned: set[
            tuple[str, tuple[int, int | None, int | None]]
        ] = set()
        self.compiled_noop_groups: set[tuple[str, tuple[Any, ...]]] = set()
        self.structural_pruned_count = 0
        self.structural_revocations = 0
        self.structural_constructor_probe_uses = 0
        self.representation_refinement_uses = 0
        self.refined_schema_ids: set[tuple[Any, ...]] = set()
        self.active_refinements: set[tuple[Any, ...]] = set()
        self.refinement_revocations = 0

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
        for key in keys:
            self.schemas[(digest, key)] = schema_for(key, obs)
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
            if (
                not self.edge_known(node, key)
                and (node, key) not in self.structural_pruned
            )
        )

    def _node_schema_counter(
        self,
        node: str,
        schema: tuple[Any, ...],
    ) -> Counter[str]:
        counter: Counter[str] = Counter()
        for key in self.catalogs.get(node, ()):
            if self.schemas.get((node, key)) != schema:
                continue
            rows = self.edges.get((node, key), set())
            if len(rows) != 1:
                continue
            signature, _target = next(iter(rows))
            counter[str(signature)] += 1
        return counter

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
        structural_model: ProposalModel | None = None,
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

        # Constructors are revocable. If later cross-game evidence breaks a
        # portable NOOP family, restore any still-unverified destination actions
        # to the acquisition frontier immediately.
        if shared and structural_model is not None and self.structural_pruned:
            for pair in list(self.structural_pruned):
                node, key = pair
                if node != digest:
                    continue
                schema = self.schemas.get(pair)
                if schema is None:
                    continue
                if structural_model.portable_noop_constructor(self.game_id, schema) is None:
                    self.structural_pruned.remove(pair)
                    self.structural_pruned_count = max(
                        0, self.structural_pruned_count - 1
                    )
                    self.structural_revocations += 1
                    self.compiled_noop_groups.discard((digest, schema))

        unknown = [
            key
            for key in self.catalogs.get(digest, ())
            if (
                key in token_by_key
                and not self.edge_known(digest, key)
                and (digest, key) not in self.structural_pruned
            )
        ]

        # V4: compile a portable NOOP-family obstruction into local acquisition
        # elimination only after two exact destination-local NOOP witnesses on
        # this exact state/schema. No exact edge is invented for pruned siblings.
        if shared and structural_model is not None and unknown:
            by_schema: dict[tuple[Any, ...], list[tuple[int, int | None, int | None]]] = defaultdict(list)
            for key in unknown:
                by_schema[self.schemas[(digest, key)]].append(key)
            for schema, keys in by_schema.items():
                constructor = structural_model.portable_noop_constructor(
                    self.game_id,
                    schema,
                )
                if constructor is None:
                    continue
                local_counter = self._node_schema_counter(digest, schema)
                if local_counter["NOOP"] >= LOCAL_NOOP_CONFIRMATIONS:
                    group = (digest, schema)
                    if group not in self.compiled_noop_groups:
                        self.compiled_noop_groups.add(group)
                        for key in keys:
                            pair = (digest, key)
                            if pair not in self.structural_pruned:
                                self.structural_pruned.add(pair)
                                self.structural_pruned_count += 1

            unknown = [
                key for key in unknown
                if (digest, key) not in self.structural_pruned
            ]

        if unknown:
            rows = []
            for key in unknown:
                schema = self.schemas[(digest, key)]
                shadow_refined_schema = refined_schema_for(key, obs)
                effective_schema = schema
                global_obstruction = None
                local_validation = None
                if shared and structural_model is not None:
                    global_obstruction = structural_model.refinement_obstruction(schema)
                    if global_obstruction is not None:
                        local_validation = model.local_refinement_validation(
                            self.game_id,
                            schema,
                        )
                        if local_validation is not None:
                            self.active_refinements.add(schema)
                        elif schema in self.active_refinements:
                            self.active_refinements.remove(schema)
                            self.refinement_revocations += 1

                    if schema in self.active_refinements:
                        effective_schema = shadow_refined_schema
                        self.refined_schema_ids.add(effective_schema)

                # Scores remain destination-local. The global graph may only
                # nominate a split; local evidence decides whether it is active.
                score, meta = model.score(
                    self.game_id,
                    effective_schema,
                    shared=False,
                )
                meta = dict(meta)
                meta["coarse_schema"] = schema
                meta["shadow_refined_schema"] = shadow_refined_schema
                meta["effective_schema"] = effective_schema
                if schema in self.active_refinements:
                    meta["representation_refined"] = True
                    meta["refinement_capability"] = global_obstruction
                    meta["local_refinement_validation"] = local_validation
                elif global_obstruction is not None:
                    meta["refinement_proposed"] = True
                    meta["refinement_capability"] = global_obstruction
                if shared and structural_model is not None:
                    constructor = structural_model.portable_noop_constructor(
                        self.game_id,
                        schema,
                    )
                    if constructor is not None:
                        local_counter = self._node_schema_counter(digest, schema)
                        siblings = sum(
                            self.schemas.get((digest, other)) == schema
                            and not self.edge_known(digest, other)
                            and (digest, other) not in self.structural_pruned
                            for other in self.catalogs.get(digest, ())
                        )
                        confirmed = int(local_counter["NOOP"])
                        if confirmed < LOCAL_NOOP_CONFIRMATIONS and siblings >= 2:
                            # This bonus values an experiment for the search
                            # space it could eliminate, not for a predicted win.
                            score += STRUCTURAL_PROBE_BONUS * (
                                1.0 + min(2.0, siblings / 8.0)
                            )
                            meta["structural_mode"] = "noop_constructor_probe"
                            meta["noop_confirmations"] = confirmed
                            meta["sibling_frontier"] = int(siblings)
                            meta["constructor"] = constructor
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
            return self.candidates(
                model,
                shared=shared,
                structural_model=structural_model,
            )

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
            "structural_pruned_actions": self.structural_pruned_count,
            "structural_revocations": self.structural_revocations,
            "compiled_noop_groups": len(self.compiled_noop_groups),
            "structural_constructor_probe_uses": self.structural_constructor_probe_uses,
            "representation_refinement_uses": self.representation_refinement_uses,
            "refined_schema_count": len(self.refined_schema_ids),
            "active_refinement_count": len(self.active_refinements),
            "refinement_revocations": self.refinement_revocations,
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


def write_refinement_ledger(
    model: ProposalModel,
    worlds: dict[str, World],
) -> dict[str, Any]:
    ledger = FlashLedger()
    promoted = 0
    for schema in sorted(model.counts, key=repr):
        obstruction = model.refinement_obstruction(schema)
        if obstruction is None:
            continue
        witnesses = []
        for game in obstruction["source_games"]:
            counter = model.local[game][schema]
            ref = EvidenceRef(
                game=game,
                kind="coarse_schema_consequence_observation",
                artifact_or_run="arc3-global-flash-closure-v7",
                local_key=repr((schema, sorted(counter.items()))),
            )
            ledger.add_evidence(ref)
            witnesses.append(ref)
        payload = {
            "kind": "representation_refinement",
            "schema": repr(schema),
            "sources": obstruction["source_games"],
            "signatures": obstruction["signatures"],
        }
        capability_id = stable_id("cap", payload)
        ledger.add_capability(
            GlobalCapability(
                capability_id=capability_id,
                kind="representation_refinement",
                source_games=set(obstruction["source_games"]),
                scope={"coarse_schema": repr(schema)},
                consequence_signature=tuple(obstruction["signatures"]),
                exact_witnesses=witnesses,
                protected_effect=None,
                acquisition_cost=int(obstruction["observations"]),
                authority="public_exact_observation",
                destination_status={
                    game: (
                        "ACTIVE"
                        if schema in worlds[game].active_refinements
                        else "RESERVE"
                    )
                    for game in GAMES
                },
                notes={"refinement": "public_geometry_v1"},
            )
        )
        promoted += 1
    path = OUT / "flash-ledger-v7.json"
    ledger.write(path)
    return {
        "schema": ledger.schema,
        "active_capabilities": len(ledger.active_capability_ids()),
        "promoted_refinements": promoted,
        "content_hash": ledger.content_hash(),
        "path": str(path.relative_to(ROOT)),
    }


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
        model = models[game_id]
        candidates = world.candidates(
            model,
            shared=shared,
            structural_model=shared_model,
        )
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

    # V3 anti-starvation invariant. Flash is allowed to change the order of
    # experiments, not erase an experimental lens before it can locally
    # falsify the shared prior. The floor is a share of paid acquisition, not
    # an equal-budget pipeline.
    if shared:
        required = max(
            WARMUP_PER_GAME,
            int(math.floor(MIN_GAME_SHARE * float(total_steps + 1))),
        )
        starved = [
            row for row in rows
            if worlds[row[2]].env_steps < required
        ]
        if starved:
            starved.sort(
                key=lambda row: (
                    required - worlds[row[2]].env_steps,
                    row[0],
                    row[1],
                    row[2],
                ),
                reverse=True,
            )
            chosen = starved[0][3]
            chosen.metadata = dict(chosen.metadata)
            chosen.metadata["scheduler_guard"] = "minimum_share"
            chosen.metadata["minimum_required_steps"] = required
            return chosen

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
    if candidate.metadata.get("scheduler_guard") == "minimum_share":
        metrics["minimum_share_forced_steps"] += 1
    if candidate.metadata.get("structural_mode") == "noop_constructor_probe":
        metrics["structural_constructor_probe_uses"] += 1
        world.structural_constructor_probe_uses += 1
    if candidate.metadata.get("representation_refined"):
        metrics["representation_refinement_probe_uses"] += 1
        world.representation_refinement_uses += 1

    if candidate.kind == "probe" and candidate.schema is not None and shared:
        cross_mode = candidate.metadata.get("cross_mode", "none")
        if cross_mode == "promoted":
            metrics["typed_cross_game_promotions"] += 1
            metrics["cross_game_prior_uses"] += 1
        elif cross_mode == "obstruction_split":
            metrics["typed_obstruction_splits"] += 1

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
        # Preserve the full local past in both representations. This makes
        # promotion/revocation a view change rather than a memory reset.
        coarse_schema = tuple(candidate.schema)
        shadow_refined_schema = tuple(
            candidate.metadata.get(
                "shadow_refined_schema",
                coarse_schema,
            )
        )
        local_model.add(world.game_id, coarse_schema, signature)
        if shadow_refined_schema != coarse_schema:
            local_model.add(world.game_id, shadow_refined_schema, signature)
        if shared_model is not None:
            # Global structural evidence stays in the stable coarse schema.
            shared_model.add(world.game_id, coarse_schema, signature)

        metrics["evidence_returns"] += 1
        metrics["flash_events"] += int(shared)
        metrics["cross_game_revaluations"] += revalued
        if revalued:
            metrics["flash_events_with_cross_game_effect"] += 1

        # Count only newly activated typed obstruction situations, not every
        # subsequent observation in an already-split schema.
        if shared_model is not None and candidate.metadata.get("cross_mode") == "obstruction_split":
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
    arm = "flash_validated_refinement" if shared else "market_local"
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
                model = local_models[game_id]
                candidates = world.candidates(
                    model,
                    shared=shared,
                    structural_model=shared_model,
                )
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
                "refinement_obstruction_count": sum(
                    shared_model.refinement_obstruction(schema) is not None
                    for schema in shared_model.counts
                ),
            }
            report["flash_ledger"] = write_refinement_ledger(shared_model, worlds)
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
    structural_pruned = sum(
        row.get("structural_pruned_actions", 0) for row in rows.values()
    )
    compiled_noop_groups = sum(
        row.get("compiled_noop_groups", 0) for row in rows.values()
    )
    representation_refinement_uses = sum(
        row.get("representation_refinement_uses", 0) for row in rows.values()
    )
    refined_schema_count = sum(
        row.get("refined_schema_count", 0) for row in rows.values()
    )
    active_refinement_count = sum(
        row.get("active_refinement_count", 0) for row in rows.values()
    )
    refinement_revocations = sum(
        row.get("refinement_revocations", 0) for row in rows.values()
    )
    consequence_yield = (
        total_distinct
        + 0.25 * total_edges
        + 100.0 * total_levels
    ) / max(1, total_steps)
    effective_coverage = total_edges + structural_pruned
    effective_consequence_yield = (
        total_distinct
        + 0.25 * effective_coverage
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
        "structural_pruned_actions": structural_pruned,
        "compiled_noop_groups": compiled_noop_groups,
        "representation_refinement_uses": representation_refinement_uses,
        "refined_schema_count": refined_schema_count,
        "active_refinement_count": active_refinement_count,
        "refinement_revocations": refinement_revocations,
        "effective_coverage": effective_coverage,
        "effective_consequence_yield_per_step": effective_consequence_yield,
        "metrics": dict(metrics),
        "games": rows,
        "trace_head": trace,
    }


def compare(arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    seq = arms["sequential_local"]
    market = arms["market_local"]
    flash = arms["flash_validated_refinement"]

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
            "structural_pruned_actions": flash.get(
                "structural_pruned_actions", 0
            ),
            "compiled_noop_groups": flash.get(
                "compiled_noop_groups", 0
            ),
            "representation_refinement_uses": flash.get(
                "representation_refinement_uses", 0
            ),
            "refined_schema_count": flash.get(
                "refined_schema_count", 0
            ),
            "active_refinement_count": flash.get(
                "active_refinement_count", 0
            ),
            "refinement_revocations": flash.get(
                "refinement_revocations", 0
            ),
            "effective_coverage_delta": (
                flash.get("effective_coverage", flash["total_exact_edge_keys"])
                - market.get("effective_coverage", market["total_exact_edge_keys"])
            ),
            "effective_consequence_yield_ratio": (
                flash.get(
                    "effective_consequence_yield_per_step",
                    flash["consequence_yield_per_step"],
                )
                / max(
                    market.get(
                        "effective_consequence_yield_per_step",
                        market["consequence_yield_per_step"],
                    ),
                    1e-12,
                )
            ),
            "cross_game_revaluations": flash["metrics"].get(
                "cross_game_revaluations", 0
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

    arms["flash_validated_refinement"] = run_market(
        module,
        manifest,
        shared=True,
    )
    print(
        "FLASH_ARM="
        + json.dumps(
            {
                k: v
                for k, v in arms["flash_validated_refinement"].items()
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
        "schema": "arc3-global-flash-closure-v7",
        "interpretation": (
            "three-game public developmental falsification: cross-game contradiction may "
            "propose a finer representation, but activation requires destination-local "
            "impurity reduction and is continuously revocable"
        ),
        "claim_boundary": (
            "cross-game contradiction only nominates a deterministic public-geometry split; "
            "the destination must have at least six exact observations, multiple local "
            "consequences and at least 0.10 impurity reduction before activation; "
            "no foreign outcome is installed as a destination fact"
        ),
        "games": list(GAMES),
        "total_budget_per_arm": TOTAL_BUDGET,
        "warmup_per_game": WARMUP_PER_GAME,
        "minimum_game_share": MIN_GAME_SHARE,
        "arms": arms,
        "comparison": comparison,
        "hypothesis_status": {
            "flash_protected_not_worse_than_sequential": all(
                arms["flash_validated_refinement"]["games"][game]["max_level"]
                >= arms["sequential_local"]["games"][game]["max_level"]
                for game in GAMES
            ),
            "flash_consequence_yield_gt_sequential": (
                arms["flash_validated_refinement"]["consequence_yield_per_step"]
                > arms["sequential_local"]["consequence_yield_per_step"]
            ),
            "flash_cross_game_revaluation_activated": (
                arms["flash_validated_refinement"]["metrics"].get(
                    "cross_game_revaluations", 0
                ) > 0
            ),
            "flash_destination_validated_refinement_activated": (
                arms["flash_validated_refinement"].get(
                    "representation_refinement_uses", 0
                ) > 0
            ),
            "flash_consequence_yield_ge_market": (
                arms["flash_validated_refinement"]["consequence_yield_per_step"]
                >= arms["market_local"]["consequence_yield_per_step"]
            ),
            "flash_effective_yield_gt_market": (
                arms["flash_validated_refinement"]["effective_consequence_yield_per_step"]
                > arms["market_local"]["effective_consequence_yield_per_step"]
            ),
            "flash_zero_change_le_market": (
                arms["flash_validated_refinement"]["zero_change_steps"]
                <= arms["market_local"]["zero_change_steps"]
            ),
            "flash_protected_not_worse_than_market": all(
                arms["flash_validated_refinement"]["games"][game]["max_level"]
                >= arms["market_local"]["games"][game]["max_level"]
                for game in GAMES
            ),
        },
    }
    audit.write_json(OUT / "global-flash-closure-v7.json", report)

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
                            "structural_pruned_actions",
                            "compiled_noop_groups",
                            "representation_refinement_uses",
                            "refined_schema_count",
                            "active_refinement_count",
                            "refinement_revocations",
                            "effective_coverage",
                            "effective_consequence_yield_per_step",
                        )
                    }
                    for name, row in arms.items()
                },
            },
            sort_keys=True,
        ),
        flush=True,
    )
    print("ARC3_GLOBAL_FLASH_CLOSURE_V7=PASS", flush=True)


if __name__ == "__main__":
    main()
