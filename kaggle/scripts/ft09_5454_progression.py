"""Target the ft09 (54,54) exact progression variable.

The retained exact bank shows Action 6 at coordinate (54,54):
- changed the public state on 687/687 observations;
- was observed across 422 exact contexts;
- appears in the primary catalog of 425 contexts;
- has only three primary contexts where its exact consequence is still unknown.

Its known transition graph is acyclic, with chains up to 31 steps.

This experiment:
1. loads the pinned final exact bank;
2. reconstructs the RESET digest from the frozen baseline trace;
3. finds shortest deterministic exact-bank routes to the three unresolved
   (54,54) contexts;
4. live-replays every route and checks every intermediate digest;
5. applies (54,54) at the unresolved endpoint;
6. if the world keeps changing, repeatedly applies the same exact intervention
   up to a bounded extension, stopping on protected progress, terminal state,
   exact no-change, repeated digest, or loss of Action 6 legality.

The 100% historical change rate is proposal evidence only. Every extension step
is observed exactly and no universal law is assumed.
"""
from __future__ import annotations

from collections import defaultdict, deque
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ft09-5454-progression-results"
AGENT = OUT / "agent.py"
BANK = OUT / "dynamic-exact-effect-bank.json"

sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import action_quotient_diagnostic as aq

aq.OUT = OUT
aq.AGENT = AGENT

TARGET_ACTION = (6, 54, 54)
EXPECTED_EDGE_KEYS = 945
EXPECTED_CATALOG_CONTEXTS = 425
MAX_EXTENSION = 96


def load_bank():
    payload = json.loads(BANK.read_text())
    if payload.get("schema") != "arc3-exact-effect-bank-v1":
        raise AssertionError("unexpected exact effect bank schema")
    if payload.get("game_id") != "ft09-0d8bbf25":
        raise AssertionError("exact effect bank game mismatch")
    if payload.get("agent_sha256") != (
        "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead"
    ):
        raise AssertionError("exact effect bank agent mismatch")
    if len(payload.get("edges", ())) != EXPECTED_EDGE_KEYS:
        raise AssertionError("exact effect bank edge count changed")
    if len(payload.get("catalogs", {})) != EXPECTED_CATALOG_CONTEXTS:
        raise AssertionError("exact effect bank catalog count changed")
    return payload


def exact_graph(payload):
    successor = {}
    ambiguous = set()
    for item in payload["edges"]:
        context = str(item["context"])
        action = tuple(item["action"])
        row = item["row"]
        outcomes = row.get("outcomes", {})
        key = (context, action)
        if row.get("ambiguous") or len(outcomes) != 1:
            ambiguous.add(key)
            continue
        successor[key] = str(next(iter(outcomes)))
    return successor, ambiguous


def target_endpoints(payload, successor):
    catalogs = {
        str(context): {tuple(action) for action in actions}
        for context, actions in payload["catalogs"].items()
    }
    return sorted(
        context
        for context, actions in catalogs.items()
        if TARGET_ACTION in actions
        and (context, TARGET_ACTION) not in successor
    )


def shortest_route(root, target, successor):
    adjacency = defaultdict(list)
    for (source, action), dest in successor.items():
        adjacency[source].append((tuple(action), str(dest)))
    for source in adjacency:
        adjacency[source].sort(key=lambda row: repr(row[0]))

    queue = deque([(root, ())])
    seen = {root}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for action, dest in adjacency.get(node, ()):
            if dest in seen:
                continue
            seen.add(dest)
            queue.append((dest, path + (action,)))
    return None


def make_action(action_key):
    from arcengine import GameAction

    action_id, x, y = action_key
    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        if x is None or y is None:
            raise AssertionError("complex retained action missing coordinates")
        action.set_data({"x": int(x), "y": int(y)})
    return action, action.action_data.model_dump()


