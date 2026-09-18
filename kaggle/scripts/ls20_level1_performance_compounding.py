"""Level-by-level performance compounding for ls20.

The augmented exact ledger has already converted Level-0 discovery into a
live-replay-verified compiled macro:

    RESET -> L1 in 56 executed primitive actions (reported L1@57)

The frozen baseline never reached L1 within 400 actions. The dynamic discovery
run first found L1@67; cross-generation exact-edge composition then shortened it
to L1@57.

This experiment moves the developmental frontier forward permanently. Across
successive generations it:

1. finds the highest protected level currently present in the exact ledger;
2. composes the shortest deterministic RESET route to that level;
3. live-replays and checks every intermediate digest exactly;
4. spends the remainder of the same 399-executed-action envelope exploring
   from that compiled level with a quotient-independent exact-ledger planner;
5. retains every newly observed exact state/action edge in the same ledger;
6. recomputes the highest level and shortest compiled route for the next
   generation.

Thus, if a generation discovers L2, the next generation no longer rediscovers
L0 or L1: it compiles the shortest verified route to L2 and spends the saved
budget beyond it.

No visual abstraction or inferred cross-state law is used. Ambiguous exact
edges are excluded from route composition.
"""
from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ls20-level1-performance-compounding-results"
AGENT = OUT / "agent.py"
LEDGER = OUT / "augmented-exact-replay-ledger.json"

sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))
import ls20_dynamic_ledger_performance as dyn

EXPECTED_AGENT_SHA = dyn.EXPECTED_AGENT_SHA
EXPECTED_GAME = dyn.EXPECTED_GAME
INITIAL_NODES = 2921
INITIAL_EDGES = 7018
EXECUTED_ACTION_BUDGET = 399
GENERATIONS = 8
STRATEGIES = (
    "maxmissing_min",
    "maxmissing_max",
    "nearest_min",
    "nearest_max",
    "maxmissing_min",
    "nearest_min",
    "maxmissing_max",
    "nearest_max",
)


def load_ledger():
    payload = json.loads(LEDGER.read_text())
    meta = payload.get("metadata", {})
    if payload.get("schema") != "arc3-exact-replay-ledger-v1":
        raise AssertionError("unexpected augmented replay-ledger schema")
    if meta.get("agent_sha256") != EXPECTED_AGENT_SHA:
        raise AssertionError("augmented ledger agent mismatch")
    if meta.get("game_id") != EXPECTED_GAME:
        raise AssertionError("augmented ledger game mismatch")
    if len(payload.get("nodes", {})) != INITIAL_NODES:
        raise AssertionError("augmented ledger node count changed")
    if len(payload.get("edges", [])) != INITIAL_EDGES:
        raise AssertionError("augmented ledger edge count changed")

    dyn.EXPECTED_NODES = INITIAL_NODES
    dyn.EXPECTED_EDGES = INITIAL_EDGES
    ledger = dyn.DynamicExactLedger(payload)
    return payload, ledger


def root_node(ledger):
    roots = [
        node
        for node, prefix in ledger.prefixes.items()
        if len(prefix) == 0
    ]
    if len(roots) != 1:
        raise AssertionError("expected one RESET node")
    return roots[0]


def highest_ledger_level(ledger):
    return max(
        int(row["protected"][1])
        for row in ledger.nodes.values()
    )


def shortest_route_to_level(ledger, target_level):
    root = root_node(ledger)
    queue = deque([(root, ())])
    seen = {root}

    while queue:
        node, actions = queue.popleft()
        protected = ledger.nodes[node]["protected"]
        if int(protected[1]) >= int(target_level):
            return {
                "root": root,
                "target": node,
                "target_protected": list(protected),
                "actions": list(actions),
            }

        for action in ledger.legal(node):
            target = ledger.successor.get((node, int(action)))
            if target is None or target in seen:
                continue
            # Exact terminal failures are not useful waypoints unless they
            # themselves satisfy the requested protected level.
            target_protected = ledger.protected(target)
            if (
                target_protected
                and str(target_protected[0]) in ("WIN", "GAME_OVER")
                and int(target_protected[1]) < int(target_level)
            ):
                continue
            seen.add(target)
            queue.append((target, actions + (int(action),)))

    raise AssertionError(
        f"no deterministic RESET route to ledger level {target_level}"
    )


