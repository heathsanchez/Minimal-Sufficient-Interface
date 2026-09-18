"""Use the persisted ls20 exact replay ledger as a performance planner.

The V4 explore/harvest run produced a pinned exact ledger with:
- raw public state digests,
- exact primitive-action transitions,
- legal primitive action contracts,
- exact reset replay prefixes.

This experiment does not rebuild that graph. The workflow downloads the pinned
artifact, verifies its archive SHA-256, and supplies the ledger here.

At runtime the planner:
1. if the current exact state has a legal primitive action absent from the
   ledger, take one;
2. otherwise follow verified deterministic ledger edges along the shortest
   path to the nearest state that still has an unobserved legal action;
3. if no unresolved boundary is reachable, prefer a verified non-self edge
   leading to the least revisited exact context;
4. otherwise fall back to the unchanged frozen controller.

A boundary action is marked attempted immediately so repeated visits do not pay
for the same unresolved intervention twice in one run.

All planning keys are exact raw public digests and exact primitive actions.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ls20-ledger-performance-portfolio-results"
AGENT = OUT / "agent.py"
LEDGER = OUT / "exact-replay-ledger.json"

EXPECTED_AGENT_SHA = "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead"
EXPECTED_GAME = "ls20-9607627b"
EXPECTED_NODES = 1952
EXPECTED_EDGES = 5650


def load_ledger() -> dict:
    data = json.loads(LEDGER.read_text())
    if data.get("schema") != "arc3-exact-replay-ledger-v1":
        raise AssertionError("unexpected replay-ledger schema")
    meta = data.get("metadata", {})
    if meta.get("agent_sha256") != EXPECTED_AGENT_SHA:
        raise AssertionError("replay-ledger agent hash mismatch")
    if meta.get("game_id") != EXPECTED_GAME:
        raise AssertionError("replay-ledger game mismatch")
    if len(data.get("nodes", {})) != EXPECTED_NODES:
        raise AssertionError("replay-ledger node count changed")
    if len(data.get("edges", [])) != EXPECTED_EDGES:
        raise AssertionError("replay-ledger edge count changed")
    return data


class ExactLedgerGraph:
    def __init__(self, ledger: dict):
        self.nodes = ledger["nodes"]
        self.prefixes = ledger["prefixes"]
        edge_rows = defaultdict(lambda: defaultdict(list))
        for row in ledger["edges"]:
            edge_rows[str(row["source"])][int(row["action"])].append(row)

        self.successor: dict[tuple[str, int], str] = {}
        self.ambiguous: set[tuple[str, int]] = set()
        self.reverse: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for source, by_action in edge_rows.items():
            for action, rows in by_action.items():
                targets = {
                    (
                        tuple(row["outcome"])
                        if isinstance(row["outcome"], list)
                        else row["outcome"],
                        str(row["target"]),
                    )
                    for row in rows
                }
                if len(targets) != 1:
                    self.ambiguous.add((source, action))
                    continue
                _outcome, target = next(iter(targets))
                self.successor[(source, action)] = target
                if target != source:
                    self.reverse[target].append((source, action))

    def legal_actions(self, context: str) -> tuple[int, ...]:
        row = self.nodes.get(str(context))
        if not row:
            return ()
        return tuple(int(action) for action in row.get("legal_actions", ()))

    def protected(self, context: str):
        row = self.nodes.get(str(context))
        return tuple(row.get("protected", ())) if row else ()

    def known_actions(self, context: str) -> set[int]:
        return {
            action
            for (source, action), _target in self.successor.items()
            if source == str(context)
        }

    def missing_actions(
        self,
        context: str,
        attempted: set[tuple[str, int]],
    ) -> tuple[int, ...]:
        legal = self.legal_actions(context)
        if not legal:
            return ()
        return tuple(
            action
            for action in legal
            if (str(context), int(action)) not in self.successor
            and (str(context), int(action)) not in attempted
        )

    def deterministic_successors(self, context: str):
        rows = []
        for action in self.legal_actions(context):
            target = self.successor.get((str(context), int(action)))
            if target is None:
                continue
            rows.append((int(action), str(target)))
        return tuple(rows)


def install_ledger_planner(controller, graph: ExactLedgerGraph, counters: Counter, strategy: str):
    original = controller._select_probe
    controller._ledger_attempted_missing: set[tuple[str, int]] = set()
    controller._ledger_context_visits = Counter()

    def select(self, obs, catalog):
        current = str(obs.evidence_sha256)
        self._ledger_context_visits[current] += 1

        token_by_action = {
            int(token.action_id): token
            for token in catalog
            if token.x is None and token.y is None
        }

        if current not in graph.nodes:
            counters["outside_ledger"] += 1
            return original(obs, catalog)

        counters["ledger_context"] += 1

        # Spend a new exact intervention at the current boundary first.
        missing = [
            action
            for action in graph.missing_actions(
                current,
                self._ledger_attempted_missing,
            )
            if action in token_by_action
        ]
        if missing:
            action = max(missing) if strategy.endswith("_max") else min(missing)
            self._ledger_attempted_missing.add((current, action))
            counters["boundary_local"] += 1
            return self._token(
                (action, None, None),
                "ledger_boundary_local",
            )

        # Search the retained graph for unresolved exact boundaries.
        queue = deque([(current, None, 0)])
        seen = {current}
        candidates = []
        while queue and len(seen) <= len(graph.nodes):
            context, first, depth = queue.popleft()
            unresolved = graph.missing_actions(
                context,
                self._ledger_attempted_missing,
            )
            if first is not None and unresolved and first in token_by_action:
                candidates.append((
                    context,
                    first,
                    depth,
                    tuple(unresolved),
                    len(graph.prefixes.get(context, ())),
                ))
                if strategy.startswith("nearest_"):
                    break

            for action, target in graph.deterministic_successors(context):
                if context == current and action not in token_by_action:
                    continue
                if target in seen:
                    continue
                protected = graph.protected(target)
                if protected and str(protected[0]) in ("WIN", "GAME_OVER"):
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
            context, first, depth, unresolved, _prefix_depth = candidates[0]
            counters["boundary_route"] += 1
            counters["boundary_route_depth_sum"] += depth
            counters["boundary_target_missing_sum"] += len(unresolved)
            return self._token(
                (first, None, None),
                "ledger_boundary_route",
            )

        # No unresolved boundary is reachable in the retained graph. Prefer a
        # verified state-changing edge toward the least revisited context.
        moving = []
        for action, token in token_by_action.items():
            target = graph.successor.get((current, action))
            if target is None or target == current:
                continue
            moving.append((
                int(self._ledger_context_visits.get(target, 0)),
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
                "ledger_known_route",
            )

        counters["fallback"] += 1
        return original(obs, catalog)

    controller._select_probe = MethodType(select, controller)


def run_arm(module, game_id, envdir, max_actions, *, graph=None, strategy="nearest_min"):
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
        card_id="ls20-ledger-performance",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    if graph is not None:
        install_ledger_planner(policy.controller, graph, counters, strategy)

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    states = set()
    actions = []
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []
    first_outside_ledger = None

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        states.add(before_digest)
        if graph is not None and before_digest not in graph.nodes and first_outside_ledger is None:
            first_outside_ledger = len(actions) + 1

        before_level = int(before.levels_completed)
        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )
        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        after_digest = module.normalize_frame(latest).evidence_sha256
        states.add(after_digest)
        zero_change += int(before_digest == after_digest)
        actions.append(key)
        sources[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({
                "level": max_level,
                "actions": len(actions) + 1,
            })

        frames.append(latest)

    arc.close_scorecard()
    return {
        "actions_raw": actions,
        "states": states,
        "stats": {
            "actions": len(actions) + 1,
            "unique_state_count": len(states),
            "distinct_actions": len(set(actions)),
            "zero_observation_change": zero_change,
            "max_levels": max_level,
            "milestones": milestones,
            "final_state": audit.state_name(latest),
            "source_counts": dict(sources),
            "first_outside_ledger_action": first_outside_ledger,
            "planner": dict(counters),
        },
    }


def main():
    ledger = load_ledger()
    graph = ExactLedgerGraph(ledger)

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"] == EXPECTED_GAME
    )

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    baseline = run_arm(
        module,
        game["game_id"],
        manifest["environments_dir"],
        manifest["max_actions"],
        graph=None,
    )
    strategies = (
        "nearest_min",
        "nearest_max",
        "maxmissing_min",
        "maxmissing_max",
    )
    arms = {}
    for strategy in strategies:
        arms[strategy] = run_arm(
            module,
            game["game_id"],
            manifest["environments_dir"],
            manifest["max_actions"],
            graph=graph,
            strategy=strategy,
        )
        if arms[strategy]["stats"]["max_levels"] < baseline["stats"]["max_levels"]:
            raise AssertionError(f"{strategy} regressed protected progress")
        if sum(arms[strategy]["stats"]["planner"].values()) < 1:
            raise AssertionError(f"{strategy} planner never activated")

    if baseline["stats"]["max_levels"] != 0:
        raise AssertionError("frozen ls20 baseline changed")

    report = {
        "interpretation": (
            "score-facing portfolio over the persisted exact ls20 replay ledger; "
            "nearest-boundary and max-unresolved-boundary policies are crossed "
            "with low/high missing-action ordering"
        ),
        "claim_boundary": (
            "the ledger is pinned to the exact public game and frozen agent; "
            "no visual or cross-state inferred abstraction is used"
        ),
        "ledger": {
            "source_branch": ledger["metadata"].get("source_branch"),
            "nodes": len(ledger["nodes"]),
            "edges": len(ledger["edges"]),
            "prefixes": len(ledger["prefixes"]),
            "baseline_probe_count": ledger["metadata"].get("baseline_probe_count"),
            "exploration_extra_probes": ledger["metadata"].get("exploration_extra_probes"),
            "reinvestment_extra_probes": ledger["metadata"].get("reinvestment_extra_probes"),
        },
        "baseline": baseline["stats"],
        "arms": {
            strategy: {
                "stats": row["stats"],
                "performance_delta": {
                    "levels": row["stats"]["max_levels"] - baseline["stats"]["max_levels"],
                    "unique_states": row["stats"]["unique_state_count"] - baseline["stats"]["unique_state_count"],
                    "zero_change_actions": row["stats"]["zero_observation_change"] - baseline["stats"]["zero_observation_change"],
                },
                "novel_states_vs_baseline": len(row["states"] - baseline["states"]),
                "novel_actions_vs_baseline": [
                    list(action)
                    for action in sorted(
                        set(row["actions_raw"]) - set(baseline["actions_raw"])
                    )
                ],
            }
            for strategy, row in arms.items()
        },
        "max_level_reached": max(row["stats"]["max_levels"] for row in arms.values()),
        "union_states": len(set().union(*(row["states"] for row in arms.values()))),
        "union_novel_states_vs_baseline": len(
            set().union(*(row["states"] for row in arms.values())) - baseline["states"]
        ),
    }

    audit.write_json(
        OUT / "ls20-ledger-performance-portfolio.json",
        report,
    )
    print(
        "LS20_LEDGER_PERFORMANCE_PORTFOLIO_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_LS20_LEDGER_PERFORMANCE_PORTFOLIO=PASS", flush=True)


if __name__ == "__main__":
    main()
