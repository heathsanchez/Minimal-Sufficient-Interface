from __future__ import annotations
import json, os, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments")); sys.path.insert(0,str(ROOT/"kaggle"/"src"))
import arc3_public_interface_genesis_g2 as historical
from metalogic_arc3.arc_prediction_compiler import CausalRolePredictor, RoleExample
OUT=ROOT/"evidence"/"arc3-crystal-adaptive-calibration-v1"/"result.json"; TARGET=27

def role(cand,p):
 r,c=p; hr=int(cand["hrow"]); vr=int(cand["vrow"]); cols=tuple(int(x) for x in cand["cols"])
 if r==hr and c in cols: cell=("H_SELECTED",cols.index(c))
 elif r==vr and c in cols: cell=("V_SELECTED",cols.index(c))
 elif r==hr: cell=("H_ROW","IN_COLSET" if c in cols else "OUT")
 elif r==vr: cell=("V_ROW","IN_COLSET" if c in cols else "OUT")
 elif c in cols: cell=("SELECTED_COL",cols.index(c))
 else: cell=("OTHER",)
 near=min((abs(c-x),c-x) for x in cols)
 return tuple(cell)+(r-hr,r-vr,near[0],near[1])

def observe(e,cs,cid,p):
 rec=historical.evaluate_probe(e,cs,[cid],p)
 return historical.sig_key(rec["details"][0]["signature"])

def bounds(predictor,cs,p):
 counts=Counter(); missing=[]
 for cid,c in enumerate(cs):
  g=predictor.predict(role(c,p))
  if g is None: missing.append(cid)
  else: counts[g]+=1
 b=max(counts.values(),default=0)
 return b+len(missing),len(missing),missing

def main():
 cs=historical.candidate_programs(); e=historical.ds.env()
 grids=[historical.grid(historical.replay(e,c)[1]) for c in cs]
 pool=historical.pool_from_grids(grids,historical.MAX_ROOT_PROBES,historical.KNOWN)
 examples=[]; observed={}; seen=set(); trace=[]
 # Greedy value-of-information: calibrate the unseen role that appears most often
 # among worlds of probes currently closest to certification. Recompute after each call.
 while True:
  pred=CausalRolePredictor.fit(examples)
  scored=[]
  for p in pool:
   upper,nmiss,missing=bounds(pred,cs,p); scored.append((upper,nmiss,p,missing))
  scored.sort(key=lambda x:(x[0],x[1],x[2][0],x[2][1]))
  best=scored[0]
  if best[0] <= TARGET:
   chosen={"probe":list(best[2]),"certified_upper_bound":best[0],"unresolved_worlds":best[1]}; break
  # Consider a small frontier of best probes, then buy the role covering most frontier cells.
  frontier=scored[:min(12,len(scored))]
  freq=Counter(); witness={}
  for _u,_m,p,missing in frontier:
   for cid in missing:
    rr=role(cs[cid],p); freq[rr]+=1; witness.setdefault(rr,(cid,p))
  if not freq: chosen=None; break
  rr,_=max(freq.items(),key=lambda kv:(kv[1],repr(kv[0])))
  cid,p=witness[rr]; y=observe(e,cs,cid,p)
  examples.append(RoleExample(str(cid),(6,p[1],p[0]),rr,y)); observed[(cid,p)]=y; seen.add(rr)
  if len(examples)>2592: raise RuntimeError("nontermination")
  if len(examples)%25==0: trace.append({"calls":len(examples),"best_upper":best[0],"best_unresolved":best[1]})
 frozen=json.dumps(chosen,sort_keys=True)
 # Blind audit only after frozen decision.
 truth={}; wrong=0
 for p in pool:
  for cid,c in enumerate(cs):
   y=observed.get((cid,p))
   if y is None: y=observe(e,cs,cid,p)
   truth[(cid,p)]=y
   g=pred.predict(role(c,p))
   if g is not None and g!=y: wrong+=1
 assert frozen==json.dumps(chosen,sort_keys=True)
 actual=None
 if chosen:
  p=tuple(chosen["probe"]); actual=max(Counter(truth[(cid,p)] for cid in range(36)).values())
 total=len(pool)*len(cs); calls=len(examples)
 out={"schema":"msi.arc3-crystal-adaptive-calibration-v1","status":"PASS" if chosen and wrong==0 and actual<=TARGET else "FAIL",
 "public_game":"tn36-ef4dde99","total_candidate_probe_pairs":total,"decision_phase_real_environment_calls":calls,
 "decision_call_fraction_of_exhaustive":calls/total,"decision_call_reduction_factor":total/calls,
 "chosen_before_audit":chosen,"chosen_actual_worst_case_after_audit":actual,"wrong_predictions_after_audit":wrong,
 "calibrated_roles":len(seen),"trace":trace,
 "boundary":"Greedy calibration sees only purchased real responses. Choice is frozen before exhaustive audit. Unpredicted worlds are adversarially assigned to the largest known bucket."}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps(out,sort_keys=True))
 if out["status"]!="PASS": raise SystemExit(1)
if __name__=="__main__": main()
