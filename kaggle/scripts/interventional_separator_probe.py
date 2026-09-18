"""Active separator probes for the partial interventional quotient on ls20.

Start from the exact frozen MG-ARC5 trajectory. Find the raw-observation pairs
that remain merged after finite observed-continuation refinement. Because ls20
has a small primitive action alphabet, replay each candidate source exactly and
try every legal primitive action. The added counterfactual evidence must either
split the candidate pair or upgrade it from UNKNOWN/partial to fully observed.

No candidate quotient affects the policy in this experiment.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "interventional-separator-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.interventional_quotient import PartialInterventionalQuotient
from interventional_quotient_diagnostic import legal_ids, protected, raw_digest


def make_action(action_id: int, x: int | None, y: int | None):
    from arcengine import GameAction

    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        if x is None or y is None:
            raise ValueError("complex replay action requires coordinates")
        action.set_data({"x": int(x), "y": int(y)})
    return action, action.action_data.model_dump()


def build_frozen_trace(game_id: str, envdir: str, max_actions: int):
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
        raise RuntimeError("offline ls20 unavailable")

    policy = module.MyAgent(
        card_id="separator-source",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    q = PartialInterventionalQuotient()
    latest = policy._convert_raw_frame_data(env.observation_space)
    digest = raw_digest(module, latest)
    q.observe_node(
        digest,
        protected=protected(latest),
        legal_actions=legal_ids(latest),
    )

    prefix: tuple[tuple[int, int | None, int | None], ...] = ()
    prefix_by_digest = {digest: prefix}
    frames = [latest]
    actions = []
    source_counts = Counter()

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break
        before = latest
        source = digest
        before_level = int(before.levels_completed)

        action = policy.choose_action(frames, before)
        data = audit.validate_action(action, before)
        key = (int(action.value), data.get("x"), data.get("y"))
        reasoning = getattr(action, "reasoning", {})
        action_source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(action, data=data, reasoning={"source": action_source})
        latest = policy._convert_raw_frame_data(raw)
        digest = raw_digest(module, latest)
        q.observe_node(
            digest,
            protected=protected(latest),
            legal_actions=legal_ids(latest),
        )
        delta = int(latest.levels_completed) - before_level
        outcome = (
            "LEVEL_INCREMENT" if delta > 0 else audit.state_name(latest),
            int(delta),
        )
        q.observe_transition(source, int(action.value), digest, outcome=outcome)

        actions.append(key)
        source_counts[action_source] += 1
        prefix = prefix + (key,)
        prefix_by_digest.setdefault(digest, prefix)
        frames.append(latest)

    arc.close_scorecard()
    return module, q, prefix_by_digest, {
        "actions": len(actions) + 1,
        "source_counts": dict(source_counts),
        "raw_states": len(q.nodes),
    }


def merged_pairs(classes: dict, nodes: set[str]) -> list[tuple[str, str]]:
    groups: dict[int, list[str]] = defaultdict(list)
    for node, class_id in classes.items():
        if node in nodes:
            groups[int(class_id)].append(node)
    return sorted(
        tuple(sorted((left, right)))
        for group in groups.values()
        for left, right in combinations(sorted(group), 2)
    )


def replay_and_probe(
    module,
    game_id: str,
    envdir: str,
    prefix: tuple[tuple[int, int | None, int | None], ...],
    expected_source: str,
    probe_action: int,
):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable during replay")
    adapter = module.MyAgent(
        card_id="separator-replay",
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

    source_digest = raw_digest(module, latest)
    if source_digest != expected_source:
        arc.close_scorecard()
        raise AssertionError(
            "exact replay failed to recover candidate state: "
            f"{expected_source[:12]} != {source_digest[:12]}"
        )

    before_level = int(latest.levels_completed)
    action, data = make_action(probe_action, None, None)
    raw = env.step(action, data=data, reasoning={"source": "separator_probe"})
    after = adapter._convert_raw_frame_data(raw)
    target = raw_digest(module, after)
    delta = int(after.levels_completed) - before_level
    outcome = (
        "LEVEL_INCREMENT" if delta > 0 else audit.state_name(after),
        int(delta),
    )
    result = {
        "source": source_digest,
        "action": int(probe_action),
        "target": target,
        "outcome": outcome,
        "target_protected": protected(after),
        "target_legal_actions": legal_ids(after),
    }
    arc.close_scorecard()
    return result


def main() -> None:
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(row for row in manifest["games"] if row["game_id"].startswith("ls20-"))
    game_id = game["game_id"]

    module, q, prefix_by_digest, source_meta = build_frozen_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    original_nodes = set(q.nodes)
    before_parts = q.partitions(max_depth=max(8, len(q.nodes)))
    before_classes = before_parts[-1]
    candidates = merged_pairs(before_classes, original_nodes)

    # This pins the exact residual discovered by the observer-only qualification.
    assert len(original_nodes) == 355
    assert len(candidates) == 15

    candidate_nodes = sorted({node for pair in candidates for node in pair})
    probes = []
    for node in candidate_nodes:
        prefix = prefix_by_digest[node]
        legal = q.nodes[node].legal_actions
        if not legal or any(action in (0, 6) for action in legal):
            raise AssertionError("ls20 separator probe expected enumerable primitive actions")
        for action in legal:
            row = replay_and_probe(
                module,
                game_id,
                manifest["environments_dir"],
                prefix,
                node,
                action,
            )
            probes.append(row)
            q.observe_node(
                row["target"],
                protected=tuple(row["target_protected"]),
                legal_actions=tuple(row["target_legal_actions"]),
            )
            q.observe_transition(
                row["source"],
                row["action"],
                row["target"],
                outcome=tuple(row["outcome"]),
            )
            print(
                "SEPARATOR_PROBE="
                + json.dumps(
                    {
                        "source": row["source"][:16],
                        "action": row["action"],
                        "target": row["target"][:16],
                        "outcome": row["outcome"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    after_parts = q.partitions(max_depth=max(8, len(q.nodes)))
    after_classes = after_parts[-1]
    after_summary = q.summary(max_depth=max(8, len(q.nodes)))
    final = after_summary["depths"][-1]
    assert after_summary["stabilized"]
    assert final["contradictory_merged_pairs"] == 0

    surviving = [
        pair
        for pair in candidates
        if after_classes[pair[0]] == after_classes[pair[1]]
    ]
    split = [pair for pair in candidates if pair not in surviving]

    separators = []
    for left, right in split:
        left_actions = q._observed_actions(left)
        right_actions = q._observed_actions(right)
        differing = []
        for action in sorted(left_actions & right_actions):
            if (
                q._action_relation(left, action, after_classes)
                != q._action_relation(right, action, after_classes)
            ):
                differing.append(action)
        separators.append({
            "left": left,
            "right": right,
            "actions": differing,
        })

    report = {
        "interpretation": (
            "active source-blind separator probing of the 15 partial ls20 "
            "state-pair merges produced by frozen MG-ARC5"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "source_trace": source_meta,
        "candidate_pairs": len(candidates),
        "candidate_nodes": len(candidate_nodes),
        "probe_count": len(probes),
        "pairs_split": len(split),
        "pairs_surviving": len(surviving),
        "surviving_pairs": surviving,
        "separators": separators,
        "after_quotient": after_summary,
        "final_quotient": final,
    }
    audit.write_json(OUT / "separator-probe.json", report)
    print("INTERVENTIONAL_SEPARATOR_RESULT=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_INTERVENTIONAL_SEPARATOR_PROBE=PASS", flush=True)


if __name__ == "__main__":
    main()
