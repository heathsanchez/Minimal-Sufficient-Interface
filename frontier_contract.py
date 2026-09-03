"""Validate the authoritative programme frontier and latest verified transition."""
from __future__ import annotations
import json
from pathlib import Path

ALLOWED_STATUS={"PROMOTE","PARK","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT"}
REQUIRED_PROMOTION={"VERIFIED","ATTACHED","SCOPE_CORRECT","EQUALITY_COMPLETE","CAUSAL"}


def main():
    x=json.loads(Path("program_frontier.json").read_text())
    assert x["authoritative"] is True and x["schema_version"]>=4
    assert set(x["promotion_contract"])==REQUIRED_PROMOTION
    assert x["live_residual"]["type"] in {"DERIVATION","ATTACHMENT","REPRESENTATION","VERIFICATION","PROCESS","INFRA"}
    assert x["live_residual"]["text"].strip()
    assert len(x["live_state_parent_sha"])==40
    for field in ("promoted","parked"):
        for item in x[field]:
            assert item.get("id") and item["status"] in ALLOWED_STATUS

    expected={18:(294,None,None,None),22:(882,126,17766,0),24:(1470,210,29610,0),26:(1764,252,35532,0)}
    kp={int(v["kappa"]):v for v in x["promoted"] if "kappa" in v}
    assert set(kp)==set(expected)
    for k,(lab,norm,pairs,surv) in expected.items():
        v=kp[k]; assert v["labelled_maps"]==lab
        if norm is not None:
            assert (v["normalized_maps"],v["normalized_D_phase_pairs"],v["survivors"])==(norm,pairs,surv)
            assert "four-row" in v["scope"] and "does not prove E677 -> E255" in v["scope"]
    assert (kp[26]["run_id"],kp[26]["job_id"],kp[26]["artifact_id"])==(33729041404,100564542120,9883140162)
    assert x["curvature_spectrum"]=={"18":294,"22":882,"24":1470,"26":1764,"30":588}
    assert "kappa=30" in x["live_residual"]["text"]
    assert x["last_transition"]["result_id"]=="kappa26_excluded" and x["last_transition"]["classification"]=="PROMOTE"
    assert any("repository frontier" in s.lower() for s in x["process_laws"])
    assert any("unchanged generic experiment" in s.lower() for s in x["process_laws"])
    print("PROGRAM_FRONTIER_VERIFIED")
    print("PROMOTED_KAPPAS="+",".join(map(str,sorted(kp))))
    print("LIVE_RESIDUAL="+x["live_residual"]["text"])

if __name__=="__main__": main()
