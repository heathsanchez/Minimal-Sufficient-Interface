"""Observer-only QCKN diagnostic: derive state classes from consequences, not pixels.

The frozen MG-ARC5 policy is run unchanged. Raw public observations are treated
as opaque hashes. A partial action-labelled transition system is then refined
by protected outcomes and observed continuations. Untried interventions remain
UNKNOWN and therefore cannot manufacture a certified equivalence.

This is bounded development evidence, not hidden generalization and not a
claim of equivalence under unobserved continuations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "interventional-quotient-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.interventional_quotient import PartialInterventionalQuotient


def legal_ids(frame) -> tuple[int, ...]:
    return tuple(sorted({
        int(getattr(action, "value", action))
        for action in getattr(frame, "available_actions", ())
    }))


def raw_digest(module, frame) -> str:
    return module.normalize_frame(frame).evidence_sha256


def protected(frame) -> tuple:
    return (
        audit.state_name(frame),
        int(frame.levels_completed),
    )


def run_world(game_id: str, envdir: str, max_actions: int) -> dict:
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
        raise RuntimeError("offline world unavailable")

    policy = module.MyAgent(
        card_id="interventional-quotient-diagnostic",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    q = PartialInterventionalQuotient()
    latest = policy._convert_raw_frame_data(env.observation_space)
    current = raw_digest(module, latest)
    q.observe_node(
        current,
        protected=protected(latest),
        legal_actions=legal_ids(latest),
    )

    frames = [latest]
    actions: list[tuple[int, int | None, int | None]] = []
    sources: list[str] = []
    milestones: list[dict] = []
    exact_actions_by_family: dict[int, set[tuple[int, int | None, int | None]]] = defaultdict(set)
    source_counts: Counter[str] = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break
        before = latest
        before_digest = current
        before_level = int(before.levels_completed)

        action = policy.choose_action(frames, before)
        data = audit.validate_action(action, before)
        aid = int(action.value)
        key = (aid, data.get("x"), data.get("y"))
        reasoning = getattr(action, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(action, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        current = raw_digest(module, latest)
        q.observe_node(
            current,
            protected=protected(latest),
            legal_actions=legal_ids(latest),
        )

        delta_level = int(latest.levels_completed) - before_level
        outcome = (
            "LEVEL_INCREMENT" if delta_level > 0 else audit.state_name(latest),
            int(delta_level),
        )
        q.observe_transition(
            before_digest,
            aid,
            current,
            outcome=outcome,
        )

        actions.append(key)
        sources.append(source)
        source_counts[source] += 1
        exact_actions_by_family[aid].add(key)
        zero_change += int(before_digest == current)

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": len(actions) + 1})
        frames.append(latest)

    arc.close_scorecard()
    summary = q.summary(max_depth=8)
    final = summary["depths"][-1] if summary["depths"] else {}
    assert int(final.get("contradictory_merged_pairs", 0)) == 0

    return {
        "game_id": game_id,
        "actions": len(actions) + 1,
        "final_state": audit.state_name(latest),
        "max_levels": max_level,
        "milestones": milestones,
        "raw_unique_observations": len(q.nodes),
        "zero_observation_change": zero_change,
        "source_counts": dict(source_counts),
        "action_family_parameter_variants": {
            str(action): len(values)
            for action, values in sorted(exact_actions_by_family.items())
        },
        "quotient": summary,
        "final_quotient": final,
    }


def main() -> None:
    fixture = json.loads((OUT / "fixture.json").read_text())
    public = json.loads((OUT / "public.json").read_text())
    worlds = []

    for manifest in (fixture, public):
        for row in manifest["games"]:
            result = run_world(
                row["game_id"],
                manifest["environments_dir"],
                manifest["max_actions"],
            )
            worlds.append(result)
            print(
                "INTERVENTIONAL_QUOTIENT_WORLD="
                + json.dumps(result, sort_keys=True),
                flush=True,
            )

    bt11 = next(row for row in worlds if row["game_id"].startswith("bt11-"))
    assert bt11["final_state"] == "WIN"
    assert bt11["max_levels"] == 5
    assert bt11["actions"] <= 73

    vc33 = next(row for row in worlds if row["game_id"].startswith("vc33-"))
    assert vc33["milestones"][:2] == [
        {"level": 1, "actions": 64},
        {"level": 2, "actions": 93},
    ]

    report = {
        "interpretation": (
            "observer-only partial interventional quotient on exact frozen MG-ARC5; "
            "public development diagnostic, not sealed holdout"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "worlds": worlds,
    }
    audit.write_json(OUT / "interventional-quotient.json", report)
    print(
        "INTERVENTIONAL_QUOTIENT_DIAGNOSTIC="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_INTERVENTIONAL_QUOTIENT_DIAGNOSTIC=PASS", flush=True)


if __name__ == "__main__":
    main()