def make_action(action_id):
    from arcengine import GameAction

    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        raise AssertionError("ls20 compiled route expected primitive actions")
    return action, action.action_data.model_dump()


def replay_route(module, game_id, envdir, ledger, route):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable")

    adapter = module.MyAgent(
        card_id="level-compounding-replay",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )

    latest = adapter._convert_raw_frame_data(env.observation_space)
    digest = str(module.normalize_frame(latest).evidence_sha256)
    if digest != route["root"]:
        arc.close_scorecard()
        raise AssertionError("RESET digest mismatches retained ledger")

    observed = [digest]
    expected = [digest]
    node = digest

    for action_id in route["actions"]:
        target = ledger.successor.get((node, int(action_id)))
        if target is None:
            arc.close_scorecard()
            raise AssertionError("compiled route contains non-deterministic edge")
        expected.append(target)

        action, data = make_action(action_id)
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "compiled_level_route"},
        )
        latest = adapter._convert_raw_frame_data(raw)
        digest = str(module.normalize_frame(latest).evidence_sha256)
        observed.append(digest)

        if digest != target:
            arc.close_scorecard()
            raise AssertionError(
                "compiled route replay diverged from exact ledger"
            )
        node = target

    if observed != expected:
        arc.close_scorecard()
        raise AssertionError("compiled route intermediate digest mismatch")

    if int(latest.levels_completed) < int(route["target_protected"][1]):
        arc.close_scorecard()
        raise AssertionError("compiled route failed protected-level contract")

    return arc, env, latest


