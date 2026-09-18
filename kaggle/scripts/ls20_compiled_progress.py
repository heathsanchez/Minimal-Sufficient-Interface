"""Compile the discovered ls20 progress route and spend the saved actions at Level 1.

The dynamic exact-ledger run discovered L1@67. Its final 2,921-state / 7,018-edge
ledger contains deterministic edges acquired across multiple episodes. Composing
those verified edges yields a shorter exact route from RESET to a Level-1 state.

This experiment:
1. loads the pinned augmented ledger artifact;
2. computes the shortest deterministic path from RESET to any protected state
   with levels_completed > 0;
3. replays that path exactly and checks every observed digest against the ledger;
4. once Level 1 is reached, starts a fresh frozen controller at that exact public
   state with the dynamic exact-ledger frontier planner installed;
5. spends the remaining action budget extending the Level-1 ledger.

No discovered path step is trusted without exact replay equality.
"""
from __future__ import annotations

from collections import deque, Counter
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ls20-compiled-progress-results"
AGENT = OUT / "agent.py"
LEDGER = OUT / "augmented-exact-replay-ledger.json"

sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))
import ls20_dynamic_ledger_performance as dyn

EXPECTED_AGENT_SHA = dyn.EXPECTED_AGENT_SHA
EXPECTED_GAME = dyn.EXPECTED_GAME
EXPECTED_NODES = 2921
EXPECTED_EDGES = 7018


def load_augmented():
    payload = json.loads(LEDGER.read_text())
    meta = payload.get("metadata", {})
    if payload.get("schema") != "arc3-exact-replay-ledger-v1":
        raise AssertionError("unexpected augmented ledger schema")
    if meta.get("agent_sha256") != EXPECTED_AGENT_SHA:
        raise AssertionError("augmented ledger agent mismatch")
    if meta.get("game_id") != EXPECTED_GAME:
        raise AssertionError("augmented ledger game mismatch")
    if len(payload.get("nodes", {})) != EXPECTED_NODES:
        raise AssertionError("augmented ledger node count changed")
    if len(payload.get("edges", [])) != EXPECTED_EDGES:
        raise AssertionError("augmented ledger edge count changed")

    dyn.EXPECTED_NODES = EXPECTED_NODES
    dyn.EXPECTED_EDGES = EXPECTED_EDGES
    return payload, dyn.DynamicExactLedger(payload)


def root_node(ledger):
    roots = [
        node for node, prefix in ledger.prefixes.items()
        if len(prefix) == 0
    ]
    if len(roots) != 1:
        raise AssertionError("expected one exact RESET node")
    return roots[0]


def shortest_progress_path(ledger):
    root = root_node(ledger)
    queue = deque([(root, ())])
    seen = {root}

    while queue:
        node, path = queue.popleft()
        row = ledger.nodes[node]
        if int(row["protected"][1]) > 0:
            return {
                "root": root,
                "target": node,
                "target_protected": list(row["protected"]),
                "actions": list(path),
            }

        for action in ledger.legal(node):
            target = ledger.successor.get((node, int(action)))
            if target is None or target in seen:
                continue
            seen.add(target)
            queue.append((target, path + (int(action),)))

    raise AssertionError("augmented ledger contains no deterministic progress route")


def make_action(action_id: int):
    from arcengine import GameAction
    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        raise AssertionError("compiled ls20 route expected primitive actions")
    return action, action.action_data.model_dump()


def replay_compiled(module, game_id, envdir, route):
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
        card_id="compiled-progress-replay",
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
        raise AssertionError("RESET digest does not match compiled ledger root")

    digests = [digest]
    for index, action_id in enumerate(route["actions"], start=1):
        expected = route["target"] if index == len(route["actions"]) else None
        source = digest
        target = None

        action, data = make_action(action_id)
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "compiled_progress"},
        )
        latest = adapter._convert_raw_frame_data(raw)
        target = str(module.normalize_frame(latest).evidence_sha256)

        # Exact edge authority comes from the ledger, not merely the final target.
        # The caller verifies each source/action edge before replay starts.
        digest = target
        digests.append(digest)

    if digest != route["target"]:
        arc.close_scorecard()
        raise AssertionError("compiled progress route final digest mismatch")

    level = int(latest.levels_completed)
    if level < 1:
        arc.close_scorecard()
        raise AssertionError("compiled route failed to reproduce protected progress")

    return arc, env, latest, digests


