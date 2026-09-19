#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

RUN=35404864326
ARTIFACT=10571982632
ARTIFACT_DIGEST="sha256:a0cd3c2088931f1411684156a3d83f55c0533e85e8a9d38f3bf301bc3cadd058"
AUTHORITY="arc3-vc33-pinned-v2"
VERIFIER="destination-exact-v1"

def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"))
def _sha(s): return hashlib.sha256(s.encode()).hexdigest()
def build_event(*,source_commit):
    if len(source_commit)!=40 or any(c not in "0123456789abcdef" for c in source_commit): raise ValueError("source commit must be full SHA")
    evidence={"schema":"arc3-online-refutation-evidence-v1","run":RUN,"artifact":ARTIFACT,"artifact_digest":ARTIFACT_DIGEST,
      "online_refutation":{"verifier_calls_before":8,"verifier_calls_after":1,"eliminated":7,"elimination_ratio":0.875,"upfront_blocked":False,"ablation_calls":8},
      "claim_boundary":"exact ft09->vc33 transfer fingerprint only"}
    candidate={"source":"ft09:bounded-fatal-5454-family","destination":"vc33","scope":{"intervention_language":"complex_action6","claim":"generic fatal-family transfer"}}
    fp=_sha(canonical(candidate))
    obs={"obstruction_id":"arc3:ft09-vc33-transfer-refutation:v2","input_type":"arc3-cross-game-transfer","output_type":"destination-transfer-validity",
         "contract":{"authority_snapshot":AUTHORITY,"verifier_id":VERIFIER},"candidate_fingerprint":fp,
         "separating_input":"ft09:bounded-fatal-5454-family->vc33","expected_output":"verified-transfer","actual_output":"refuted-transfer",
         "provenance":f"run:{RUN}/artifact:{ARTIFACT}"}
    payload={"obstruction":obs}; et=canonical(evidence)
    event={"schema":"qckn-flash-external-event-v1","event_id":obs["obstruction_id"],"event_kind":"obstruction_admission",
      "repository":"heathsanchez/Minimal-Sufficient-Interface","commit":source_commit,"authority_snapshot":AUTHORITY,"verifier_id":VERIFIER,
      "source_evidence_sha256":_sha(et),"payload":payload,"payload_sha256":_sha(canonical(payload))}
    return evidence,event
def main():
    p=argparse.ArgumentParser();p.add_argument("--commit",required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    e,v=build_event(source_commit=a.commit);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"evidence.json").write_text(canonical(e));(a.out/"event.json").write_text(canonical(v))
    print("QCKN_FLASH_EVENT="+v["event_id"])
if __name__=="__main__": main()
