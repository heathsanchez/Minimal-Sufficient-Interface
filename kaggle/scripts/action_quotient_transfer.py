"""Prospective transfer test for an ft09 intervention quotient.

Learn a coordinate-action partition from two frequently revisited exact states,
using only equality of exact protected successor consequences. Then freeze that
partition and test whether every learned action equivalence survives on later
held development states from the same untouched frozen-MG-ARC5 trajectory.

The policy is never changed here. A learned action class is only evidence for
future promotion if all held states preserve the class under exact replay.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "action-quotient-transfer-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import action_quotient_diagnostic as aq

aq.OUT = OUT
aq.AGENT = AGENT

TRAIN_STATES = 2
HELD_STATES = 8


def consequence_table(module, game_id, envdir, digest, prefix):
    arc, _env, adapter, latest = aq.replay_state(
        module, game_id, envdir, prefix, digest
    )
    candidates = aq.candidate_catalog(module, adapter, latest)
    arc.close_scorecard()

    table = {}
    descriptors = {}
    for row in candidates:
        action = tuple(row["action"])
        consequence = aq.probe_action(
            module, game_id, envdir, prefix, digest, action
        )
        table[action] = (
            tuple(consequence["outcome"]),
            consequence["target"],
        )
        descriptors[action] = row["descriptor"]
    return table, descriptors


def stable_training_classes(tables):
    actions = sorted(set.intersection(*(set(table) for table in tables)))
    signatures = defaultdict(list)
    for action in actions:
        signature = tuple(table[action] for table in tables)
        signatures[signature].append(action)
    classes = [
        tuple(sorted(group))
        for _signature, group in sorted(
            signatures.items(),
            key=lambda item: (
                -len(item[1]),
                min(item[1]),
            ),
        )
    ]
    return classes


def main() -> None:
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]

    module, prefixes, visits, protected, trace = aq.collect_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    eligible = [
        (count, digest)
        for digest, count in visits.items()
        if protected[digest][0] == "NOT_FINISHED"
    ]
    eligible.sort(
        key=lambda row: (-row[0], len(prefixes[row[1]]), row[1])
    )
    selected = eligible[: TRAIN_STATES + HELD_STATES]
    assert len(selected) == TRAIN_STATES + HELD_STATES

    training = selected[:TRAIN_STATES]
    held = selected[TRAIN_STATES:]

    training_tables = []
    training_descriptors = []
    for count, digest in training:
        table, descriptors = consequence_table(
            module,
            game_id,
            manifest["environments_dir"],
            digest,
            prefixes[digest],
        )
        training_tables.append(table)
        training_descriptors.append(descriptors)
        print(
            "ACTION_QUOTIENT_TRAIN_STATE="
            + json.dumps(
                {
                    "source": digest[:16],
                    "visits": count,
                    "prefix_length": len(prefixes[digest]),
                    "actions": len(table),
                    "consequence_classes": len(set(table.values())),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    classes = stable_training_classes(training_tables)
    actions = sorted(set().union(*classes))
    class_by_action = {
        action: index
        for index, group in enumerate(classes)
        for action in group
    }

    descriptor_conflicts = {}
    descriptor_rows = defaultdict(set)
    for table, descriptors in zip(training_tables, training_descriptors):
        for action, descriptor in descriptors.items():
            descriptor_rows[descriptor].add(table[action])
    for descriptor, outcomes in descriptor_rows.items():
        if len(outcomes) > 1:
            descriptor_conflicts[descriptor] = len(outcomes)

    held_rows = []
    split_events = []
    all_held_consistent = True
    for count, digest in held:
        table, _descriptors = consequence_table(
            module,
            game_id,
            manifest["environments_dir"],
            digest,
            prefixes[digest],
        )
        missing = [action for action in actions if action not in table]
        class_splits = []
        if missing:
            all_held_consistent = False
        for class_id, group in enumerate(classes):
            present = [action for action in group if action in table]
            consequences = {
                table[action]
                for action in present
            }
            if len(present) != len(group) or len(consequences) != 1:
                all_held_consistent = False
                class_splits.append({
                    "class_id": class_id,
                    "member_count": len(group),
                    "present_count": len(present),
                    "consequence_count": len(consequences),
                })
                split_events.append({
                    "source": digest,
                    "class_id": class_id,
                    "members": [list(action) for action in group],
                    "consequences": [
                        {
                            "action": list(action),
                            "outcome": list(table[action][0]),
                            "target": table[action][1],
                        }
                        for action in present
                    ],
                })

        consequence_classes = len(set(table.values()))
        held_rows.append({
            "source": digest,
            "visits": count,
            "prefix_length": len(prefixes[digest]),
            "candidate_actions": len(table),
            "consequence_classes": consequence_classes,
            "learned_classes": len(classes),
            "missing_actions": [list(action) for action in missing],
            "class_splits": class_splits,
            "preserves_training_partition": (
                not missing and not class_splits
            ),
        })
        print(
            "ACTION_QUOTIENT_HELD_STATE="
            + json.dumps(
                held_rows[-1],
                sort_keys=True,
            ),
            flush=True,
        )

    class_rows = []
    for class_id, group in enumerate(classes):
        class_rows.append({
            "class_id": class_id,
            "size": len(group),
            "representative": list(min(group)),
            "members": [list(action) for action in group],
        })

    report = {
        "interpretation": (
            "prospective source-blind transfer test of a consequence-derived "
            "ft09 coordinate-action quotient; two training states and eight "
            "later held development states from frozen MG-ARC5"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "trace": trace,
        "training_state_count": len(training),
        "held_state_count": len(held),
        "action_count": len(actions),
        "learned_class_count": len(classes),
        "action_compression": len(actions) / max(1, len(classes)),
        "classes": class_rows,
        "held_results": held_rows,
        "held_split_events": split_events,
        "all_held_consistent": all_held_consistent,
        "descriptor_conflict_count": len(descriptor_conflicts),
        "descriptor_conflicts": descriptor_conflicts,
    }
    audit.write_json(OUT / "action-quotient-transfer.json", report)
    print(
        "ACTION_QUOTIENT_TRANSFER_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_ACTION_QUOTIENT_TRANSFER=PASS", flush=True)


if __name__ == "__main__":
    main()
