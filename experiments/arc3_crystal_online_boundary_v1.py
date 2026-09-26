from __future__ import annotations
import json, os, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
sys.path.insert(0,str(ROOT/"kaggle"/"src"))
import arc3_public_interface_genesis_g2 as historical
from metalogic_arc3.crystal_laws import ArcCrystalLawBridge, Prediction, VerifiedLawStore
from metalogic_arc3.arc_prediction_compiler import CausalRolePredictor, RoleExample

OUT=ROOT/"evidence"/"arc3-crystal-online-boundary-v1"/"result.json"
TARGET=27

def action_key(probe):
    r,c=probe; return (6,c,r)

def role(cand, probe):
    r,c=probe
    hrow=int(cand["hrow"]); vrow=int(cand["vrow"]); cols=tuple(int(x) for x in cand["cols"])
    if r==hrow and c in cols: cell=("H_SELECTED",cols.index(c))
    elif r==vrow and c in cols: cell=("V_SELECTED",cols.index(c))
    elif r==hrow: cell=("H_ROW","IN_COLSET" if c in cols else "OUT")
    elif r==vrow: cell=("V_ROW","IN_COLSET" if c in cols else "OUT")
    elif c in cols: cell=("SELECTED_COL",cols.index(c))
    else: cell=("OTHER",)
    nearest=min((abs(c-x),c-x) for x in cols)
    return tuple(cell)+(r-hrow,r-vrow,nearest[0],nearest[1])

def observe(e,candidates,cid,p):
    rec=historical.evaluate_probe(e,candidates,[cid],p)
    return historical.sig_key(rec["details"][0]["signature"])

def main():
    candidates=historical.candidate_programs(); assert len(candidates)==36
    e=historical.ds.env()
    # Pool construction uses current observable candidate boards, not hypothetical probe outcomes.
    base_grids=[historical.grid(historical.replay(e,c)[1]) for c in candidates]
    pool=historical.pool_from_grids(base_grids,historical.MAX_ROOT_PROBES,historical.KNOWN)

    # DECISION PHASE. Acquire one real response for each distinct relational role.
    # No unobserved candidate×probe outcome exists in memory at this point.
    examples=[]; seen=set(); calibration={}
    for p in pool:
        for cid,cand in enumerate(candidates):
            rr=role(cand,p)
            if rr in seen: continue
            outcome=observe(e,candidates,cid,p)
            seen.add(rr); calibration[(cid,p)]=outcome
            examples.append(RoleExample(str(cid),action_key(p),rr,outcome))
    predictor=CausalRolePredictor.fit(examples)

    # Predict consequences without consulting audit truth. Unknown worlds are charged
    # adversarially to the largest known bucket: U(a)=b_max+m.
    candidates_by_probe={}
    for p in pool:
        rows=[]; counts=Counter(); unresolved=0
        for cid,cand in enumerate(candidates):
            guess=predictor.predict(role(cand,p))
            if guess is None: unresolved+=1
            else:
                rows.append(Prediction(str(cid),action_key(p),guess)); counts[guess]+=1
        bmax=max(counts.values(),default=0)
        upper=bmax+unresolved
        candidates_by_probe[p]=(upper,unresolved,rows)

    certified=[(p,*v) for p,v in candidates_by_probe.items() if v[0] <= TARGET]
    certified.sort(key=lambda x:(x[1],x[2],x[0][0],x[0][1]))
    chosen=None
    if certified:
        p,upper,unresolved,rows=certified[0]
        chosen={"probe":list(p),"certified_upper_bound":upper,"unresolved_worlds":unresolved}

    # Freeze the decision before any audit truth is acquired.
    frozen=json.dumps(chosen,sort_keys=True)

    # AUDIT PHASE. Now reveal the complete table. These calls cannot affect the choice.
    truth={}; wrong=0; unknown=0
    for p in pool:
        for cid,cand in enumerate(candidates):
            actual=calibration.get((cid,p))
            if actual is None:
                actual=observe(e,candidates,cid,p)
            truth[(cid,p)]=actual
            guess=predictor.predict(role(cand,p))
            if guess is None: unknown+=1
            elif guess != actual: wrong+=1

    assert frozen == json.dumps(chosen,sort_keys=True)
    actual_worst=None
    if chosen is not None:
        p=tuple(chosen["probe"])
        actual_worst=max(Counter(truth[(cid,p)] for cid in range(36)).values())

    decision_calls=len(calibration)
    total=len(pool)*len(candidates)
    out={
      "schema":"msi.arc3-crystal-online-boundary-v1",
      "status":"PASS" if chosen and wrong==0 and actual_worst is not None and actual_worst<=TARGET else "FAIL",
      "public_game":"tn36-ef4dde99",
      "candidate_worlds":36,"probe_pool":len(pool),
      "total_candidate_probe_pairs":total,
      "decision_phase_real_environment_calls":decision_calls,
      "decision_call_fraction_of_exhaustive":decision_calls/total,
      "decision_call_reduction_factor":total/decision_calls,
      "audit_only_environment_calls":total-decision_calls,
      "distinct_calibrated_roles":len(seen),
      "conflicted_roles":len(predictor.conflicted_roles),
      "chosen_before_audit":chosen,
      "chosen_actual_worst_case_after_audit":actual_worst,
      "wrong_predictions_after_audit":wrong,
      "unknown_predictions_after_audit":unknown,
      "historical_root":[32,37,27],
      "authority_boundary":"Decision is frozen before audit truth exists. Decision-time authority consists only of real calibration observations plus deterministic role transfer. Unknown predictions are adversarially charged to the largest known response bucket. Audit replays occur only after the choice is frozen."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    if out["status"]!="PASS": raise SystemExit(1)

if __name__=="__main__": main()
