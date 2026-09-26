from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

import arc3_public_interface_genesis_g2 as historical
from metalogic_arc3.crystal_laws import (
    ArcCrystalLawBridge,
    Prediction,
    VerifiedLawStore,
)

OUT = ROOT / "evidence" / "arc3-crystal-real-separator-retrospective-v1" / "result.json"


def action_key(probe):
    r, c = probe
    return (6, c, r)


def probe_from_action(action):
    _aid, c, r = action
    return [r, c]


def predictions_from_records(records):
    rows = []
    for record in records:
        action = action_key(record["probe"])
        for detail in record["details"]:
            rows.append(Prediction(
                str(detail["candidate_id"]),
                action,
                historical.sig_key(detail["signature"]),
            ))
    return tuple(rows)


def evaluate_level(e, candidates, ids, pool, prefix=()):
    records = [
        historical.evaluate_probe(e, candidates, ids, probe, prefix=prefix)
        for probe in pool
    ]
    bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
    answer = bridge.choose_separator(
        hypotheses=tuple(str(x) for x in ids),
        actions=tuple(action_key(probe) for probe in pool),
        predictions=predictions_from_records(records),
        support_refs=("historical:tn36:35924850812",),
        live_supports=("historical:tn36:35924850812",),
    )
    return records, answer


def g6_no_safe_separator_control():
    bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
    probes = ((0, None, None),(1, None, None),(2, None, None),(3, None, None),(4, None, None))
    controls = {}
    for pair in (("UL","LL"),("LU","UU")):
        predictions = tuple(
            Prediction(h, action, "same-protected-response")
            for h in pair for action in probes
        )
        answer = bridge.choose_separator(
            hypotheses=pair,
            actions=probes,
            predictions=predictions,
            support_refs=("historical:g6:ordered-history:36087670806",),
            live_supports=("historical:g6:ordered-history:36087670806",),
        )
        controls["/".join(pair)] = {
            "status": answer.status.value,
            "reason": answer.reason,
            "worst_case_survivors": answer.worst_case_survivors,
        }
    return controls


def main():
    candidates = historical.candidate_programs()
    assert len(candidates) == 36
    e = historical.ds.env()

    base_grids = []
    for cand in candidates:
        _start, frame = historical.replay(e, cand)
        base_grids.append(historical.grid(frame))
    root_pool = historical.pool_from_grids(
        base_grids, historical.MAX_ROOT_PROBES, historical.KNOWN
    )
    all_ids = list(range(36))
    root_records, root_answer = evaluate_level(e, candidates, all_ids, root_pool)
    old_root = historical.best_probe(root_records)
    assert old_root is not None
    assert root_answer.chosen_action is not None
    crystal_root = probe_from_action(root_answer.chosen_action)
    assert crystal_root == old_root["probe"] == [32, 37]
    assert root_answer.worst_case_survivors == 27

    classes = {}
    for detail, signature in zip(old_root["details"], old_root["_signatures"]):
        classes.setdefault(signature, []).append(detail["candidate_id"])

    second_rows = []
    for signature, ids in sorted(classes.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(ids) < 2:
            continue
        post_grids, _hashes = historical.snapshot_grids(
            e, candidates, ids, (tuple(old_root["probe"]),)
        )
        pool = historical.pool_from_grids(
            post_grids, historical.MAX_SECOND_PROBES, historical.KNOWN
        )
        records, answer = evaluate_level(
            e, candidates, ids, pool, prefix=(tuple(old_root["probe"]),)
        )
        old_best = historical.best_probe(records)
        assert old_best is not None
        assert answer.chosen_action is not None
        crystal_probe = probe_from_action(answer.chosen_action)
        assert crystal_probe == old_best["probe"]
        second_rows.append({
            "candidate_count": len(ids),
            "historical_probe": old_best["probe"],
            "crystal_probe": crystal_probe,
            "worst_case_survivors": answer.worst_case_survivors,
        })

    expected = {(27, (38,38), 18), (9, (32,42), 6)}
    actual = {
        (row["candidate_count"], tuple(row["crystal_probe"]), row["worst_case_survivors"])
        for row in second_rows
    }
    assert actual == expected

    g6_controls = g6_no_safe_separator_control()
    assert all(row["status"] == "EXCLUDED" for row in g6_controls.values())

    out = {
        "schema": "msi.arc3-crystal-real-separator-retrospective-v1",
        "status": "QUALIFIED_BOUNDED",
        "public_game": "tn36-ef4dde99",
        "historical_authority": {
            "head": "d64598072d7ccb116eceef7394bc4eda2243d841",
            "run": 35924850812,
            "artifact": 10778378268,
            "artifact_digest": "sha256:d8ed85d6d84c9f8ce6f9b1452fe197dac541e763524909f5ad8b3f4e0b584787",
            "candidate_worlds": 36,
        },
        "root": {
            "historical_probe": old_root["probe"],
            "crystal_probe": crystal_root,
            "partition_counts": sorted(old_root["partition"]["counts"].values(), reverse=True),
            "worst_case_survivors": root_answer.worst_case_survivors,
            "probe_pool": len(root_pool),
        },
        "second_level": second_rows,
        "parity": "EXACT_ON_HISTORICAL_ACTIVE_PROBE_POLICY",
        "g6_negative_control": {
            "authority_run": 36087670806,
            "declared_suffix_bank": ["epsilon","U","D","L","R"],
            "pairs": g6_controls,
            "result": "NO_SAFE_SEPARATOR_REPRODUCED",
        },
        "action_savings_claim": None,
        "interpretation": (
            "The generic Crystal finite-separator law exactly reproduces the bespoke "
            "historical tn36 active-probe choices when given the same complete frozen "
            "candidate-response tables. It also refuses a later G6 bounded case where "
            "the declared safe suffix bank did not separate rival histories."
        ),
        "boundary": (
            "This is real-public-game policy parity, not evidence that Crystal reduces "
            "actions relative to the already-active historical controller. The frozen "
            "prediction tables were generated by black-box candidate-world replay; "
            "the next residual is to predict them cheaply from a learned world model."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
