"""Validate the authoritative programme frontier and its latest transition."""
from __future__ import annotations

import json
from pathlib import Path

ALLOWED_STATUS={"PROMOTE","PARK","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT"}
REQUIRED_PROMOTION={"VERIFIED","ATTACHED","SCOPE_CORRECT","EQUALITY_COMPLETE","CAUSAL"}


def main() -> None:
    x=json.loads(Path("program_frontier.json").read_text())
    assert x["authoritative"] is True
    assert x["schema_version"] >= 2
    assert x["target"].strip()
    assert set(x["promotion_contract"])==REQUIRED_PROMOTION
    assert x["live_state_parent_sha"] and len(x["live_state_parent_sha"])==40
    assert isinstance(x["live_residual"],dict) and x["live_residual"]["text"].strip()
    assert x["live_residual"]["type"] in {"DERIVATION","ATTACHMENT","REPRESENTATION","VERIFICATION","PROCESS","INFRA"}

    for field in ("promoted","parked"):
        assert isinstance(x[field],list)
        for item in x[field]:
            assert item.get("id") and item["status"] in ALLOWED_STATUS

    t6=next(v for v in x["promoted"] if v["id"]=="t6_four_row_annihilation")
    assert (t6["run_id"],t6["job_id"],t6["baseline"],t6["survivors"])==(33725970762,100554886606,141,0)
    assert "four-row" in t6["scope"]

    k18=next(v for v in x["promoted"] if v["id"]=="kappa18_excluded")
    assert k18["kappa"]==18 and k18["labelled_maps"]==294
    assert "does not prove E677 -> E255" in k18["scope"]

    k22=next(v for v in x["promoted"] if v["id"]=="kappa22_excluded")
    assert k22["kappa"]==22
    assert k22["labelled_maps"]==882 and k22["normalized_maps"]==126
    assert k22["normalized_D_phase_pairs"]==17766 and k22["survivors"]==0
    assert (k22["run_id"],k22["job_id"],k22["artifact_id"])==(33728222563,100561993523,9882811488)
    assert "four-row" in k22["scope"] and "does not prove E677 -> E255" in k22["scope"]

    assert x["curvature_spectrum"]=={"18":294,"22":882,"24":1470,"26":1764,"30":588}
    assert "kappa=24" in x["live_residual"]["text"]
    assert x["last_transition"]["classification"]=="PROMOTE"
    assert x["last_transition"]["result_id"]=="kappa22_excluded"
    assert x["last_transition"]["run_id"]==33728222563

    assert any("equality completion" in s.lower() for s in x["negative_laws"])
    assert any("repository frontier" in s.lower() for s in x["process_laws"])
    assert any("emit one explicit proposed transition" in s.lower() for s in x["process_laws"])

    print("PROGRAM_FRONTIER_VERIFIED")
    print("PROMOTED_KAPPAS="+",".join(str(v["kappa"]) for v in x["promoted"] if "kappa" in v))
    print("LIVE_RESIDUAL_TYPE="+x["live_residual"]["type"])
    print("LIVE_RESIDUAL="+x["live_residual"]["text"])

if __name__=="__main__":
    main()
