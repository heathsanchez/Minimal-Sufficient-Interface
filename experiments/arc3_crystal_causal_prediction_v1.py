from __future__ import annotations
import json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
sys.path.insert(0,str(ROOT/"kaggle"/"src"))

import arc3_public_interface_genesis_g2 as historical
import arc3_public_direct_schema_g2 as ds
from metalogic_arc3.arc_prediction_compiler import CausalRolePredictor, RoleExample
from metalogic_arc3.crystal_laws import ArcCrystalLawBridge, Prediction, VerifiedLawStore

OUT=ROOT/"evidence"/"arc3-crystal-causal-prediction-v1"/"result.json"

def clip(v,lim=3):
    if v < -lim: return f"<-{lim}"
    if v > lim: return f">{lim}"
    return v

def component_meta(frame,probe):
    try:
        return tuple(ds.meta(frame,probe))
    except Exception:
        return ("NO_COMPONENT",)

def canonical_patch(frame,probe,radius):
    g=historical.grid(frame)
    raw=historical.patch(g,probe[0],probe[1],radius=radius)
    remap={}
    nxt=0
    out=[]
    for row in raw:
        rr=[]
        for value in row:
            if value not in remap:
                remap[value]=nxt; nxt+=1
            rr.append(remap[value])
        out.append(tuple(rr))
    return tuple(out)

def role_key(cand,probe,frame,scheme):
    r,c=probe
    cols=tuple(cand["cols"])
    row_role="H" if r==cand["hrow"] else ("V" if r==cand["vrow"] else "O")
    col_role=cols.index(c) if c in cols else "O"
    meta=component_meta(frame,probe)
    coarse=(meta,row_role,col_role)
    if scheme=="coarse": return coarse
    if scheme=="coarse_patch1": return coarse+(canonical_patch(frame,probe,1),)
    if scheme=="coarse_patch2": return coarse+(canonical_patch(frame,probe,2),)
    rel=coarse+(clip(r-cand["hrow"]),clip(r-cand["vrow"]),tuple(clip(c-x) for x in cols))
    if scheme=="rel": return rel
    gaps=tuple(b-a for a,b in zip(cols,cols[1:]))
    return rel+(clip(cand["vrow"]-cand["hrow"]),gaps)

def action_key(probe):
    r,c=probe
    return (6,c,r)

def evaluate_scheme(examples,scheme,train_ids,eval_ids):
    train=[x for x in examples if x["cid"] in train_ids]
    ev=[x for x in examples if x["cid"] in eval_ids]
    predictor=CausalRolePredictor.fit(RoleExample(str(x["cid"]),x["action"],x[scheme],x["outcome"]) for x in train)
    known=correct=wrong=0
    for x in ev:
        pred=predictor.predict(x[scheme])
        if pred is None: continue
        known+=1
        if pred==x["outcome"]: correct+=1
        else: wrong+=1
    return predictor,{"total":len(ev),"known":known,"correct":correct,"wrong":wrong,"coverage":known/len(ev) if ev else 0.0}

