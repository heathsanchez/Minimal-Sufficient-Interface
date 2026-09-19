"""QCKN Flash Multigame V5: identity-free refutation survives cold restart."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=ROOT/"kaggle"/"scripts"
SRC=ROOT/"kaggle"/"src"
sys.path.insert(0,str(SCRIPTS))
sys.path.insert(0,str(SRC))

from arc3_flash_multigame_v2 import (
    SCOPE,
    destination_ref,
    destination_verifier,
    load_inputs,
    source_ledger,
)
from metalogic_arc3.flash_closure import (
    export_compiled_transfer_obstructions,
    import_compiled_transfer_obstructions,
    transfer_obstruction_key,
    transfer_proposal_blocked,
    validate_transfer_result,
)
from metalogic_arc3.flash_ledger import GlobalCapability


BASE="ft09:bounded-fatal-5454-family"


def evidence_key(ledger,game,kind):
    rows=[k for k,r in ledger.raw_evidence.items() if r.game==game and r.kind==kind]
    if len(rows)!=1:
        raise AssertionError(rows)
    return rows[0]


def replace_source_identity(ledger,new_id):
    base=ledger.capabilities[BASE]
    replacement=GlobalCapability(
        capability_id=new_id,
        kind=base.kind,
        source_games=set(base.source_games),
        scope=dict(base.scope),
        consequence_signature=tuple(base.consequence_signature),
        exact_witnesses=list(base.exact_witnesses),
        protected_effect=base.protected_effect,
        acquisition_cost=base.acquisition_cost+123,
        notes={"developmental_history":"cold-restart-replacement"},
    )
    del ledger.capabilities[BASE]
    ledger.add_capability(replacement)
    return new_id


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ft09-dir",required=True)
    p.add_argument("--v2-dir",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()

    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    inputs=load_inputs(Path(args.ft09_dir),Path(args.v2_dir))

    # Generation 1 learns the destination refutation under the historical source ID.
    learned=source_ledger(inputs)
    learned.add_evidence(destination_ref(inputs))
    dkey=evidence_key(learned,"vc33","public_v2_control")
    if destination_verifier(inputs):
        raise AssertionError("pinned destination unexpectedly verified transfer")
    validate_transfer_result(
        learned,
        source_capability_id=BASE,
        destination_game="vc33",
        destination_evidence_id=dkey,
        verified=False,
        exact_scope=SCOPE,
    )
    present=export_compiled_transfer_obstructions(learned)
    (out/"compiled-transfer-obstructions-v5.mg.json").write_text(present)

    # Cold restart: original capability identity is deliberately absent.
    restarted=source_ledger(inputs)
    replacement_id=replace_source_identity(
        restarted,
        "ft09:replacement-equivalent-consequence",
    )
    restarted.add_evidence(destination_ref(inputs))
    if BASE in restarted.capabilities:
        raise AssertionError("historical source identity leaked into restart")

    imported=import_compiled_transfer_obstructions(restarted,present)
    if imported!=1:
        raise AssertionError(imported)
    if not transfer_proposal_blocked(
        restarted,
        source_capability_id=replacement_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    ):
        raise AssertionError("equivalent consequence failed to inherit refutation")

    proposals=8
    verifier_calls=0
    blocked=0
    for _ in range(proposals):
        if transfer_proposal_blocked(
            restarted,
            source_capability_id=replacement_id,
            destination_game="vc33",
            exact_scope=SCOPE,
        ):
            blocked+=1
        else:
            verifier_calls+=1
            destination_verifier(inputs)

    if blocked!=8 or verifier_calls!=0:
        raise AssertionError((blocked,verifier_calls))

    # Changed consequence remains live.
    replacement=restarted.capabilities[replacement_id]
    changed_id="ft09:changed-consequence"
    restarted.add_capability(GlobalCapability(
        capability_id=changed_id,
        kind=replacement.kind,
        source_games=set(replacement.source_games),
        scope=dict(replacement.scope),
        consequence_signature=tuple(replacement.consequence_signature)+("changed",),
        exact_witnesses=list(replacement.exact_witnesses),
        protected_effect=replacement.protected_effect,
        acquisition_cost=replacement.acquisition_cost,
    ))
    changed_blocked=transfer_proposal_blocked(
        restarted,
        source_capability_id=changed_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    )
    if changed_blocked:
        raise AssertionError("identity-free restart erased a real consequence difference")

    # Exact ablation restores one destination verification obligation.
    key=transfer_obstruction_key(
        restarted,
        source_capability_id=replacement_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    )
    del restarted.obstructions[key]
    restored_blocked=transfer_proposal_blocked(
        restarted,
        source_capability_id=replacement_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    )
    if restored_blocked:
        raise AssertionError("ablation failed")
    ablation_calls=1
    destination_verifier(inputs)

    evidence={
        "schema":"qckn-flash-multigame-v5",
        "generation1_source_id":BASE,
        "restart_source_id":replacement_id,
        "original_source_present_after_restart":BASE in restarted.capabilities,
        "imported_obstructions":imported,
        "post_restart_proposals":proposals,
        "post_restart_blocked":blocked,
        "destination_verifier_calls_after_restart":verifier_calls,
        "changed_consequence_blocked":changed_blocked,
        "ablation_destination_verifier_calls_restored":ablation_calls,
        "compiled_present_bytes":len(present.encode()),
        "claim_boundary":(
            "one exact destination-refuted transfer compiled under pinned FT09 source "
            "authority and pinned VC33 destination authority, then reused after cold "
            "restart by a differently identified capability with the same certified "
            "source boundary. Source and destination evidence remain mandatory."
        ),
        "verdict":"PASS_IDENTITY_FREE_RESTARTED_REFUTATION_COMPOUNDING",
    }
    (out/"identity-free-restart.json").write_text(
        json.dumps(evidence,indent=2,sort_keys=True)+"\n"
    )
    print("QCKN_FLASH_MULTIGAME_V5="+evidence["verdict"])
    print("IDENTITY_FREE_RESTART="+json.dumps(evidence,sort_keys=True))


if __name__=="__main__":
    main()
