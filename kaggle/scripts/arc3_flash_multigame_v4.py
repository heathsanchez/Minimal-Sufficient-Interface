"""QCKN Flash Multigame V4: consequence-quotiented refutation reuse.

Eight source capabilities have distinct identities/cost histories but the same
certified consequential boundary. One exact destination refutation should settle
the transfer proposal for all eight. A genuinely different consequence must not
inherit the refutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "kaggle" / "scripts"
SRC = ROOT / "kaggle" / "src"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from arc3_flash_multigame_v2 import (
    SCOPE,
    destination_ref,
    destination_verifier,
    load_inputs,
    source_ledger,
)
from metalogic_arc3.flash_closure import (
    transfer_obstruction_key,
    transfer_proposal_blocked,
    validate_transfer_result,
)
from metalogic_arc3.flash_ledger import GlobalCapability


def add_equivalent_sources(ledger, count=8):
    base = ledger.capabilities["ft09:bounded-fatal-5454-family"]
    ids = []
    for i in range(count):
        cid = f"ft09:equivalent-history-{i}"
        ledger.add_capability(
            GlobalCapability(
                capability_id=cid,
                kind=base.kind,
                source_games=set(base.source_games),
                scope=dict(base.scope),
                consequence_signature=tuple(base.consequence_signature),
                exact_witnesses=list(base.exact_witnesses),
                protected_effect=base.protected_effect,
                acquisition_cost=base.acquisition_cost + i + 1,
                notes={"developmental_history": f"history-{i}"},
            )
        )
        ids.append(cid)
    return ids


def destination_key(ledger):
    rows=[
        key for key,ref in ledger.raw_evidence.items()
        if ref.game=="vc33" and ref.kind=="public_v2_control"
    ]
    if len(rows)!=1:
        raise AssertionError(rows)
    return rows[0]


def run_arm(inputs, arm):
    ledger=source_ledger(inputs)
    source_ids=add_equivalent_sources(ledger)
    upfront=[
        transfer_proposal_blocked(
            ledger,
            source_capability_id=cid,
            destination_game="vc33",
            exact_scope=SCOPE,
        )
        for cid in source_ids
    ]
    if any(upfront):
        raise AssertionError("consequence refutation existed before destination collision")

    ledger.add_evidence(destination_ref(inputs))
    dkey=destination_key(ledger)
    calls=0
    blocked=0

    for cid in source_ids:
        if arm=="flash" and transfer_proposal_blocked(
            ledger,
            source_capability_id=cid,
            destination_game="vc33",
            exact_scope=SCOPE,
        ):
            blocked += 1
            continue

        calls += 1
        verified=destination_verifier(inputs)
        if verified:
            raise AssertionError("pinned destination unexpectedly verified transfer")
        validate_transfer_result(
            ledger,
            source_capability_id=cid,
            destination_game="vc33",
            destination_evidence_id=dkey,
            verified=False,
            exact_scope=SCOPE,
        )
        if arm=="ablation":
            key=transfer_obstruction_key(
                ledger,
                source_capability_id=cid,
                destination_game="vc33",
                exact_scope=SCOPE,
            )
            del ledger.obstructions[key]

    return {
        "arm":arm,
        "source_capability_ids":source_ids,
        "distinct_source_ids":len(set(source_ids)),
        "destination_verifier_calls":calls,
        "proposals_blocked_after_evidence":blocked,
        "upfront_blocked":any(upfront),
        "obstruction_count":sum(
            row.get("kind")=="exact_transfer_refutation"
            for row in ledger.obstructions.values()
        ),
    }, ledger


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ft09-dir",required=True)
    p.add_argument("--v2-dir",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()

    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    inputs=load_inputs(Path(args.ft09_dir),Path(args.v2_dir))

    independent,_=run_arm(inputs,"independent")
    flash,flash_ledger=run_arm(inputs,"flash")
    ablation,_=run_arm(inputs,"ablation")

    if independent["destination_verifier_calls"] != 8:
        raise AssertionError(independent)
    if flash["destination_verifier_calls"] != 1:
        raise AssertionError(flash)
    if flash["proposals_blocked_after_evidence"] != 7:
        raise AssertionError(flash)
    if flash["upfront_blocked"]:
        raise AssertionError("quotient gain existed upfront")
    if ablation["destination_verifier_calls"] != 8:
        raise AssertionError(ablation)

    # A real consequential difference must remain distinguishable.
    base=flash_ledger.capabilities["ft09:equivalent-history-0"]
    different_id="ft09:real-consequence-difference"
    flash_ledger.add_capability(
        GlobalCapability(
            capability_id=different_id,
            kind=base.kind,
            source_games=set(base.source_games),
            scope=dict(base.scope),
            consequence_signature=tuple(base.consequence_signature)+("different",),
            exact_witnesses=list(base.exact_witnesses),
            protected_effect=base.protected_effect,
            acquisition_cost=base.acquisition_cost,
        )
    )
    changed_blocked=transfer_proposal_blocked(
        flash_ledger,
        source_capability_id=different_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    )
    if changed_blocked:
        raise AssertionError("consequence quotient erased a real distinction")

    evidence={
        "schema":"qckn-flash-multigame-v4",
        "independent":independent,
        "flash":flash,
        "ablation":ablation,
        "changed_consequence_blocked":changed_blocked,
        "delta":{
            "destination_verifier_calls_eliminated":
                independent["destination_verifier_calls"]-flash["destination_verifier_calls"],
            "elimination_ratio":
                1.0-flash["destination_verifier_calls"]/independent["destination_verifier_calls"],
        },
        "claim_boundary":(
            "bounded reuse of an exact destination-refuted transfer across source "
            "capabilities sharing kind, source domain, source scope, consequence "
            "signature and protected effect. Capability identity, cost, notes and "
            "developmental provenance do not distinguish the active transfer "
            "obligation. A changed consequence remains distinct."
        ),
        "verdict":"PASS_CONSEQUENCE_QUOTIENTED_REFUTATION_COMPOUNDING",
    }
    (out/"consequence-quotient-refutation.json").write_text(
        json.dumps(evidence,indent=2,sort_keys=True)+"\n"
    )
    print("QCKN_FLASH_MULTIGAME_V4="+evidence["verdict"])
    print("CONSEQUENCE_QUOTIENT="+json.dumps(evidence,sort_keys=True))


if __name__=="__main__":
    main()
