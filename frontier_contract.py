"""Validate the authoritative programme frontier and its latest transition."""
from __future__ import annotations

import json
from pathlib import Path

ALLOWED_STATUS={"PROMOTE","PARK","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT"}
REQUIRED_PROMOTION={"VERIFIED","ATTACHED","SCOPE_CORRECT","EQUALITY_COMPLETE","CAUSAL"}


def main() -> None:
    x=json.loads(Path("program_frontier.json").read_text())
    assert x["authoritative"] is True
    assert x["schema_version"] >= 3
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

    expected={
      18:(294,None,None,None),
      22:(882,126,17766,0),
      24:(1470,210,29610,0),
    }
    promoted_kappas={}
    for v in x["promoted"]:
        if "kappa" in v:
            promoted_kappas[int(v["kappa"])]=v
    assert set(promoted_kappas)==set(expected)
    for k,(labelled,norm,pairs,survivors) in expected.items():
        v=promoted_kappas[k]
        assert v["labelled_maps"]==labelled
        if norm is not None:
            assert v["normalized_maps"]==norm
            assert v["normalized_D_phase_pairs"]==pairs
            assert v["survivors"]==survivors
            assert "four-row" in v["scope"] and "does not prove E677 -> E255" in v["scope"]

    k24=promoted_kappas[24]
    assert (k24["run_id"],k24["job_id"],k24["artifact_id"])==(33728674193,100563396140,9882992540)

    assert x["curvature_spectrum"]=={"18":294,"22":882,"24":1470,"26":1764,"30":588}
    assert "kappa=26" in x["live_residual"]["text"]
    assert x["last_transition"]["classification"]=="PROMOTE"
    assert x["last_transition"]["result_id"]=="kappa24_excluded"
    assert x["last_transition"]["run_id"]==33728674193

    assert any("equality completion" in s.lower() for s in x["negative_laws"])
    assert any("repository frontier" in s.lower() for s in x["process_laws"])
    assert any("smallest unclosed" in s.lower() for s in x["process_laws"])

    print("PROGRAM_FRONTIER_VERIFIED")
    print("PROMOTED_KAPPAS="+",".join(map(str,sorted(promoted_kappas))))
    print("LIVE_RESIDUAL_TYPE="+x["live_residual"]["type"])
    print("LIVE_RESIDUAL="+x["live_residual"]["text"])

if __name__=="__main__":
    main()
