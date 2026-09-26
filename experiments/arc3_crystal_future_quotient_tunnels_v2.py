from __future__ import annotations
import argparse,json,hashlib
from collections import Counter,defaultdict
from pathlib import Path
from arc3_crystal_game_exclusive_v1 import features
from arc3_crystal_stateful_growth_v1 import raw_obs

def H(x):return hashlib.blake2b(repr(x).encode(),digest_size=10).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--limit",type=int,default=1600000);ap.add_argument("--out",required=True);a=ap.parse_args()
 from datasets import load_dataset
 splits=("rollouts_novelty_gen","rollouts_positive","rollouts","hhazard");per=a.limit//4
 rows=[]; residual=defaultdict(list)
 for split in splits:
  for row in load_dataset("fredericowieser/arc-agi-3-wm-traces",split=split,streaming=True).take(per):
   base,out=features(row); obs=raw_obs(row);g=str(row.get("game_id"));act=int(row.get("action_id",-1))
   rows.append((g,base,obs,act,out))
 # Start from coarse consequential source role. Refine only source classes whose same action
 # has incompatible protected futures; separator coordinates are inherited from wall campaign.
 active=defaultdict(tuple);hist=[]; final_prom=[]
 for rnd in range(5):
  groups=defaultdict(list)
  for g,b,o,a1,y in rows:
   key=(b,a1)+tuple(o[i] for i in active[(b,a1)])
   groups[key].append((g,y,o))
  promote=[]; conflicts=defaultdict(Counter); wrong_total=0
  for key,items in groups.items():
   by=defaultdict(Counter)
   for g,y,o in items:by[g][repr(y)]+=1
   tests=wrong=covered=0;preds=set()
   for hold in by:
    tr=Counter()
    for g,c in by.items():
     if g!=hold:tr.update(c)
    if len(tr)!=1:continue
    p=next(iter(tr));preds.add(p);tests+=1;covered+=sum(by[hold].values());wrong+=sum(v for y,v in by[hold].items() if y!=p)
   if tests>=2 and covered>=3 and wrong==0 and len(preds)==1:
    promote.append((key,next(iter(preds)),tests,covered,sum(sum(c.values()) for c in by.values())))
   else:
    wrong_total+=wrong
    if wrong or len({repr(y) for _,y,_ in items})>1:
     root=(key[0],key[1])
     for i in range(4):
      if i in active[root]:continue
      buck=defaultdict(set)
      for _,y,o in items:buck[repr(o[i])].add(repr(y))
      conflicts[root][i]+=sum(1 for z in buck.values() if len(z)==1)-sum(1 for z in buck.values() if len(z)>1)
  changed=0
  for root,sc in conflicts.items():
   if sc:
    i,v=max(sc.items(),key=lambda z:(z[1],-z[0]))
    if v>0:active[root]=tuple(active[root])+(i,);changed+=1
  hist.append({"round":rnd,"variants":len(groups),"promoted":len(promote),"wrong_holdout":wrong_total,"new_separators":changed})
  final_prom=promote
  if not changed:break
 # Build qualified tunnel graph from final promoted laws.
 outg=defaultdict(set)
 for key,dst,*_ in final_prom:outg[H(key)].add(H(dst))
 multi=sum(1 for ds in outg.values() if len(ds)>1)
 out={"schema":"msi.arc3-crystal-future-quotient-tunnels-v2","rows":len(rows),"rounds":hist,
      "promoted_tunnels":len(final_prom),"qualified_source_classes":len(outg),"multi_route_classes":multi,
      "separator_assignments":sum(len(x) for x in active.values()),
      "top_tunnels":[{"src":H(k),"dst":H(d),"tested_games":t,"covered":c,"support":s} for k,d,t,c,s in sorted(final_prom,key=lambda z:-z[4])[:3000]],
      "boundary":"Tunnel identity begins at coarse protected-future role and is refined only by earned observation separators. Final promotion is deterministic leave-one-game-out zero-wrong transfer."}
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps({k:out[k] for k in ("rows","promoted_tunnels","qualified_source_classes","multi_route_classes","separator_assignments","rounds")},sort_keys=True))
if __name__=="__main__":main()