def verify_route_edges(ledger, route):
    node = route["root"]
    expected_nodes = [node]
    for action in route["actions"]:
        target = ledger.successor.get((node, int(action)))
        if target is None:
            raise AssertionError("compiled route contains non-deterministic/missing edge")
        expected_nodes.append(target)
        node = target
    if node != route["target"]:
        raise AssertionError("compiled route graph target mismatch")
    return expected_nodes


def continue_from_level1(
    module,
    env,
    latest,
    ledger,
    *,
    remaining_actions: int,
    compiled_prefix: tuple[tuple[int, int | None, int | None], ...],
):
    policy = module.MyAgent(
        card_id="compiled-progress-continuation",
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
        "maxmissing_min",
    )

    frames = [latest]
    actions = []
    states = {str(module.normalize_frame(latest).evidence_sha256)}
    milestones = []
    max_level = int(latest.levels_completed)
    zero_change = 0
    # Use the newly compiled RESET route as replay authority for descendants,
    # not the longer historical prefix under which this target was first found.
    prefix = tuple(compiled_prefix)

    while len(actions) < remaining_actions and audit.state_name(latest) != "WIN":
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
            raise AssertionError("ls20 continuation expected primitive actions")

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
        ledger.add_node(
            after_digest,
            protected_value=dyn.protected(after_obs),
            legal=dyn.legal_actions(after_obs),
            prefix=prefix,
        )
        ledger.add_edge(
            before_digest,
            int(key[0]),
            after_digest,
            outcome,
        )

        zero_change += int(before_digest == after_digest)
        actions.append(key)

        if int(after_obs.levels_completed) > max_level:
            max_level = int(after_obs.levels_completed)
            milestones.append({
                "level": max_level,
                "continuation_actions": len(actions),
            })

        frames.append(latest)

    return {
        "continuation_actions": len(actions),
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "unique_states": len(states),
        "zero_change_actions": zero_change,
        "planner": dict(counters),
    }


def main():
    payload, ledger = load_augmented()
    route = shortest_progress_path(ledger)
    expected_nodes = verify_route_edges(ledger, route)

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"] == EXPECTED_GAME
    )

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    arc, env, latest, replay_nodes = replay_compiled(
        module,
        game["game_id"],
        manifest["environments_dir"],
        route,
    )
    if replay_nodes != expected_nodes:
        arc.close_scorecard()
        raise AssertionError("compiled route diverged from exact ledger at an intermediate step")

    compiled_actions = len(route["actions"])
    # Benchmark convention reports actions as executed_steps + 1, so preserve
    # the same 399 executed-step envelope used by the frozen 400-action arms.
    remaining = max(0, manifest["max_actions"] - 1 - compiled_actions)
    compiled_prefix = tuple(
        (int(action_id), None, None)
        for action_id in route["actions"]
    )
    continuation = continue_from_level1(
        module,
        env,
        latest,
        ledger,
        remaining_actions=remaining,
        compiled_prefix=compiled_prefix,
    )
    arc.close_scorecard()

    if int(route["target_protected"][1]) < 1:
        raise AssertionError("compiled target is not protected progress")

    report = {
        "interpretation": (
            "verified discovery compilation: deterministic edges learned across "
            "developmental generations are composed into the shortest exact RESET→L1 "
            "route, replay-checked, then the saved action budget is reinvested at L1"
        ),
        "claim_boundary": (
            "every compiled action is an exact deterministic ledger edge and the live "
            "replay must match every intermediate digest before the route is accepted"
        ),
        "ledger": {
            "nodes": len(payload["nodes"]),
            "edges": len(payload["edges"]),
            "source_branch": payload["metadata"].get("source_branch"),
            "dynamic_generation_count": payload["metadata"].get("dynamic_generation_count"),
        },
        "discovery_milestone_actions": 67,
        "compiled_route": {
            "primitive_actions": compiled_actions,
            "reported_milestone_action": compiled_actions + 1,
            "target": route["target"],
            "target_protected": route["target_protected"],
            "action_word": route["actions"],
        },
        "compilation_gain": {
            "actions_saved_vs_discovery": 67 - (compiled_actions + 1),
            "relative_reduction": (
                (67 - (compiled_actions + 1)) / 67
            ),
        },
        "continuation": continuation,
        "overall_max_level": continuation["max_levels"],
    }

    audit.write_json(
        OUT / "ls20-compiled-progress.json",
        report,
    )
    print(
        "LS20_COMPILED_PROGRESS_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_LS20_COMPILED_PROGRESS=PASS", flush=True)


if __name__ == "__main__":
    main()
