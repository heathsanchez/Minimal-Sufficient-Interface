"""Explore the exact successor cone of the ls20 convergence state.

This continues the QCKN obligation created by the interventional quotient
closure. Several independently certified equivalent state classes converge,
under every primitive action, to one exact public observation. We now ask the
stronger question: does the full primitive-action cone reachable from that
observation contain any protected progress?

Every newly discovered state is reached by an exact replay prefix from RESET
and every legal primitive action is tried. The result is either an explicit
progress word, an UNKNOWN boundary, or a finite closed no-progress component.

The frozen MG-ARC5 policy is unchanged.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "interventional-dead-component-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import interventional_separator_probe as sep
import interventional_closure_probe as closure

sep.OUT = OUT
sep.AGENT = AGENT
closure.OUT = OUT
closure.AGENT = AGENT

TARGET = "a119b0226fa1f7a53705a4eadd418c01a1b78d1dd850c2621ce7825f70046a89"
MAX_STATES = 256
MAX_NEW_PROBES = 1024


def prepare_certificate_context(module, q, prefix_by_digest, game_id, envdir, candidates):
    """Reproduce the verified one-step probes and enough closure to obtain TARGET."""

    candidate_nodes = sorted({node for pair in candidates for node in pair})
    for node in candidate_nodes:
        legal = q.nodes[node].legal_actions
        if not legal or any(action in (0, 6) for action in legal):
            raise AssertionError("ls20 expected primitive action contract")
        for action in legal:
            prefix = prefix_by_digest[node]
            row = sep.replay_and_probe(
                module, game_id, envdir, prefix, node, action
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

    closer = closure.ClosureProbe(
        module, q, prefix_by_digest, game_id, envdir
    )
    result = closer.close_root(surviving[0])
    assert result["status"] == "CLOSED_BOUNDED_REPLAY_BISIMULATION"
    assert TARGET in prefix_by_digest
    return surviving, closer.new_probes


def explore_component(module, q, prefix_by_digest, game_id, envdir):
    explorer = closure.ClosureProbe(
        module, q, prefix_by_digest, game_id, envdir
    )
    explorer.new_probes = 0

    start_level = int(q.nodes[TARGET].protected[1])
    queue = deque([(TARGET, ())])
    seen: dict[str, tuple[int, ...]] = {}
    edges: list[dict] = []
    terminal_states: list[str] = []

    while queue:
        if len(seen) >= MAX_STATES:
            return {
                "status": "UNKNOWN_STATE_BOUND",
                "root": TARGET,
                "states": len(seen),
                "new_probes": explorer.new_probes,
                "edges": edges,
                "terminal_states": terminal_states,
            }
        if explorer.new_probes >= MAX_NEW_PROBES:
            return {
                "status": "UNKNOWN_PROBE_BOUND",
                "root": TARGET,
                "states": len(seen),
                "new_probes": explorer.new_probes,
                "edges": edges,
                "terminal_states": terminal_states,
            }

        node, word = queue.popleft()
        if node in seen:
            continue
        seen[node] = tuple(word)
        record = q.nodes[node]
        state = str(record.protected[0])
        level = int(record.protected[1])

        if level > start_level:
            return {
                "status": "PROGRESS_FOUND",
                "root": TARGET,
                "progress_word": list(word),
                "progress_state": node,
                "progress_level": level,
                "states": len(seen),
                "new_probes": explorer.new_probes,
                "edges": edges,
                "terminal_states": terminal_states,
            }

        if state in ("WIN", "GAME_OVER"):
            terminal_states.append(node)
            continue

        legal = tuple(record.legal_actions)
        if not legal:
            return {
                "status": "UNKNOWN_NO_ACTION_CONTRACT",
                "root": TARGET,
                "state": node,
                "word": list(word),
                "states": len(seen),
                "new_probes": explorer.new_probes,
                "edges": edges,
                "terminal_states": terminal_states,
            }
        if any(action in (0, 6) for action in legal):
            return {
                "status": "UNKNOWN_PARAMETERIZED_OR_RESET_ACTION",
                "root": TARGET,
                "state": node,
                "word": list(word),
                "legal_actions": list(legal),
                "states": len(seen),
                "new_probes": explorer.new_probes,
                "edges": edges,
                "terminal_states": terminal_states,
            }

        for action in legal:
            rows = explorer.ensure_action(node, int(action))
            if len(rows) != 1:
                return {
                    "status": "UNKNOWN_NONDETERMINISTIC_OBSERVATION",
                    "root": TARGET,
                    "state": node,
                    "word": list(word),
                    "action": int(action),
                    "successor_count": len(rows),
                    "states": len(seen),
                    "new_probes": explorer.new_probes,
                    "edges": edges,
                    "terminal_states": terminal_states,
                }
            outcome, target = next(iter(rows))
            next_word = tuple(word) + (int(action),)
            edge = {
                "source": node,
                "action": int(action),
                "outcome": outcome,
                "target": target,
            }
            edges.append(edge)
            target_record = q.nodes[target]
            target_level = int(target_record.protected[1])
            if (
                isinstance(outcome, tuple)
                and outcome
                and str(outcome[0]) == "LEVEL_INCREMENT"
            ) or target_level > start_level:
                return {
                    "status": "PROGRESS_FOUND",
                    "root": TARGET,
                    "progress_word": list(next_word),
                    "progress_state": target,
                    "progress_level": target_level,
                    "states": len(seen),
                    "new_probes": explorer.new_probes,
                    "edges": edges,
                    "terminal_states": terminal_states,
                }
            if target not in seen:
                queue.append((target, next_word))

    return {
        "status": "CLOSED_BOUNDED_NO_PROGRESS_COMPONENT",
        "root": TARGET,
        "states": len(seen),
        "new_probes": explorer.new_probes,
        "edges": edges,
        "terminal_states": sorted(set(terminal_states)),
        "state_words": {
            node: list(word) for node, word in sorted(seen.items())
        },
        "component_states": sorted(seen),
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
    classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    candidates = sep.merged_pairs(classes, original_nodes)
    assert len(original_nodes) == 355
    assert len(candidates) == 15

    survivors, certificate_probes = prepare_certificate_context(
        module,
        q,
        prefix_by_digest,
        game_id,
        manifest["environments_dir"],
        candidates,
    )
    result = explore_component(
        module,
        q,
        prefix_by_digest,
        game_id,
        manifest["environments_dir"],
    )

    report = {
        "interpretation": (
            "exact replay exploration of the primitive-action successor cone "
            "of the ls20 convergence state exposed by certified interventional "
            "quotient closure; public development evidence only"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "source_trace": source_meta,
        "initial_candidate_pairs": len(candidates),
        "one_step_survivors": len(survivors),
        "certificate_new_probes": certificate_probes,
        "component": result,
    }
    audit.write_json(OUT / "dead-component.json", report)
    print(
        "INTERVENTIONAL_DEAD_COMPONENT_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_INTERVENTIONAL_DEAD_COMPONENT=PASS", flush=True)


if __name__ == "__main__":
    main()
