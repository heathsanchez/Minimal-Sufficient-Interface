from __future__ import annotations
import json, os, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
sys.path.insert(0,str(ROOT/"kaggle"/"src"))
import arc3_public_interface_genesis_g2 as historical
from metalogic_arc3.crystal_laws import ArcCrystalLawBridge, Prediction, VerifiedLawStore
from metalogic_arc3.arc_prediction_compiler import CausalRolePredictor, RoleExample

OUT=ROOT/"evidence"/"arc3-crystal-role-prediction-v1"/"result.json"

def action_key(probe):
    r,c=probe; return (6,c,r)

def role(cand, probe):
    r,c=probe
    hrow=int(cand["hrow"]); vrow=int(cand["vrow"]); cols=tuple(int(x) for x in cand["cols"])
    # Relational, not candidate identity: position of the intervention relative
    # to the hypothesized horizontal/vertical operator grid.
    if r==hrow and c in cols: cell=("H_SELECTED", cols.index(c))
    elif r==vrow and c in cols: cell=("V_SELECTED", cols.index(c))
    elif r==hrow: cell=("H_ROW", "IN_COLSET" if c in cols else "OUT")
    elif r==vrow: cell=("V_ROW", "IN_COLSET" if c in cols else "OUT")
    elif c in cols: cell=("SELECTED_COL", cols.index(c))
    else: cell=("OTHER",)
    # Preserve signed offsets to the two candidate rows and nearest selected
    # column. These are representation-relative coordinates, not candidate IDs.
    nearest=min((abs(c-x), c-x) for x in cols)
    return tuple(cell)+(r-hrow,r-vrow,nearest[0],nearest[1])

def sig(record_detail):
    return historical.sig_key(record_detail["signature"])

def main():
    candidates=historical.candidate_programs()
    assert len(candidates)==36
    e=historical.ds.env()
    base_grids=[historical.grid(historical.replay(e,c)[1]) for c in candidates]
    pool=historical.pool_from_grids(base_grids,historical.MAX_ROOT_PROBES,historical.KNOWN)
    records=[historical.evaluate_probe(e,candidates,list(range(36)),p) for p in pool]
    truth={}
    for rec in records:
        p=tuple(rec["probe"])
        for d in rec["details"]:
            truth[(int(d["candidate_id"]),p)]=sig(d)

    # Calibrate by role, using the first deterministic example for each role.
    # If a role is observed with conflicting outcomes, the conservative
    # predictor marks it UNKNOWN.
    examples=[]
    seen_roles=set()
    calibration_pairs=set()
    for p in pool:
        for cid,cand in enumerate(candidates):
            rr=role(cand,p)
            if rr in seen_roles: continue
            seen_roles.add(rr)
            examples.append(RoleExample(str(cid),action_key(p),rr,truth[(cid,p)]))
            calibration_pairs.add((cid,p))
    predictor=CausalRolePredictor.fit(examples)

    predicted={}
    exact=0; unknown=0; wrong=0
    for p in pool:
        for cid,cand in enumerate(candidates):
            guess=predictor.predict(role(cand,p))
            if guess is None:
                unknown+=1
            else:
                predicted[(cid,p)]=guess
                if guess==truth[(cid,p)]: exact+=1
                else: wrong+=1

    # A prediction table is admissible for separator choice only when every
    # candidate has a prediction for that probe. Wrong predictions are fatal.
    admissible=[]
    bridge=ArcCrystalLawBridge(VerifiedLawStore.default())
    for p in pool:
        rows=[]
        ok=True
        for cid,cand in enumerate(candidates):
            guess=predicted.get((cid,p))
            if guess is None or guess!=truth[(cid,p)]:
                ok=False; break
            rows.append(Prediction(str(cid),action_key(p),guess))
        if ok: admissible.append((p,rows))

    crystal=None
    if admissible:
        answer=bridge.choose_separator(
            hypotheses=tuple(str(i) for i in range(36)),
            actions=tuple(action_key(p) for p,_ in admissible),
            predictions=tuple(row for _p,rows in admissible for row in rows),
            support_refs=("role-predictor:tn36:v1",),
            live_supports=("role-predictor:tn36:v1",),
        )
        if answer.chosen_action is not None:
            _aid,c,r=answer.chosen_action
            crystal=(r,c,answer.worst_case_survivors)

    total=len(pool)*len(candidates)
    out={
      "schema":"msi.arc3-crystal-role-prediction-v1",
      "status":"MEASURED",
      "public_game":"tn36-ef4dde99",
      "candidate_worlds":36,
      "probe_pool":len(pool),
      "total_candidate_probe_pairs":total,
      "calibration_pairs":len(calibration_pairs),
      "calibration_fraction":len(calibration_pairs)/total,
      "exact_predictions":exact,
      "unknown_predictions":unknown,
      "wrong_predictions":wrong,
      "exact_fraction":exact/total,
      "admissible_complete_probes":len(admissible),
      "crystal_separator":crystal,
      "historical_root":[32,37,27],
      "boundary":"Exploratory compression measurement. Promote only if wrong_predictions=0 and a complete predicted probe yields a minimax-equivalent separator with materially fewer calibration pairs than exhaustive replay."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__": main()
