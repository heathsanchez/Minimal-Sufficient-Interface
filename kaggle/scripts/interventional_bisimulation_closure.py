"""Recursive paired-intervention closure for the four surviving ls20 pairs.

This is the all-continuation follow-up to the one-step separator probe. For each
surviving pair, replay both raw observations exactly and recursively apply every
legal primitive action on both sides. A different protected outcome is a
separator word. Revisited state pairs close coinductively. Hitting the explicit
obligation/probe budget remains UNKNOWN, never a proof of equivalence.

No quotient affects the frozen MG-ARC5 policy.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "interventional-bisimulation-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from interventional_separator_probe import (
    build_frozen_trace,
    merged_pairs,
    replay_and_probe,
)


MAX_PAIR_OBLIGATIONS = 64
MAX_ACTIVE_PROBES = 768


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
    candidates = merged_pairs(before_parts[-1], original_nodes)
    assert len(candidates) == 15

    probe_cache: dict[tuple[str, int], dict] = {}
    active_probe_count = 0

    def probe(source: str, action: int) -> dict:
        nonlocal active_probe_count
        key = (source, int(action))
        if key in probe_cache:
            return probe_cache[key]
        if active_probe_count >= MAX_ACTIVE_PROBES:
            raise RuntimeError("ACTIVE_PROBE_BUDGET")
        legal = q.nodes[source].legal_actions
        if int(action) not in legal:
            raise AssertionError("probe action outside source legal contract")
        if int(action) in (0, 6):
            raise RuntimeError("UNSUPPORTED_NONPRIMITIVE_ACTION")

        row = replay_and_probe(
            module,
            game_id,
            manifest["environments_dir"],
            prefix_by_digest[source],
            source,
            int(action),
        )
        active_probe_count += 1
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
        new_prefix = prefix_by_digest[source] + ((int(action), None, None),)
        old = prefix_by_digest.get(row["target"])
        if old is None or len(new_prefix) < len(old):
            prefix_by_digest[row["target"]] = new_prefix
        probe_cache[key] = row
        return row

    # First buy the exact one-step evidence that produced the four survivors.
    candidate_nodes = sorted({node for pair in candidates for node in pair})
    for node in candidate_nodes:
        legal = q.nodes[node].legal_actions
        if not legal or any(action in (0, 6) for action in legal):
            raise AssertionError("ls20 expected enumerable primitive action alphabet")
        for action in legal:
            probe(node, action)

    one_step_parts = q.partitions(max_depth=max(8, len(q.nodes)))
    one_step_classes = one_step_parts[-1]
    survivors = [
        pair
        for pair in candidates
        if one_step_classes[pair[0]] == one_step_classes[pair[1]]
    ]
    assert len(survivors) == 4

    def close_root(root: tuple[str, str]) -> dict:
        queue = deque([(root[0], root[1], tuple())])
        seen: set[tuple[str, str]] = set()
        max_depth = 0

        while queue:
            left, right, word = queue.popleft()
            pair = tuple(sorted((left, right)))
            if pair in seen:
                continue
            if len(seen) >= MAX_PAIR_OBLIGATIONS:
                return {
                    "root": list(root),
                    "status": "UNKNOWN_OBLIGATION_BOUND",
                    "visited_pair_obligations": len(seen),
                    "max_depth": max_depth,
                    "separator_word": None,
                }
            seen.add(pair)
            max_depth = max(max_depth, len(word))

            if left == right:
                continue
            if left not in q.nodes or right not in q.nodes:
                raise AssertionError("closure obligation missing observed node")

            left_row = q.nodes[left]
            right_row = q.nodes[right]
            if left_row.protected != right_row.protected:
                return {
                    "root": list(root),
                    "status": "SPLIT_PROTECTED",
                    "visited_pair_obligations": len(seen),
                    "max_depth": max_depth,
                    "separator_word": list(word),
                }
            if left_row.legal_actions != right_row.legal_actions:
                return {
                    "root": list(root),
                    "status": "SPLIT_LEGALITY",
                    "visited_pair_obligations": len(seen),
                    "max_depth": max_depth,
                    "separator_word": list(word),
                }

            legal = left_row.legal_actions
            if any(action in (0, 6) for action in legal):
                return {
                    "root": list(root),
                    "status": "UNKNOWN_ACTION_LANGUAGE",
                    "visited_pair_obligations": len(seen),
                    "max_depth": max_depth,
                    "separator_word": list(word),
                }

            for action in legal:
                try:
                    left_probe = probe(left, action)
                    right_probe = probe(right, action)
                except RuntimeError as exc:
                    return {
                        "root": list(root),
                        "status": str(exc),
                        "visited_pair_obligations": len(seen),
                        "max_depth": max_depth,
                        "separator_word": list(word),
                    }

                extended = word + (int(action),)
                if tuple(left_probe["outcome"]) != tuple(right_probe["outcome"]):
                    return {
                        "root": list(root),
                        "status": "SPLIT_OUTCOME",
                        "visited_pair_obligations": len(seen),
                        "max_depth": max(max_depth, len(extended)),
                        "separator_word": list(extended),
                        "left_outcome": left_probe["outcome"],
                        "right_outcome": right_probe["outcome"],
                    }

                left_target = left_probe["target"]
                right_target = right_probe["target"]
                if left_target == right_target:
                    continue

                target_left = q.nodes[left_target]
                target_right = q.nodes[right_target]
                if (
                    target_left.protected != target_right.protected
                    or target_left.legal_actions != target_right.legal_actions
                ):
                    return {
                        "root": list(root),
                        "status": "SPLIT_TARGET_CONTRACT",
                        "visited_pair_obligations": len(seen),
                        "max_depth": max(max_depth, len(extended)),
                        "separator_word": list(extended),
                    }

                target_pair = tuple(sorted((left_target, right_target)))
                if target_pair not in seen:
                    queue.append((left_target, right_target, extended))

        return {
            "root": list(root),
            "status": "CLOSED_FINITE_BISIMULATION",
            "visited_pair_obligations": len(seen),
            "max_depth": max_depth,
            "separator_word": None,
        }

    results = []
    for root in survivors:
        row = close_root(root)
        results.append(row)
        print("BISIMULATION_ROOT=" + json.dumps(row, sort_keys=True), flush=True)

    report = {
        "interpretation": (
            "recursive paired primitive-action closure from the four one-step "
            "surviving ls20 interventional quotient pairs"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "source_trace": source_meta,
        "initial_candidate_pairs": len(candidates),
        "one_step_survivors": len(survivors),
        "active_probe_count": active_probe_count,
        "max_pair_obligations_per_root": MAX_PAIR_OBLIGATIONS,
        "max_active_probes": MAX_ACTIVE_PROBES,
        "results": results,
        "status_counts": {
            status: sum(row["status"] == status for row in results)
            for status in sorted({row["status"] for row in results})
        },
    }
    audit.write_json(OUT / "bisimulation-closure.json", report)
    print("INTERVENTIONAL_BISIMULATION_RESULT=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_INTERVENTIONAL_BISIMULATION_CLOSURE=PASS", flush=True)


if __name__ == "__main__":
    main()
