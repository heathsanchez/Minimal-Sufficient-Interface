"""Recursively close the surviving ls20 interventional quotient obligations.

This follows the QCK/QCKN rule literally: a state-pair merge is not retained
because one-step probes happen to match. Every matched primitive intervention
creates a successor-pair obligation. The closure explores that obligation graph
until it finds a concrete separating action word or closes a finite observed
bisimulation cone under the ls20 primitive action contract.

The frozen MG-ARC5 policy remains unchanged. This is development evidence over
exact replayed public trajectories, not a hidden-generalization claim.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "interventional-closure-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

from metalogic_arc3.interventional_quotient import PartialInterventionalQuotient
import interventional_separator_probe as sep

sep.OUT = OUT
sep.AGENT = AGENT

MAX_NEW_PROBES = 512
MAX_PAIR_OBLIGATIONS = 2048


def canonical_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def terminal(node_record) -> bool:
    state = str(node_record.protected[0]) if node_record.protected else ""
    return state in ("WIN", "GAME_OVER")


class ClosureProbe:
    def __init__(self, module, q, prefix_by_digest, game_id, envdir):
        self.module = module
        self.q: PartialInterventionalQuotient = q
        self.prefix_by_digest = prefix_by_digest
        self.game_id = game_id
        self.envdir = envdir
        self.new_probes = 0
        self.probe_rows: list[dict] = []

    def ensure_action(self, node: str, action: int) -> set[tuple[object, str]]:
        existing = self.q.edges.get(node, {}).get(int(action), set())
        if existing:
            return set(existing)
        if self.new_probes >= MAX_NEW_PROBES:
            raise RuntimeError("separator probe budget exhausted")
        prefix = self.prefix_by_digest.get(node)
        if prefix is None:
            raise RuntimeError("no exact replay prefix for quotient obligation")
        row = sep.replay_and_probe(
            self.module,
            self.game_id,
            self.envdir,
            prefix,
            node,
            int(action),
        )
        self.new_probes += 1
        self.probe_rows.append(row)
        self.q.observe_node(
            row["target"],
            protected=tuple(row["target_protected"]),
            legal_actions=tuple(row["target_legal_actions"]),
        )
        self.q.observe_transition(
            row["source"],
            row["action"],
            row["target"],
            outcome=tuple(row["outcome"]),
        )
        action_key = (int(action), None, None)
        candidate_prefix = tuple(prefix) + (action_key,)
        old = self.prefix_by_digest.get(row["target"])
        if old is None or len(candidate_prefix) < len(old):
            self.prefix_by_digest[row["target"]] = candidate_prefix
        print(
            "CLOSURE_PROBE="
            + json.dumps(
                {
                    "source": node[:16],
                    "action": int(action),
                    "target": row["target"][:16],
                    "outcome": row["outcome"],
                    "probe_index": self.new_probes,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return set(self.q.edges[node][int(action)])

    def close_root(self, root: tuple[str, str]) -> dict:
        root = canonical_pair(*root)
        queue = deque([(root, ())])
        seen: dict[tuple[str, str], tuple[int, ...]] = {}
        edges: list[dict] = []

        while queue:
            if len(seen) > MAX_PAIR_OBLIGATIONS:
                return {
                    "root": root,
                    "status": "UNKNOWN_PAIR_BOUND",
                    "separator_word": None,
                    "pair_obligations": len(seen),
                    "edges": edges,
                }
            pair, word = queue.popleft()
            pair = canonical_pair(*pair)
            if pair[0] == pair[1]:
                continue
            if pair in seen:
                continue
            seen[pair] = tuple(word)
            left, right = pair
            lrow = self.q.nodes[left]
            rrow = self.q.nodes[right]

            if lrow.protected != rrow.protected:
                return {
                    "root": root,
                    "status": "SEPARATED",
                    "separator_word": list(word),
                    "reason": "protected_outcome",
                    "witness_pair": pair,
                    "pair_obligations": len(seen),
                    "edges": edges,
                }
            if lrow.legal_actions != rrow.legal_actions:
                return {
                    "root": root,
                    "status": "SEPARATED",
                    "separator_word": list(word),
                    "reason": "legal_action_contract",
                    "witness_pair": pair,
                    "pair_obligations": len(seen),
                    "edges": edges,
                }
            if terminal(lrow):
                continue

            legal = tuple(lrow.legal_actions)
            if not legal:
                return {
                    "root": root,
                    "status": "UNKNOWN_NO_ACTION_CONTRACT",
                    "separator_word": None,
                    "witness_pair": pair,
                    "pair_obligations": len(seen),
                    "edges": edges,
                }
            if any(action == 6 for action in legal):
                return {
                    "root": root,
                    "status": "UNKNOWN_PARAMETERIZED_ACTION",
                    "separator_word": None,
                    "witness_pair": pair,
                    "pair_obligations": len(seen),
                    "edges": edges,
                }

            for action in legal:
                left_rows = self.ensure_action(left, action)
                right_rows = self.ensure_action(right, action)

                if len(left_rows) != 1 or len(right_rows) != 1:
                    return {
                        "root": root,
                        "status": "UNKNOWN_NONDETERMINISTIC_OBSERVATION",
                        "separator_word": None,
                        "witness_pair": pair,
                        "action": int(action),
                        "left_successors": len(left_rows),
                        "right_successors": len(right_rows),
                        "pair_obligations": len(seen),
                        "edges": edges,
                    }

                left_outcome, left_target = next(iter(left_rows))
                right_outcome, right_target = next(iter(right_rows))
                next_word = tuple(word) + (int(action),)
                edge = {
                    "pair": pair,
                    "action": int(action),
                    "left_outcome": left_outcome,
                    "right_outcome": right_outcome,
                    "left_target": left_target,
                    "right_target": right_target,
                }
                edges.append(edge)

                if left_outcome != right_outcome:
                    return {
                        "root": root,
                        "status": "SEPARATED",
                        "separator_word": list(next_word),
                        "reason": "transition_outcome",
                        "witness_pair": pair,
                        "action": int(action),
                        "pair_obligations": len(seen),
                        "edges": edges,
                    }
                if left_target != right_target:
                    queue.append((
                        canonical_pair(left_target, right_target),
                        next_word,
                    ))

        return {
            "root": root,
            "status": "CLOSED_BOUNDED_REPLAY_BISIMULATION",
            "separator_word": None,
            "pair_obligations": len(seen),
            "edges": edges,
            "closed_pairs": [
                {"pair": pair, "word": list(word)}
                for pair, word in sorted(seen.items())
            ],
        }


def main() -> None:
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ls20-")
    )
    game_id = game["game_id"]

    module, q, prefix_by_digest, source_meta = sep.build_frozen_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    original_nodes = set(q.nodes)
    parts = q.partitions(max_depth=max(8, len(q.nodes)))
    candidates = sep.merged_pairs(parts[-1], original_nodes)
    assert len(original_nodes) == 355
    assert len(candidates) == 15

    # Reproduce the first active-separator round exactly.
    first_nodes = sorted({node for pair in candidates for node in pair})
    for node in first_nodes:
        legal = q.nodes[node].legal_actions
        assert legal and not any(action in (0, 6) for action in legal)
        for action in legal:
            prefix = prefix_by_digest[node]
            row = sep.replay_and_probe(
                module,
                game_id,
                manifest["environments_dir"],
                prefix,
                node,
                action,
            )
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
            candidate_prefix = tuple(prefix) + ((int(action), None, None),)
            old = prefix_by_digest.get(row["target"])
            if old is None or len(candidate_prefix) < len(old):
                prefix_by_digest[row["target"]] = candidate_prefix

    classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    surviving = [
        pair for pair in candidates
        if classes[pair[0]] == classes[pair[1]]
    ]
    assert len(surviving) == 4

    closer = ClosureProbe(
        module,
        q,
        prefix_by_digest,
        game_id,
        manifest["environments_dir"],
    )
    results = [closer.close_root(pair) for pair in surviving]

    final_summary = q.summary(max_depth=max(8, len(q.nodes)))
    final = final_summary["depths"][-1]
    assert final_summary["stabilized"]
    assert final["contradictory_merged_pairs"] == 0

    report = {
        "interpretation": (
            "recursive continuation closure of the four ls20 state pairs that "
            "survived all one-step primitive probes; exact replayed public "
            "development evidence, not universal hidden-state equivalence"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "source_trace": source_meta,
        "initial_candidate_pairs": len(candidates),
        "one_step_survivors": len(surviving),
        "closure_new_probes": closer.new_probes,
        "closure_results": results,
        "separated_roots": sum(
            row["status"] == "SEPARATED" for row in results
        ),
        "closed_roots": sum(
            row["status"] == "CLOSED_BOUNDED_REPLAY_BISIMULATION"
            for row in results
        ),
        "unknown_roots": sum(
            row["status"].startswith("UNKNOWN") for row in results
        ),
        "final_quotient": final,
        "final_summary": final_summary,
    }
    audit.write_json(OUT / "closure-probe.json", report)
    print(
        "INTERVENTIONAL_CLOSURE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_INTERVENTIONAL_CLOSURE=PASS", flush=True)


if __name__ == "__main__":
    main()
