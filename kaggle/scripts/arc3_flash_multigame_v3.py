"""QCKN Flash Multigame V3: exact refutation survives canonical restart."""
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
    export_compiled_transfer_obstructions,
    import_compiled_transfer_obstructions,
    transfer_obstruction_key,
    transfer_proposal_blocked,
    validate_transfer_result,
)
from metalogic_arc3.flash_ledger import EvidenceRef


def evidence_key(ledger, game: str, kind: str) -> str:
    rows = [
        key
        for key, ref in ledger.raw_evidence.items()
        if ref.game == game and ref.kind == kind
    ]
    if len(rows) != 1:
        raise AssertionError((game, kind, rows))
    return rows[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ft09-dir", required=True)
    parser.add_argument("--v2-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(Path(args.ft09_dir), Path(args.v2_dir))

    # Generation 1: the first live proposal cannot be blocked before destination evidence.
    learned = source_ledger(inputs)
    source_id = "ft09:bounded-fatal-5454-family"
    if transfer_proposal_blocked(
        learned,
        source_capability_id=source_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    ):
        raise AssertionError("refutation existed before first destination collision")

    learned.add_evidence(destination_ref(inputs))
    first_verifier_calls = 1
    if destination_verifier(inputs):
        raise AssertionError("pinned vc33 evidence unexpectedly verifies fatal transfer")
    destination_key = evidence_key(learned, "vc33", "public_v2_control")
    validate_transfer_result(
        learned,
        source_capability_id=source_id,
        destination_game="vc33",
        destination_evidence_id=destination_key,
        verified=False,
        exact_scope=SCOPE,
    )
    present = export_compiled_transfer_obstructions(learned)
    (out / "compiled-transfer-obstructions.mg.json").write_text(present)

    # Cold process restart: rebuild only source capability + authority evidence pointer,
    # then install the compiled obstruction. No destination verifier is called.
    restarted = source_ledger(inputs)
    restarted.add_evidence(destination_ref(inputs))
    imported = import_compiled_transfer_obstructions(restarted, present)
    if imported != 1:
        raise AssertionError(imported)
    if not transfer_proposal_blocked(
        restarted,
        source_capability_id=source_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    ):
        raise AssertionError("compiled refutation did not survive restart")

    post_restart_proposals = 8
    post_restart_verifier_calls = 0
    blocked = 0
    for _ in range(post_restart_proposals):
        if transfer_proposal_blocked(
            restarted,
            source_capability_id=source_id,
            destination_game="vc33",
            exact_scope=SCOPE,
        ):
            blocked += 1
            continue
        post_restart_verifier_calls += 1
        destination_verifier(inputs)

    if blocked != post_restart_proposals or post_restart_verifier_calls != 0:
        raise AssertionError((blocked, post_restart_verifier_calls))

    # Changed scope is not licensed by the exact compiled obstruction.
    changed_scope = dict(SCOPE)
    changed_scope["claim"] = "different transfer claim"
    changed_scope_blocked = transfer_proposal_blocked(
        restarted,
        source_capability_id=source_id,
        destination_game="vc33",
        exact_scope=changed_scope,
    )
    if changed_scope_blocked:
        raise AssertionError("exact obstruction leaked to a changed scope")

    # Exact ablation restores a verifier obligation.
    obstruction_key = transfer_obstruction_key(
        restarted,
        source_capability_id=source_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    )
    del restarted.obstructions[obstruction_key]
    if transfer_proposal_blocked(
        restarted,
        source_capability_id=source_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    ):
        raise AssertionError("ablation failed to restore unresolved proposal")
    ablation_verifier_calls = 1
    destination_verifier(inputs)

    # Stale authority evidence cannot import the present.
    stale = source_ledger(inputs)
    ref = destination_ref(inputs)
    stale_ref = EvidenceRef(
        ref.game,
        ref.kind,
        ref.artifact_or_run,
        ref.local_key,
        "STALE-" + str(ref.sha256),
    )
    stale.add_evidence(stale_ref)
    stale_rejected = False
    try:
        import_compiled_transfer_obstructions(stale, present)
    except ValueError as exc:
        stale_rejected = "destination evidence mismatch" in str(exc)
    if not stale_rejected:
        raise AssertionError("stale destination evidence was not rejected")

    evidence = {
        "schema": "qckn-flash-multigame-v3",
        "first_generation": {
            "destination_verifier_calls": first_verifier_calls,
            "compiled_obstruction_count": 1,
        },
        "restart": {
            "imported_obstructions": imported,
            "post_restart_proposals": post_restart_proposals,
            "blocked_after_restart": blocked,
            "destination_verifier_calls_after_restart": post_restart_verifier_calls,
            "changed_scope_blocked": changed_scope_blocked,
        },
        "ablation": {
            "destination_verifier_calls_restored": ablation_verifier_calls,
        },
        "stale_control": {
            "destination_evidence_rejected": stale_rejected,
        },
        "compiled_present_bytes": len(present.encode("utf-8")),
        "claim_boundary": (
            "exact canonical restart reuse of one destination-refuted transfer "
            "fingerprint against the same pinned source capability and destination "
            "evidence identity; no broader semantic transfer or game-solving gain"
        ),
        "verdict": "PASS_RESTARTED_REFUTATION_COMPOUNDING",
    }
    (out / "restart-refutation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )
    print("QCKN_FLASH_MULTIGAME_V3=" + evidence["verdict"])
    print("RESTART_REFUTATION=" + json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
