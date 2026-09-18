"""Dynamic exact-ledger performance compounding for ls20.

The static V4 ledger planner reduced no-change actions sharply and reached many
states absent from the frozen baseline, but once it crossed the persisted ledger
boundary it reverted to the old heuristic.

This version makes the exact ledger developmental:

- every observed public state is inserted with its exact protected contract;
- every executed primitive action is recorded as an exact source/action/target edge;
- conflicting successors are retained as ambiguous and are never used for planning;
- every newly discovered exact edge immediately stops being an "unknown";
- after one 400-action episode, the enlarged ledger is retained and the next
  episode starts from RESET with strictly more exact evidence.

Four generations alternate low/high unresolved-action ordering and nearest /
max-unresolved boundary routing. The same mutable exact ledger is shared across
all generations.

No visual factor or cross-state inference is introduced. The only reusable
knowledge is exact public-state/action evidence.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import sys
from types import MethodType
from typing import Any

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ls20-dynamic-ledger-performance-results"
AGENT = OUT / "agent.py"
LEDGER = OUT / "exact-replay-ledger.json"

EXPECTED_AGENT_SHA = "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead"
EXPECTED_GAME = "ls20-9607627b"
EXPECTED_NODES = 1952
EXPECTED_EDGES = 5650

STRATEGIES = (
    "nearest_min",
    "nearest_max",
    "maxmissing_min",
    "maxmissing_max",
)


def legal_actions(obs) -> tuple[int, ...]:
    return tuple(sorted({int(value) for value in obs.available_actions}))


def protected(obs) -> tuple[str, int]:
    return (str(obs.state), int(obs.levels_completed))


class DynamicExactLedger:
    def __init__(self, payload: dict[str, Any]):
        if payload.get("schema") != "arc3-exact-replay-ledger-v1":
            raise AssertionError("unexpected replay-ledger schema")
        meta = payload.get("metadata", {})
        if meta.get("agent_sha256") != EXPECTED_AGENT_SHA:
            raise AssertionError("replay-ledger agent hash mismatch")
        if meta.get("game_id") != EXPECTED_GAME:
            raise AssertionError("replay-ledger game mismatch")
        if len(payload.get("nodes", {})) != EXPECTED_NODES:
            raise AssertionError("replay-ledger node count changed")
        if len(payload.get("edges", [])) != EXPECTED_EDGES:
            raise AssertionError("replay-ledger edge count changed")

        self.source_metadata = dict(meta)
        self.nodes: dict[str, dict[str, Any]] = {
            str(node): {
                "protected": list(row["protected"]),
                "legal_actions": [int(action) for action in row["legal_actions"]],
            }
            for node, row in payload["nodes"].items()
        }
        self.prefixes: dict[str, list[list[int | None]]] = {
            str(node): [list(action) for action in rows]
            for node, rows in payload.get("prefixes", {}).items()
        }
        self.edge_records: list[dict[str, Any]] = [
            {
                "source": str(row["source"]),
                "action": int(row["action"]),
                "outcome": list(row["outcome"]) if isinstance(row["outcome"], list) else row["outcome"],
                "target": str(row["target"]),
            }
            for row in payload["edges"]
        ]

        self._rows: dict[tuple[str, int], set[tuple[tuple[Any, ...], str]]] = defaultdict(set)
        for row in self.edge_records:
            outcome = tuple(row["outcome"]) if isinstance(row["outcome"], list) else (row["outcome"],)
            self._rows[(row["source"], int(row["action"]))].add(
                (outcome, row["target"])
            )

        self.successor: dict[tuple[str, int], str] = {}
        self.ambiguous: set[tuple[str, int]] = set()
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self.successor.clear()
        self.ambiguous.clear()
        for key, rows in self._rows.items():
            if len(rows) == 1:
                _outcome, target = next(iter(rows))
                self.successor[key] = str(target)
            else:
                self.ambiguous.add(key)

    def add_node(
        self,
        node: str,
        *,
        protected_value: tuple[str, int],
        legal: tuple[int, ...],
        prefix: tuple[tuple[int, int | None, int | None], ...] | None = None,
    ) -> bool:
        node = str(node)
        row = {
            "protected": [str(protected_value[0]), int(protected_value[1])],
            "legal_actions": [int(action) for action in sorted(set(legal))],
        }
        old = self.nodes.get(node)
        if old is not None:
            if old != row:
                raise AssertionError("same exact digest acquired conflicting public contract")
            if prefix is not None:
                self.note_prefix(node, prefix)
            return False
        self.nodes[node] = row
        if prefix is not None:
            self.note_prefix(node, prefix)
        return True

    def note_prefix(
        self,
        node: str,
        prefix: tuple[tuple[int, int | None, int | None], ...],
    ) -> None:
        encoded = [
            [
                int(action_id),
                None if x is None else int(x),
                None if y is None else int(y),
            ]
            for action_id, x, y in prefix
        ]
        old = self.prefixes.get(str(node))
        if old is None or len(encoded) < len(old):
            self.prefixes[str(node)] = encoded

    def add_edge(
        self,
        source: str,
        action: int,
        target: str,
        outcome: tuple[str, int],
    ) -> tuple[bool, bool]:
        source = str(source)
        target = str(target)
        key = (source, int(action))
        frozen = ((str(outcome[0]), int(outcome[1])), target)
        before = set(self._rows.get(key, set()))
        self._rows[key].add(frozen)

        new_record = frozen not in before
        if new_record:
            self.edge_records.append({
                "source": source,
                "action": int(action),
                "outcome": [str(outcome[0]), int(outcome[1])],
                "target": target,
            })

        rows = self._rows[key]
        became_ambiguous = len(rows) > 1 and key not in self.ambiguous
        if len(rows) == 1:
            self.successor[key] = target
            self.ambiguous.discard(key)
        else:
            self.successor.pop(key, None)
            self.ambiguous.add(key)
        return new_record, became_ambiguous

    def legal(self, context: str) -> tuple[int, ...]:
        row = self.nodes.get(str(context))
        if not row:
            return ()
        return tuple(int(action) for action in row["legal_actions"])

    def protected(self, context: str) -> tuple[Any, ...]:
        row = self.nodes.get(str(context))
        if not row:
            return ()
        return tuple(row["protected"])

    def missing(
        self,
        context: str,
        attempted: set[tuple[str, int]],
    ) -> tuple[int, ...]:
        context = str(context)
        return tuple(
            action
            for action in self.legal(context)
            if (context, action) not in self.successor
            and (context, action) not in self.ambiguous
            and (context, action) not in attempted
        )

    def deterministic_successors(self, context: str):
        context = str(context)
        return tuple(
            (action, self.successor[(context, action)])
            for action in self.legal(context)
            if (context, action) in self.successor
        )

    def export(self, *, generation_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schema": "arc3-exact-replay-ledger-v1",
            "metadata": {
                **self.source_metadata,
                "source_branch": "arc3-ls20-dynamic-ledger-performance-v1",
                "parent_source_branch": self.source_metadata.get("source_branch"),
                "dynamic_generation_count": len(generation_rows),
                "dynamic_generations": generation_rows,
                "agent_sha256": EXPECTED_AGENT_SHA,
                "game_id": EXPECTED_GAME,
            },
            "nodes": self.nodes,
            "edges": self.edge_records,
            "prefixes": self.prefixes,
        }


def load_ledger() -> DynamicExactLedger:
    return DynamicExactLedger(json.loads(LEDGER.read_text()))


def install_planner(
    controller,
    ledger: DynamicExactLedger,
    counters: Counter,
    strategy: str,
):
    original = controller._select_probe
    controller._dynamic_attempted: set[tuple[str, int]] = set()
    controller._dynamic_context_visits = Counter()

    def select(self, obs, catalog):
        current = str(obs.evidence_sha256)
        self._dynamic_context_visits[current] += 1
        token_by_action = {
            int(token.action_id): token
            for token in catalog
            if token.x is None and token.y is None
        }

        if current not in ledger.nodes:
            counters["unindexed_context"] += 1
            return original(obs, catalog)

        counters["indexed_context"] += 1

        missing = [
            action
            for action in ledger.missing(
                current,
                self._dynamic_attempted,
            )
            if action in token_by_action
        ]
        if missing:
            action = max(missing) if strategy.endswith("_max") else min(missing)
            self._dynamic_attempted.add((current, action))
            counters["boundary_local"] += 1
            return self._token(
                (action, None, None),
                "dynamic_boundary_local",
            )

        queue = deque([(current, None, 0)])
        seen = {current}
        candidates = []

        while queue and len(seen) <= len(ledger.nodes):
            context, first, depth = queue.popleft()
            unresolved = ledger.missing(
                context,
                self._dynamic_attempted,
            )
            if first is not None and unresolved and first in token_by_action:
                prefix_depth = len(ledger.prefixes.get(context, ()))
                candidates.append((
                    context,
                    first,
                    depth,
                    tuple(unresolved),
                    prefix_depth,
                ))
                if strategy.startswith("nearest_"):
                    break

            for action, target in ledger.deterministic_successors(context):
                if context == current and action not in token_by_action:
                    continue
                if target in seen:
                    continue
                target_protected = ledger.protected(target)
                if target_protected and str(target_protected[0]) in ("WIN", "GAME_OVER"):
                    continue
                seen.add(target)
                queue.append((
                    target,
                    action if first is None else first,
                    depth + 1,
                ))

        if candidates:
            if strategy.startswith("maxmissing_"):
                candidates.sort(
                    key=lambda row: (-len(row[3]), row[2], -row[4], row[0])
                )
            else:
                candidates.sort(key=lambda row: (row[2], row[0]))
            _context, first, depth, unresolved, _prefix_depth = candidates[0]
            counters["boundary_route"] += 1
            counters["boundary_route_depth_sum"] += depth
            counters["boundary_target_missing_sum"] += len(unresolved)
            return self._token(
                (first, None, None),
                "dynamic_boundary_route",
            )

        moving = []
        for action, token in token_by_action.items():
            target = ledger.successor.get((current, action))
            if target is None or target == current:
                continue
            moving.append((
                int(self._dynamic_context_visits.get(target, 0)),
                action,
                target,
                token,
            ))
        if moving:
            moving.sort(key=lambda row: (row[0], row[1], row[2]))
            _visits, action, _target, _token = moving[0]
            counters["known_route"] += 1
            return self._token(
                (action, None, None),
                "dynamic_known_route",
            )

        counters["fallback"] += 1
        return original(obs, catalog)

    controller._select_probe = MethodType(select, controller)


def run_generation(
    module,
    game_id: str,
    envdir: str,
    max_actions: int,
    ledger: DynamicExactLedger,
    *,
    strategy: str,
    generation: int,
):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable")

    policy = module.MyAgent(
        card_id=f"ls20-dynamic-ledger-g{generation}",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    install_planner(policy.controller, ledger, counters, strategy)

    latest = policy._convert_raw_frame_data(env.observation_space)
    obs = module.normalize_frame(latest)
    digest = str(obs.evidence_sha256)
    prefix: tuple[tuple[int, int | None, int | None], ...] = ()
    ledger.add_node(
        digest,
        protected_value=protected(obs),
        legal=legal_actions(obs),
        prefix=prefix,
    )

    frames = [latest]
    states = {digest}
    actions = []
    sources = Counter()
    zero_change = 0
    max_level = int(obs.levels_completed)
    milestones = []

    start_nodes = len(ledger.nodes)
    start_edges = len(ledger.edge_records)
    new_nodes = 0
    new_edges = 0
    new_ambiguous = 0

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_obs = module.normalize_frame(before)
        before_digest = str(before_obs.evidence_sha256)
        before_level = int(before_obs.levels_completed)

        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )
        if key[1] is not None or key[2] is not None:
            raise AssertionError("ls20 dynamic ledger expected primitive interventions")

        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        after_obs = module.normalize_frame(latest)
        after_digest = str(after_obs.evidence_sha256)
        states.add(after_digest)

        delta = int(after_obs.levels_completed) - before_level
        outcome = (
            "LEVEL_INCREMENT" if delta > 0 else str(after_obs.state),
            int(delta),
        )

        prefix = prefix + (key,)
        if ledger.add_node(
            after_digest,
            protected_value=protected(after_obs),
            legal=legal_actions(after_obs),
            prefix=prefix,
        ):
            new_nodes += 1

        added, ambiguous = ledger.add_edge(
            before_digest,
            int(key[0]),
            after_digest,
            outcome,
        )
        new_edges += int(added)
        new_ambiguous += int(ambiguous)

        zero_change += int(before_digest == after_digest)
        actions.append(key)
        sources[source] += 1

        if int(after_obs.levels_completed) > max_level:
            max_level = int(after_obs.levels_completed)
            milestones.append({
                "level": max_level,
                "actions": len(actions) + 1,
            })

        frames.append(latest)

    arc.close_scorecard()
    return {
        "generation": generation,
        "strategy": strategy,
        "actions": len(actions) + 1,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "unique_state_count": len(states),
        "distinct_actions": len(set(actions)),
        "zero_observation_change": zero_change,
        "source_counts": dict(sources),
        "planner": dict(counters),
        "new_nodes": new_nodes,
        "new_edges": new_edges,
        "new_ambiguous_edges": new_ambiguous,
        "ledger_nodes_before": start_nodes,
        "ledger_nodes_after": len(ledger.nodes),
        "ledger_edges_before": start_edges,
        "ledger_edges_after": len(ledger.edge_records),
    }


def run_baseline(module, game_id: str, envdir: str, max_actions: int):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable")

    policy = module.MyAgent(
        card_id="ls20-dynamic-ledger-baseline",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    states = set()
    actions = []
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break
        before = latest
        before_digest = str(module.normalize_frame(before).evidence_sha256)
        states.add(before_digest)
        before_level = int(before.levels_completed)

        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )
        raw = env.step(chosen, data=data, reasoning={"source": "baseline"})
        latest = policy._convert_raw_frame_data(raw)
        after_digest = str(module.normalize_frame(latest).evidence_sha256)
        states.add(after_digest)
        zero_change += int(before_digest == after_digest)
        actions.append(key)

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({
                "level": max_level,
                "actions": len(actions) + 1,
            })
        frames.append(latest)

    arc.close_scorecard()
    return {
        "actions": len(actions) + 1,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "unique_state_count": len(states),
        "distinct_actions": len(set(actions)),
        "zero_observation_change": zero_change,
    }


def main():
    ledger = load_ledger()

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"] == EXPECTED_GAME
    )

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    baseline = run_baseline(
        module,
        game["game_id"],
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    if baseline["max_levels"] != 0:
        raise AssertionError("frozen ls20 baseline changed")

    initial_nodes = len(ledger.nodes)
    initial_edges = len(ledger.edge_records)
    generations = []

    for index, strategy in enumerate(STRATEGIES, start=1):
        row = run_generation(
            module,
            game["game_id"],
            manifest["environments_dir"],
            manifest["max_actions"],
            ledger,
            strategy=strategy,
            generation=index,
        )
        if row["max_levels"] < baseline["max_levels"]:
            raise AssertionError("dynamic ledger generation regressed protected progress")
        generations.append(row)
        print(
            "DYNAMIC_LEDGER_GENERATION="
            + json.dumps(row, sort_keys=True),
            flush=True,
        )

    augmented = ledger.export(generation_rows=generations)
    audit.write_json(OUT / "augmented-exact-replay-ledger.json", augmented)

    report = {
        "interpretation": (
            "performance compounding by retaining every exact transition from "
            "successive ledger-planned ls20 episodes and reusing the enlarged "
            "graph in the next RESET episode"
        ),
        "claim_boundary": (
            "only exact public state/action evidence is retained; conflicting "
            "successors are ambiguous and excluded from deterministic planning"
        ),
        "baseline": baseline,
        "initial_ledger": {
            "nodes": initial_nodes,
            "edges": initial_edges,
        },
        "generations": generations,
        "final_ledger": {
            "nodes": len(ledger.nodes),
            "edges": len(ledger.edge_records),
            "deterministic_edges": len(ledger.successor),
            "ambiguous_edges": len(ledger.ambiguous),
            "node_growth": len(ledger.nodes) - initial_nodes,
            "edge_growth": len(ledger.edge_records) - initial_edges,
        },
        "max_level_reached": max(row["max_levels"] for row in generations),
        "total_new_nodes": sum(row["new_nodes"] for row in generations),
        "total_new_edges": sum(row["new_edges"] for row in generations),
        "total_zero_change_actions": sum(
            row["zero_observation_change"] for row in generations
        ),
    }

    audit.write_json(
        OUT / "ls20-dynamic-ledger-performance.json",
        report,
    )
    print(
        "LS20_DYNAMIC_LEDGER_PERFORMANCE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_LS20_DYNAMIC_LEDGER_PERFORMANCE=PASS", flush=True)


if __name__ == "__main__":
    main()
