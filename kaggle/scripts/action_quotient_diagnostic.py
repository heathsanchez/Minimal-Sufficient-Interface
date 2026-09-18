"""Source-blind action-quotient diagnostic for ft09 on frozen MG-ARC5.

The state quotient showed ft09 raw observations are not safely compressible under
the observed exact coordinate interventions. This diagnostic turns the question
around: from frequently revisited exact states, enumerate the controller's
grounded Action6 candidates and group them by their exact protected successor
consequence.

This measures causal redundancy in the intervention space. It does not change
the policy, use game source, or claim unobserved-coordinate equivalence.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "action-quotient-results"
AGENT = OUT / "agent.py"
TOP_STATES = 3


def make_action(action_id: int, x: int | None, y: int | None):
    from arcengine import GameAction

    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        if x is None or y is None:
            raise ValueError("complex action requires coordinates")
        action.set_data({"x": int(x), "y": int(y)})
    return action, action.action_data.model_dump()


def collect_trace(game_id: str, envdir: str, max_actions: int):
    from arc_agi import Arcade, OperationMode

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()
    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ft09 unavailable")

    policy = module.MyAgent(
        card_id="action-quotient-source",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    latest = policy._convert_raw_frame_data(env.observation_space)
    digest = module.normalize_frame(latest).evidence_sha256
    prefix: tuple[tuple[int, int | None, int | None], ...] = ()
    prefix_by_digest = {digest: prefix}
    visits = Counter([digest])
    protected_by_digest = {
        digest: (audit.state_name(latest), int(latest.levels_completed))
    }
    frames = [latest]
    actions = []

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break
        before = latest
        action = policy.choose_action(frames, before)
        data = audit.validate_action(action, before)
        key = (int(action.value), data.get("x"), data.get("y"))
        raw = env.step(action, data=data, reasoning={"source": "frozen_trace"})
        latest = policy._convert_raw_frame_data(raw)
        digest = module.normalize_frame(latest).evidence_sha256
        actions.append(key)
        prefix = prefix + (key,)
        old = prefix_by_digest.get(digest)
        if old is None or len(prefix) < len(old):
            prefix_by_digest[digest] = prefix
        visits[digest] += 1
        protected_by_digest[digest] = (
            audit.state_name(latest),
            int(latest.levels_completed),
        )
        frames.append(latest)

    arc.close_scorecard()
    return module, prefix_by_digest, visits, protected_by_digest, {
        "actions": len(actions) + 1,
        "unique_states": len(visits),
        "top_visits": visits.most_common(12),
    }


def replay_state(module, game_id: str, envdir: str, prefix, expected_digest: str):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ft09 unavailable during replay")
    adapter = module.MyAgent(
        card_id="action-quotient-replay",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    latest = adapter._convert_raw_frame_data(env.observation_space)
    for action_id, x, y in prefix:
        action, data = make_action(action_id, x, y)
        raw = env.step(action, data=data, reasoning={"source": "exact_replay"})
        latest = adapter._convert_raw_frame_data(raw)
    digest = module.normalize_frame(latest).evidence_sha256
    if digest != expected_digest:
        arc.close_scorecard()
        raise AssertionError("exact replay did not recover selected state")
    return arc, env, adapter, latest


def candidate_catalog(module, adapter, latest):
    obs = module.normalize_frame(latest)
    controller = adapter.controller
    controller._grid = module.settled_grid(latest)
    catalog = controller._catalog(obs)
    primary = tuple(controller._primary) or catalog
    rows = []
    for token in primary:
        if int(token.action_id) != 6:
            continue
        rows.append({
            "action": (int(token.action_id), int(token.x), int(token.y)),
            "descriptor": controller._descriptor(token),
        })
    # Deterministic de-duplication while preserving controller order.
    seen = set()
    out = []
    for row in rows:
        if row["action"] in seen:
            continue
        seen.add(row["action"])
        out.append(row)
    return out


def probe_action(module, game_id, envdir, prefix, source_digest, action_key):
    arc, env, adapter, latest = replay_state(
        module, game_id, envdir, prefix, source_digest
    )
    before_level = int(latest.levels_completed)
    action, data = make_action(*action_key)
    raw = env.step(action, data=data, reasoning={"source": "action_quotient_probe"})
    after = adapter._convert_raw_frame_data(raw)
    target = module.normalize_frame(after).evidence_sha256
    delta = int(after.levels_completed) - before_level
    outcome = (
        "LEVEL_INCREMENT" if delta > 0 else audit.state_name(after),
        int(delta),
    )
    arc.close_scorecard()
    return {
        "target": target,
        "outcome": outcome,
        "changed": target != source_digest,
    }


def audit_state(module, game_id, envdir, digest, prefix, visits):
    arc, _env, adapter, latest = replay_state(
        module, game_id, envdir, prefix, digest
    )
    candidates = candidate_catalog(module, adapter, latest)
    arc.close_scorecard()

    results = []
    for row in candidates:
        consequence = probe_action(
            module,
            game_id,
            envdir,
            prefix,
            digest,
            row["action"],
        )
        results.append({**row, **consequence})
        print(
            "ACTION_QUOTIENT_PROBE="
            + json.dumps(
                {
                    "source": digest[:16],
                    "action": list(row["action"]),
                    "target": consequence["target"][:16],
                    "outcome": consequence["outcome"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    consequence_groups = defaultdict(list)
    descriptor_groups = defaultdict(set)
    for row in results:
        key = (tuple(row["outcome"]), row["target"])
        consequence_groups[key].append(row["action"])
        descriptor_groups[row["descriptor"]].add(key)

    changed = [row for row in results if row["changed"]]
    progress = [
        row for row in results
        if row["outcome"][0] == "LEVEL_INCREMENT"
    ]
    conflicts = {
        descriptor: len(values)
        for descriptor, values in descriptor_groups.items()
        if len(values) > 1
    }
    classes = sorted(
        (
            {
                "outcome": list(key[0]),
                "target": key[1],
                "size": len(actions),
                "representative": list(min(actions)),
            }
            for key, actions in consequence_groups.items()
        ),
        key=lambda row: (-row["size"], row["representative"]),
    )
    return {
        "source": digest,
        "baseline_visits": int(visits),
        "prefix_length": len(prefix),
        "candidate_actions": len(results),
        "consequence_classes": len(consequence_groups),
        "action_compression": (
            len(results) / max(1, len(consequence_groups))
        ),
        "largest_class": max(
            (len(actions) for actions in consequence_groups.values()),
            default=0,
        ),
        "changed_actions": len(changed),
        "no_change_actions": len(results) - len(changed),
        "progress_actions": [
            {"action": list(row["action"]), "target": row["target"]}
            for row in progress
        ],
        "descriptor_count": len(descriptor_groups),
        "descriptor_conflicts": conflicts,
        "descriptor_conflict_count": len(conflicts),
        "classes": classes,
    }


def main() -> None:
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]
    module, prefixes, visits, protected, trace = collect_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )

    eligible = [
        (count, digest)
        for digest, count in visits.items()
        if protected[digest][0] == "NOT_FINISHED"
    ]
    eligible.sort(key=lambda row: (-row[0], len(prefixes[row[1]]), row[1]))
    selected = eligible[:TOP_STATES]
    states = [
        audit_state(
            module,
            game_id,
            manifest["environments_dir"],
            digest,
            prefixes[digest],
            count,
        )
        for count, digest in selected
    ]

    report = {
        "interpretation": (
            "source-blind exact consequence quotient over grounded Action6 "
            "coordinates at the three most revisited frozen-MG-ARC5 ft09 states"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "trace": trace,
        "selected_states": states,
        "total_probe_actions": sum(row["candidate_actions"] for row in states),
        "any_progress_action": any(row["progress_actions"] for row in states),
    }
    audit.write_json(OUT / "action-quotient.json", report)
    print("ACTION_QUOTIENT_RESULT=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_ACTION_QUOTIENT_DIAGNOSTIC=PASS", flush=True)


if __name__ == "__main__":
    main()
