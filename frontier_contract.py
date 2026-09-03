"""Validate the authoritative programme frontier.

This is deliberately small. It does not decide mathematics; it prevents the
process from silently losing scope, evidence, residual uniqueness, or promotion
classification between conversations/branches.
"""
from __future__ import annotations

import json
from pathlib import Path

ALLOWED_STATUS={"PROMOTE","PARK","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT"}
REQUIRED_PROMOTION={"VERIFIED","ATTACHED","SCOPE_CORRECT","EQUALITY_COMPLETE","CAUSAL"}


def main() -> None:
    p=Path("program_frontier.json")
    assert p.exists(), "missing authoritative program_frontier.json"
    x=json.loads(p.read_text())
    assert x["authoritative"] is True
    assert x["target"].strip()
    assert set(x["promotion_contract"])==REQUIRED_PROMOTION
    assert isinstance(x["live_residual"],dict)
    assert x["live_residual"]["type"] in {"DERIVATION","ATTACHMENT","REPRESENTATION","VERIFICATION","PROCESS","INFRA"}
    assert x["live_residual"]["text"].strip()
    assert x["live_state_parent_sha"] and len(x["live_state_parent_sha"])==40

    items=[]
    for field in ("promoted","parked"):
        assert isinstance(x[field],list)
        items.extend(x[field])
    for item in items:
        assert item["status"] in ALLOWED_STATUS
        assert item.get("id")

    t6=next(v for v in x["promoted"] if v["id"]=="t6_four_row_annihilation")
    assert t6["run_id"]==33725970762
    assert t6["job_id"]==100554886606
    assert t6["baseline"]==141 and t6["survivors"]==0
    assert "four-row" in t6["scope"]

    k18=next(v for v in x["promoted"] if v["id"]=="kappa18_excluded")
    assert "does not prove E677 -> E255" in k18["scope"]

    assert any("equality completion" in s.lower() for s in x["negative_laws"])
    assert any("repository frontier" in s.lower() for s in x["process_laws"])

    print("PROGRAM_FRONTIER_VERIFIED")
    print("LIVE_RESIDUAL_TYPE="+x["live_residual"]["type"])
    print("LIVE_RESIDUAL="+x["live_residual"]["text"])

if __name__=="__main__":
    main()