def replay_and_extend(
    module,
    game_id,
    envdir,
    successor,
    root,
    endpoint,
    route,
):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ft09 unavailable")

    adapter = module.MyAgent(
        card_id="ft09-5454-progression",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )

    latest = adapter._convert_raw_frame_data(env.observation_space)
    digest = str(module.normalize_frame(latest).evidence_sha256)
    if digest != root:
        arc.close_scorecard()
        raise AssertionError("RESET digest mismatch")

    replay_rows = []
    for index, action_key in enumerate(route, start=1):
        expected = successor.get((digest, tuple(action_key)))
        if expected is None:
            arc.close_scorecard()
            raise AssertionError("retained route contains missing/ambiguous edge")

        action, data = make_action(action_key)
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "retained_exact_route"},
        )
        latest = adapter._convert_raw_frame_data(raw)
        actual = str(module.normalize_frame(latest).evidence_sha256)
        if actual != expected:
            arc.close_scorecard()
            raise AssertionError("retained exact route diverged")
        replay_rows.append({
            "index": index,
            "action": list(action_key),
            "target": actual,
        })
        digest = actual

    if digest != endpoint:
        arc.close_scorecard()
        raise AssertionError("retained route failed to reach unresolved endpoint")

    endpoint_frame = module.normalize_frame(latest)
    start_level = int(endpoint_frame.levels_completed)
    seen = {digest}
    extension = []
    stop_reason = None
    progress = None

    for step in range(1, MAX_EXTENSION + 1):
        current = module.normalize_frame(latest)
        if 6 not in {int(value) for value in current.available_actions}:
            stop_reason = "ACTION6_NOT_LEGAL"
            break

        before_digest = str(current.evidence_sha256)
        before_level = int(current.levels_completed)

        action, data = make_action(TARGET_ACTION)
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "targeted_5454_progression"},
        )
        latest = adapter._convert_raw_frame_data(raw)
        after = module.normalize_frame(latest)
        after_digest = str(after.evidence_sha256)
        delta = int(after.levels_completed) - before_level

        row = {
            "step": step,
            "source": before_digest,
            "target": after_digest,
            "changed": before_digest != after_digest,
            "state": str(after.state),
            "level": int(after.levels_completed),
            "level_delta": delta,
        }
        extension.append(row)

        if int(after.levels_completed) > start_level:
            progress = {
                "level": int(after.levels_completed),
                "extension_step": step,
                "executed_actions": len(route) + step,
                "reported_milestone_action": len(route) + step + 1,
                "action_word": [
                    list(action) for action in route
                ] + [list(TARGET_ACTION)] * step,
                "target": after_digest,
            }
            stop_reason = "PROTECTED_PROGRESS"
            break

        if str(after.state) in ("GAME_OVER", "WIN"):
            stop_reason = str(after.state)
            break

        if after_digest == before_digest:
            stop_reason = "NO_CHANGE"
            break

        if after_digest in seen:
            stop_reason = "REPEATED_DIGEST"
            break

        seen.add(after_digest)

    if stop_reason is None:
        stop_reason = "EXTENSION_BOUND"

    arc.close_scorecard()
    return {
        "endpoint": endpoint,
        "route_actions": len(route),
        "route": [list(action) for action in route],
        "replay_rows": replay_rows,
        "extension": extension,
        "stop_reason": stop_reason,
        "progress": progress,
        "unique_extension_states": len(seen),
    }


def main():
    payload = load_bank()
    successor, ambiguous = exact_graph(payload)
    endpoints = target_endpoints(payload, successor)

    if len(endpoints) != 3:
        raise AssertionError(
            f"expected exactly three unresolved (54,54) contexts, got {len(endpoints)}"
        )
    if any((endpoint, TARGET_ACTION) in ambiguous for endpoint in endpoints):
        raise AssertionError("unresolved target action is already ambiguous")

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]

    module, prefixes, _visits, _protected, trace = aq.collect_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    roots = [
        digest for digest, prefix in prefixes.items()
        if len(prefix) == 0
    ]
    if len(roots) != 1:
        raise AssertionError("expected one exact RESET digest")
    root = roots[0]

    rows = []
    progress = None
    unreachable = []

    for endpoint in endpoints:
        route = shortest_route(root, endpoint, successor)
        if route is None:
            unreachable.append(endpoint)
            continue

        row = replay_and_extend(
            module,
            game_id,
            manifest["environments_dir"],
            successor,
            root,
            endpoint,
            route,
        )
        rows.append(row)
        print(
            "FT09_5454_ENDPOINT="
            + json.dumps(
                {
                    "endpoint": endpoint,
                    "route_actions": row["route_actions"],
                    "stop_reason": row["stop_reason"],
                    "extension_steps": len(row["extension"]),
                    "progress": row["progress"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

        if row["progress"] is not None:
            progress = row["progress"]
            break

    report = {
        "interpretation": (
            "targeted extension of the exact ft09 (54,54) intervention, which "
            "changed state on all 687 retained observations and forms acyclic "
            "known chains up to length 31"
        ),
        "claim_boundary": (
            "historical 100% change rate is proposal-only; every retained route "
            "digest and every new extension consequence is checked exactly"
        ),
        "trace": trace,
        "bank": {
            "edge_keys": len(payload["edges"]),
            "catalog_contexts": len(payload["catalogs"]),
            "target_action": list(TARGET_ACTION),
            "historical_observations": 687,
            "historical_contexts": 422,
            "unresolved_primary_contexts": len(endpoints),
        },
        "root": root,
        "endpoints": endpoints,
        "unreachable_endpoints": unreachable,
        "endpoint_results": rows,
        "result": {
            "status": (
                "PROGRESS_FOUND"
                if progress is not None
                else "NO_PROTECTED_PROGRESS"
            ),
            "progress": progress,
        },
    }

    audit.write_json(
        OUT / "ft09-5454-progression.json",
        report,
    )
    print(
        "FT09_5454_PROGRESSION_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_FT09_5454_PROGRESSION=PASS", flush=True)


if __name__ == "__main__":
    main()
