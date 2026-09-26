from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from arc3_crystal_game_exclusive_v1 import features

def raw_obs(row):
 g=row.get("state") or []; layer=g[-1] if g else []
 h=len(layer);w=len(layer[0]) if h else 0;a=row.get("action_args") or {};x=int(a.get("x",-1) or -1);y=int(a.get("y",-1) or -1)
 def cell(dy,dx):
  yy=y+dy;xx=x+dx
  return -1 if not(0<=yy<h and 0<=xx<w) else int(layer[yy][xx])
 patch=tuple(cell(dy,dx) for dy in (-1,0,1) for dx in (-1,0,1)) if x>=0 and y>=0 else ()
 # Candidate separator bank: local canonical patch, palette multiplicities, component-free row/col signatures,
 # previous/next action-independent visible geometry. Refinement chooses only coordinates that split futures.
 vals=Counter(v for r in layer for v in r)
 row_sig=tuple(layer[y]) if 0<=y<h else ()
 col_sig=tuple(layer[r][x] for r in range(h)) if 0<=x<w else ()
 return (patch,tuple(sorted(vals.items())),row_sig,col_sig)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--limit",type=int,default=1200000);ap.add_argument("--rounds",type=int,default=6);ap.add_argument("--out",required=True);a=ap.parse_args()
 from datasets import load_dataset
 splits=("rollouts_novelty_gen","rollouts_positive","rollouts","hhazard");per=a.limit//4
 rows=[]
 for split in splits:
  for row in load_dataset("fredericowieser/arc-agi-3-wm-traces",split=split,streaming=True).take(per):
   base,out=features(row); rows.append((str(row.get("game_id")),base,out,raw_obs(row)))
 # A representation is base role plus a subset of separator coordinates. Start coarse.
 active=defaultdict(tuple); history=[]
 for rnd in range(a.rounds):
  groups=defaultdict(list)
  for game,base,out,sep in rows:
   key=(base,)+tuple(sep[i] for i in active[base])
   groups[key].append((game,out,sep))
  promoted=rejected=unknown=0; conflict_bases=defaultdict(Counter)
  for key,items in groups.items():
   bygame=defaultdict(Counter)
   for g,o,s in items:bygame[g][repr(o)]+=1
   tests=wrong=covered=0
   for hold in bygame:
    train=Counter()
    for g,c in bygame.items():
     if g!=hold:train.update(c)
    if len(train)!=1:continue
    pred=next(iter(train));tests+=1;covered+=sum(bygame[hold].values());wrong+=sum(v for o,v in bygame[hold].items() if o!=pred)
   if tests>=2 and covered>=3 and wrong==0:promoted+=1
   elif wrong:rejected+=1
   else:unknown+=1
   if wrong or len({repr(o) for _,o,_ in items})>1:
    base=key[0]
    for idx in range(4):
     if idx in active[base]:continue
     buckets=defaultdict(set)
     for _,o,s in items:buckets[repr(s[idx])].add(repr(o))
     # score separators that reduce future collisions, not raw cardinality
     pure=sum(1 for v in buckets.values() if len(v)==1); conflict=sum(1 for v in buckets.values() if len(v)>1)
     conflict_bases[base][idx]+=pure-conflict
  history.append({"round":rnd,"representation_variants":len(groups),"promoted":promoted,"rejected":rejected,"unknown":unknown,
                  "refined_bases":sum(bool(v) for v in conflict_bases.values())})
  changed=0
  for base,scores in conflict_bases.items():
   if not scores:continue
   idx,score=max(scores.items(),key=lambda z:(z[1],-z[0]))
   if score>0 and idx not in active[base]:
    active[base]=tuple(active[base])+(idx,);changed+=1
  history[-1]["new_separators"]=changed
  if changed==0:break
 out={"schema":"msi.arc3-crystal-stateful-growth-v1","rows":len(rows),"rounds":history,
      "refined_base_roles":sum(bool(v) for v in active.values()),"separator_assignments":sum(len(v) for v in active.values()),
      "boundary":"Stateful multi-round representation refinement on public traces. Each round refines only consequence-conflicted roles; promotion counts are leave-one-game-out. This is candidate ARC Crystal growth, not hidden-game authority."}
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