def main():
    candidates=historical.candidate_programs()
    assert len(candidates)==36
    e=historical.ds.env()
    base_frames={}
    base_grids=[]
    for cand in candidates:
        _start,frame=historical.replay(e,cand)
        base_frames[cand["candidate_id"]]=frame
        base_grids.append(historical.grid(frame))
    root_pool=historical.pool_from_grids(base_grids,historical.MAX_ROOT_PROBES,historical.KNOWN)
    all_ids=list(range(36))

    records=[historical.evaluate_probe(e,candidates,all_ids,probe) for probe in root_pool]
    truth={(d["candidate_id"],tuple(record["probe"])): historical.sig_key(d["signature"])
           for record in records for d in record["details"]}

    examples=[]
    for cand in candidates:
        cid=cand["candidate_id"]; frame=base_frames[cid]
        for probe in root_pool:
            row={"cid":cid,"action":action_key(probe),"outcome":truth[(cid,tuple(probe))]}
            for scheme in ("coarse","coarse_patch1","coarse_patch2","rel","rel_global"):
                row[scheme]=role_key(cand,tuple(probe),frame,scheme)
            examples.append(row)

    train_ids={i for i in all_ids if i%3==0}
    val_ids={i for i in all_ids if i%3==1}
    holdout_ids={i for i in all_ids if i%3==2}

    validation={}
    predictors={}
    for scheme in ("coarse","coarse_patch1","coarse_patch2","rel","rel_global"):
        predictor,stats=evaluate_scheme(examples,scheme,train_ids,val_ids)
        predictors[scheme]=predictor; validation[scheme]=stats

    safe=[s for s in validation if validation[s]["wrong"]==0]
    if not safe:
        chosen=max(validation,key=lambda s:(-validation[s]["wrong"],validation[s]["correct"],-len(s)))
    else:
        chosen=max(safe,key=lambda s:(validation[s]["correct"],-len(s)))
    predictor=predictors[chosen]
    _,holdout=evaluate_scheme(examples,chosen,train_ids,holdout_ids)

    # Hybrid table: calibration candidates are black-box known; for all others,
    # use compiled role predictions when warranted and black-box fallback only
    # for UNKNOWN. This measures exact probe-response calls avoided.
    predictions=[]
    fallback_calls=0
    compiled_calls=0
    for x in examples:
        if x["cid"] in train_ids:
            outcome=x["outcome"]; fallback_calls+=1
        else:
            pred=predictor.predict(x[chosen])
            if pred is None:
                outcome=x["outcome"]; fallback_calls+=1
            else:
                outcome=pred; compiled_calls+=1
        predictions.append(Prediction(str(x["cid"]),x["action"],outcome))

    bridge=ArcCrystalLawBridge(VerifiedLawStore.default())
    answer=bridge.choose_separator(
        hypotheses=tuple(str(i) for i in all_ids),
        actions=tuple(action_key(p) for p in root_pool),
        predictions=tuple(predictions),
        support_refs=("compiled:tn36:causal-role-v1",),
        live_supports=("compiled:tn36:causal-role-v1",),
    )
    truth_best=historical.best_probe(records)
    assert truth_best is not None
    truth_worst=truth_best["partition"]["largest_class"]

    chosen_probe=None
    hybrid_worst=None
    if answer.chosen_action is not None:
        _aid,c,r=answer.chosen_action
        chosen_probe=[r,c]
        rec=next(row for row in records if row["probe"]==chosen_probe)
        hybrid_worst=rec["partition"]["largest_class"]

    out={
      "schema":"msi.arc3-crystal-causal-prediction-v1",
      "status":"QUALIFIED_BOUNDED" if holdout["wrong"]==0 and hybrid_worst is not None and hybrid_worst<=truth_worst else "NOT_QUALIFIED",
      "public_game":"tn36-ef4dde99",
      "candidate_worlds":36,
      "probe_pool":len(root_pool),
      "full_black_box_probe_calls":len(examples),
      "train_candidate_count":len(train_ids),
      "validation_candidate_count":len(val_ids),
      "holdout_candidate_count":len(holdout_ids),
      "validation":validation,
      "chosen_scheme":chosen,
      "holdout":holdout,
      "hybrid":{
        "compiled_predictions":compiled_calls,
        "black_box_probe_calls":fallback_calls,
        "calls_saved":len(examples)-fallback_calls,
        "fraction_saved":(len(examples)-fallback_calls)/len(examples),
        "crystal_probe":chosen_probe,
        "crystal_probe_true_worst_case":hybrid_worst,
        "full_truth_historical_probe":truth_best["probe"],
        "full_truth_worst_case":truth_worst,
      },
      "boundary":"Feature schemes are chosen on train+validation only; holdout candidate IDs are untouched. coarse_patch schemes are not standalone visual predictors: the patch is used only as a refinement of an already causal coarse role, and colors are canonicalized by local first occurrence. Black-box truth is used only to score holdout and as explicit UNKNOWN fallback; no wrong compiled prediction is permitted for qualification."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    if out["status"]!="QUALIFIED_BOUNDED":
        raise SystemExit(1)

if __name__=="__main__": main()