def continue_generation(
    module,
    env,
    latest,
    ledger,
    *,
    compiled_actions,
    strategy,
    generation,
):
    policy = module.MyAgent(
        card_id=f"level-compounding-g{generation}",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    dyn.install_planner(
        policy.controller,
        ledger,
        counters,
        strategy,
    )

    compiled_prefix = tuple(
        (int(action_id), None, None)
        for action_id in compiled_actions
    )
    prefix = compiled_prefix

    latest_obs = module.normalize_frame(latest)
    start_digest = str(latest_obs.evidence_sha256)
    ledger.note_prefix(start_digest, prefix)

    frames = [latest]
    states = {start_digest}
    actions = []
    zero_change = 0
    milestones = []
    max_level = int(latest.levels_completed)

    start_nodes = len(ledger.nodes)
    start_edges = len(ledger.edge_records)
    new_nodes = 0
    new_edges = 0
    new_ambiguous = 0

    remaining = max(
        0,
        EXECUTED_ACTION_BUDGET - len(compiled_actions),
    )

    while len(actions) < remaining and audit.state_name(latest) != "WIN":
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
            raise AssertionError("ls20 level compounding expected primitive actions")

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
            protected_value=dyn.protected(after_obs),
            legal=dyn.legal_actions(after_obs),
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

        if int(after_obs.levels_completed) > max_level:
            max_level = int(after_obs.levels_completed)
            milestones.append({
                "level": max_level,
                "continuation_action": len(actions),
                "reported_total_action": (
                    len(compiled_actions) + len(actions) + 1
                ),
            })

        frames.append(latest)

    return {
        "generation": generation,
        "strategy": strategy,
        "compiled_level": int(latest_obs.levels_completed),
        "compiled_route_actions": len(compiled_actions),
        "reported_compiled_milestone_action": len(compiled_actions) + 1,
        "continuation_actions": len(actions),
        "reported_total_actions": len(compiled_actions) + len(actions) + 1,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "unique_continuation_states": len(states),
        "zero_change_actions": zero_change,
        "planner": dict(counters),
        "new_nodes": new_nodes,
        "new_edges": new_edges,
        "new_ambiguous_edges": new_ambiguous,
        "ledger_nodes_before": start_nodes,
        "ledger_nodes_after": len(ledger.nodes),
        "ledger_edges_before": start_edges,
        "ledger_edges_after": len(ledger.edge_records),
    }


def main():
    payload, ledger = load_ledger()

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"] == EXPECTED_GAME
    )

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    initial_max_level = highest_ledger_level(ledger)
    if initial_max_level != 1:
        raise AssertionError("expected augmented ledger to begin at Level 1")

    initial_route = shortest_route_to_level(ledger, initial_max_level)
    if len(initial_route["actions"]) != 56:
        raise AssertionError("known compiled L1 route length changed")

    generations = []
    route_history = []

    for generation in range(1, GENERATIONS + 1):
        target_level_before = highest_ledger_level(ledger)
        route = shortest_route_to_level(
            ledger,
            target_level_before,
        )
        route_history.append({
            "generation": generation,
            "target_level": target_level_before,
            "route_actions": len(route["actions"]),
            "reported_milestone_action": len(route["actions"]) + 1,
            "target": route["target"],
        })

        arc, env, latest = replay_route(
            module,
            game["game_id"],
            manifest["environments_dir"],
            ledger,
            route,
        )
        row = continue_generation(
            module,
            env,
            latest,
            ledger,
            compiled_actions=route["actions"],
            strategy=STRATEGIES[generation - 1],
            generation=generation,
        )
        arc.close_scorecard()

        row["ledger_max_level_after"] = highest_ledger_level(ledger)
        new_route = shortest_route_to_level(
            ledger,
            row["ledger_max_level_after"],
        )
        row["next_compiled_route_actions"] = len(new_route["actions"])
        row["next_reported_milestone_action"] = len(new_route["actions"]) + 1
        generations.append(row)

        print(
            "LS20_LEVEL_COMPOUNDING_GENERATION="
            + json.dumps(row, sort_keys=True),
            flush=True,
        )

    final_max_level = highest_ledger_level(ledger)
    final_route = shortest_route_to_level(ledger, final_max_level)

    augmented = ledger.export(generation_rows=generations)
    audit.write_json(
        OUT / "level-compounded-exact-replay-ledger.json",
        augmented,
    )

    report = {
        "interpretation": (
            "protected-level performance compounding: each generation enters "
            "at the highest already-discovered level via the shortest exact "
            "compiled RESET route, spends only the remaining action envelope "
            "beyond it, retains all new exact evidence, and recompiles"
        ),
        "claim_boundary": (
            "compiled routes contain deterministic exact public-state/action "
            "edges only and are live-replay-verified at every intermediate digest"
        ),
        "initial": {
            "ledger_nodes": len(payload["nodes"]),
            "ledger_edges": len(payload["edges"]),
            "max_level": initial_max_level,
            "compiled_route_actions": len(initial_route["actions"]),
            "reported_milestone_action": len(initial_route["actions"]) + 1,
        },
        "route_history": route_history,
        "generations": generations,
        "final": {
            "ledger_nodes": len(ledger.nodes),
            "ledger_edges": len(ledger.edge_records),
            "deterministic_edges": len(ledger.successor),
            "ambiguous_edges": len(ledger.ambiguous),
            "max_level": final_max_level,
            "compiled_route_actions": len(final_route["actions"]),
            "reported_milestone_action": len(final_route["actions"]) + 1,
            "target": final_route["target"],
        },
        "performance_compounding": {
            "level_gain": final_max_level - initial_max_level,
            "l1_actions_saved_vs_discovery": 67 - 57,
            "best_level_reached": max(
                [initial_max_level]
                + [row["max_levels"] for row in generations]
            ),
            "total_new_nodes": sum(row["new_nodes"] for row in generations),
            "total_new_edges": sum(row["new_edges"] for row in generations),
        },
    }

    audit.write_json(
        OUT / "ls20-level1-performance-compounding.json",
        report,
    )
    print(
        "LS20_LEVEL1_PERFORMANCE_COMPOUNDING_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_LS20_LEVEL1_PERFORMANCE_COMPOUNDING=PASS", flush=True)


if __name__ == "__main__":
    main()
