"""QCKN Flash Multigame V2: online exact-refutation compounding.

The source capability and destination evidence are pinned real ARC3 retained artifacts.
The destination evidence is deliberately withheld from shared state until the first
proposal, so no admissible upfront guard exists. The first destination check may
compile only an exact source/destination/scope refutation. Future identical
proposals may reuse it; changed scope may not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.flash_closure import (
    transfer_obstruction_key,
    transfer_proposal_blocked,
    validate_transfer_result,
)
from metalogic_arc3.flash_ledger import EvidenceRef, GlobalCapability, GlobalLedger

FT09_RUN = "35387362885"
FT09_ARTIFACT = "10564626208"
FT09_ARTIFACT_DIGEST = "sha256:22748bb909fae8087e90bc51bd26780466dd153dd1974782515e676d0d24bd05"
V2_RUN = "35398347557"
V2_ARTIFACT = "10569651788"
V2_ARTIFACT_DIGEST = "sha256:4e00a55675ea50c5f5b772b670d8651345ef712a053b4e7c283423b448fabdc2"

SCOPE = {
    "intervention_language": "complex_action6",
    "claim": "generic fatal-family transfer",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def find_one(root: Path, name: str) -> Path:
    rows = list(root.rglob(name))
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one {name} below {root}, got {len(rows)}")
    return rows[0]


def load_inputs(ft09_dir: Path, v2_dir: Path):
    ft_path = find_one(ft09_dir, "ft09-fatal-basin-certificate.json")
    v2_path = find_one(v2_dir, "global-flash-closure-v1.json")
    return {
        "ft_path": ft_path,
        "v2_path": v2_path,
        "ft": json.loads(ft_path.read_text()),
        "v2": json.loads(v2_path.read_text()),
    }


def source_ledger(inputs):
    ledger = GlobalLedger(["ft09", "vc33"])
    ftref = EvidenceRef(
        "ft09",
        "fatal_basin_certificate",
        f"run:{FT09_RUN}/artifact:{FT09_ARTIFACT}",
        "ft09-fatal-basin-certificate.json",
        sha256(inputs["ft_path"]),
    )
    ledger.add_evidence(ftref)
    ft = inputs["ft"]
    ledger.add_capability(
        GlobalCapability(
            "ft09:bounded-fatal-5454-family",
            "fatal_basin",
            {"ft09"},
            {
                "phase": "L0",
                "intervention_language": "complex_action6",
                "family": "54,54 progression + six ranked alternatives",
            },
            ("bounded_repeated_action_family", "fatal_or_nochange", "complex_action6"),
            [ftref],
            None,
            int(ft["probe_count"]),
            notes={
                "tested_source_states": ft["tested_source_states"],
                "probe_count": ft["probe_count"],
            },
        )
    )
    return ledger


def destination_ref(inputs):
    return EvidenceRef(
        "vc33",
        "public_v2_control",
        f"run:{V2_RUN}/artifact:{V2_ARTIFACT}",
        "market_local.vc33",
        sha256(inputs["v2_path"]),
    )


def destination_verifier(inputs) -> bool:
    """Return True only if the generic fatal-family transfer survives vc33 evidence."""
    vc = inputs["v2"]["arms"]["market_local"]["games"]["vc33-5430563c"]
    # Reaching L1 is an exact counterexample to the proposed generic L0-fatal transfer.
    return int(vc["max_level"]) < 1


def run_arm(inputs, arm: str, proposals: int = 8):
    ledger = source_ledger(inputs)
    source_id = "ft09:bounded-fatal-5454-family"
    upfront_blocked = transfer_proposal_blocked(
        ledger,
        source_capability_id=source_id,
        destination_game="vc33",
        exact_scope=SCOPE,
    )
    if upfront_blocked:
        raise AssertionError("an online refutation guard existed before destination evidence")

    verifier_calls = 0
    blocked = 0
    admitted_destination = False
    first_refutation_index = None

    for i in range(proposals):
        use_guard = arm == "flash"
        if use_guard and transfer_proposal_blocked(
            ledger,
            source_capability_id=source_id,
            destination_game="vc33",
            exact_scope=SCOPE,
        ):
            blocked += 1
            continue

        if not admitted_destination:
            ledger.add_evidence(destination_ref(inputs))
            admitted_destination = True

        verifier_calls += 1
        verified = destination_verifier(inputs)
        if verified:
            raise AssertionError("pinned vc33 evidence unexpectedly verified generic fatal transfer")

        key = next(
            k for k, ref in ledger.raw_evidence.items()
            if ref.game == "vc33" and ref.kind == "public_v2_control"
        )
        validate_transfer_result(
            ledger,
            source_capability_id=source_id,
            destination_game="vc33",
            destination_evidence_id=key,
            verified=False,
            exact_scope=SCOPE,
        )
        if first_refutation_index is None:
            first_refutation_index = i

        if arm == "ablation":
            obstruction = transfer_obstruction_key(
                ledger,
                source_capability_id=source_id,
                destination_game="vc33",
                exact_scope=SCOPE,
            )
            del ledger.obstructions[obstruction]

    return {
        "arm": arm,
        "proposals": proposals,
        "upfront_blocked": upfront_blocked,
        "destination_verifier_calls": verifier_calls,
        "proposals_blocked_after_evidence": blocked,
        "future_verifier_calls_eliminated": proposals - verifier_calls,
        "first_refutation_index": first_refutation_index,
        "obstruction_count": sum(
            row.get("kind") == "exact_transfer_refutation"
            for row in ledger.obstructions.values()
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ft09-dir", required=True)
    p.add_argument("--v2-dir", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(Path(args.ft09_dir), Path(args.v2_dir))

    independent = run_arm(inputs, "independent")
    flash = run_arm(inputs, "flash")
    ablation = run_arm(inputs, "ablation")

    if independent["destination_verifier_calls"] != 8:
        raise AssertionError(independent)
    if flash["destination_verifier_calls"] != 1:
        raise AssertionError(flash)
    if flash["proposals_blocked_after_evidence"] != 7:
        raise AssertionError(flash)
    if flash["upfront_blocked"]:
        raise AssertionError("Flash gain was available upfront")
    if ablation["destination_verifier_calls"] != 8:
        raise AssertionError(ablation)

    evidence = {
        "schema": "qckn-flash-multigame-v2",
        "inputs": {
            "ft09_run": FT09_RUN,
            "ft09_artifact": FT09_ARTIFACT,
            "ft09_artifact_digest": FT09_ARTIFACT_DIGEST,
            "ft09_file_sha256": sha256(inputs["ft_path"]),
            "v2_run": V2_RUN,
            "v2_artifact": V2_ARTIFACT,
            "v2_artifact_digest": V2_ARTIFACT_DIGEST,
            "v2_file_sha256": sha256(inputs["v2_path"]),
        },
        "independent": independent,
        "flash": flash,
        "ablation": ablation,
        "delta": {
            "destination_verifier_calls_eliminated": (
                independent["destination_verifier_calls"]
                - flash["destination_verifier_calls"]
            ),
            "elimination_ratio": (
                1.0 - flash["destination_verifier_calls"]
                / independent["destination_verifier_calls"]
            ),
        },
        "claim_boundary": (
            "online reuse of one exact destination-refuted transfer fingerprint "
            "over pinned retained ARC3 evidence; measures repeated destination "
            "transfer-verification work only, not game-solving actions, hidden-game "
            "performance, or universal cross-domain transfer"
        ),
        "verdict": "PASS_ONLINE_REFUTATION_COMPOUNDING",
    }
    (out / "online-refutation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )
    print("QCKN_FLASH_MULTIGAME_V2=" + evidence["verdict"])
    print("ONLINE_REFUTATION=" + json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
