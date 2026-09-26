from __future__ import annotations
from collections import Counter
import json, os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
sys.path.insert(0,str(ROOT/"kaggle"/"src"))
import arc3_public_interface_genesis_g2 as hist
from metalogic_arc3.arc_prediction_compiler import CausalRolePredictor, RoleExample
from metalogic_arc3.crystal_laws import ArcCrystalLawBridge, Prediction, VerifiedLawStore

OUT=ROOT/"evidence"/"arc3-crystal-tn36-causal-role-predictor-v1"/"result.json"

def akey(probe): r,c=probe; return (6,c,r)

def role(cand,probe):
    r,c=probe
    hrow=int(cand["hrow"]); vrow=int(cand["vrow"]); cols=tuple(int(x) for x in cand["cols"])
    return (
        "tn36-grid-role-v1",
        r-hrow,
        r-vrow,
        tuple(c-x for x in cols),
        r==hrow,
        r==vrow,
        c in cols,
    )

def main():
    candidates=hist.candidate_programs()
    assert len(candidates)==36
    e=hist.ds.env()
    base=[]
    for cand in candidates:
        _s,f=hist.replay(e,cand); base.append(hist.grid(f))
    pool=hist.pool_from_grids(base,hist.MAX_ROOT_PROBES,hist.KNOWN)
    assert len(pool)==72
    records=[hist.evaluate_probe(e,candidates,list(range(36)),p) for p in pool]
    oracle_calls=36*len(pool)

    train_ids={i for i in range(36) if i%2==0}
    test_ids=set(range(36))-train_ids
    examples=[]
    oracle={}
    for rec in records:
        p=tuple(rec["probe"])
        for d in rec["details"]:
            cid=int(d["candidate_id"]); outcome=hist.sig_key(d["signature"])
            oracle[(cid,p)]=outcome
            if cid in train_ids:
                examples.append(RoleExample(str(cid),akey(p),role(candidates[cid],p),outcome))
    predictor=CausalRolePredictor.fit(examples)

    predicted=[]; covered=0; correct=0; unknown=0
    for cid in sorted(test_ids):
        for p in pool:
            pred=predictor.predict(role(candidates[cid],p))
            if pred is None:
                unknown+=1; continue
            covered+=1
            correct += int(pred==oracle[(cid,tuple(p))])
            predicted.append(Prediction(str(cid),akey(p),pred))

    total=len(test_ids)*len(pool)
    coverage=covered/total
    accuracy=(correct/covered) if covered else 0.0

    # Can the learned role model alone choose a separator over the held-out
    # candidate worlds? Only ask Crystal when the prediction table is complete.
    bridge=ArcCrystalLawBridge(VerifiedLawStore.default())
    if coverage==1.0:
        answer=bridge.choose_separator(
            hypotheses=tuple(str(i) for i in sorted(test_ids)),
            actions=tuple(akey(p) for p in pool),
            predictions=tuple(predicted),
            support_refs=("tn36:role-predictor-v1:train-even",),
            live_supports=("tn36:role-predictor-v1:train-even",),
        )
        chosen=list((answer.chosen_action[2],answer.chosen_action[1])) if answer.chosen_action else None
        status=answer.status.value
        worst=answer.worst_case_survivors
    else:
        chosen=None; status="UNKNOWN"; worst=None

    role_counts=Counter(role(candidates[cid],p) for cid in train_ids for p in pool)
    out={
      "schema":"msi.arc3-crystal-tn36-causal-role-predictor-v1",
      "status":"DIAGNOSTIC",
      "public_game":"tn36-ef4dde99",
      "candidate_worlds":36,
      "root_probe_pool":len(pool),
      "oracle_candidate_probe_calls":oracle_calls,
      "train_candidates":len(train_ids),
      "heldout_candidates":len(test_ids),
      "role_representation":"relative intervention coordinates to candidate hrow/vrow/selected columns",
      "train_role_count":len(role_counts),
      "conflicted_train_roles":len(predictor.conflicted_roles),
      "heldout_cells":total,
      "covered_cells":covered,
      "unknown_cells":unknown,
      "coverage":coverage,
      "exact_accuracy_on_covered":accuracy,
      "crystal_from_predicted_table":{"status":status,"chosen_probe":chosen,"worst_case_survivors":worst},
      "boundary":"Diagnostic only. Full oracle table is generated to score held-out predictions; no claim of online call savings is made unless a later gate freezes a calibrated predictor before held-out action choice."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__": main()
