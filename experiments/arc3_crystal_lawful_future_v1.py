from __future__ import annotations
import argparse,json,hashlib
from collections import Counter,defaultdict
from pathlib import Path
from arc3_crystal_game_exclusive_v1 import features
from arc3_crystal_stateful_growth_v1 import raw_obs

def sid(x):
 return hashlib.blake2b(repr(x).encode(),digest_size=10).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--limit",type=int,default=1600000);ap.add_argument("--out",required=True);a=ap.parse_args()
 from datasets import load_dataset
 splits=("rollouts_novelty_gen","rollouts_positive","rollouts","hhazard");per=a.limit//4
 # Compile tunnels from consequence-refined chamber signatures. We use all separator coordinates
 # because the prior campaign established saturation of this supplied separator language.
 edges=defaultdict(lambda:defaultdict(Counter))
 chamber_support=Counter(); rows=0
 for split in splits:
  for row in load_dataset("fredericowieser/arc-agi-3-wm-traces",split=split,streaming=True).take(per):
   base,out=features(row); obs=raw_obs(row); game=str(row.get("game_id"))
   src=(base,obs); dst=(out,)
   action=(int(row.get("action_id",-1)), tuple(sorted((row.get("action_args") or {}).items())))
   S=sid(src);D=sid(dst); A=repr(action)
   edges[(S,A)][game][D]+=1; chamber_support[S]+=1; rows+=1
 promoted=[];rejected=[];unknown=[]; outgoing=defaultdict(set); incoming=defaultdict(set)
 for (S,A),bygame in edges.items():
  tests=wrong=covered=0; predicted=set()
  for hold in bygame:
   train=Counter()
   for g,c in bygame.items():
    if g!=hold:train.update(c)
   if len(train)!=1:continue
   D=next(iter(train));predicted.add(D);tests+=1;covered+=sum(bygame[hold].values());wrong+=sum(v for d,v in bygame[hold].items() if d!=D)
  support=sum(sum(c.values()) for c in bygame.values())
  rec={"src":S,"action":A,"games":len(bygame),"support":support,"tested_games":tests,"covered":covered,"wrong":wrong}
  if tests>=2 and covered>=3 and wrong==0 and len(predicted)==1:
   D=next(iter(predicted));rec["dst"]=D;promoted.append(rec);outgoing[S].add(D);incoming[D].add(S)
  elif wrong:rejected.append(rec)
  else:unknown.append(rec)
 # Viability/repair geometry: alternative qualified outgoing destinations from a chamber.
 route_counts=Counter(len(ds) for ds in outgoing.values())
 robust=[{"chamber":s,"alternatives":len(ds),"destinations":sorted(ds)} for s,ds in outgoing.items() if len(ds)>=2]
 robust.sort(key=lambda z:(-z["alternatives"],z["chamber"]))
 promoted.sort(key=lambda z:(-z["games"],-z["support"],z["src"]))
 out={"schema":"msi.arc3-crystal-lawful-future-v1","rows":rows,"source_chambers":len(chamber_support),
 "promoted_tunnels":len(promoted),"rejected_tunnels":len(rejected),"unknown_tunnels":len(unknown),
 "chambers_with_qualified_outgoing":len(outgoing),"alternative_route_histogram":dict(route_counts),
 "multi_route_chambers":len(robust),"top_tunnels":promoted[:2000],"top_multi_route":robust[:512],
 "boundary":"Public-trace lawful-future compilation. Tunnel promotion requires deterministic leave-one-game-out destination with zero wrong covered transitions. Multi-route counts are qualified alternative outgoing destinations, not yet a proof of complete repair cover on hidden games."}
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
 print(json.dumps({k:out[k] for k in ("rows","source_chambers","promoted_tunnels","rejected_tunnels","unknown_tunnels","chambers_with_qualified_outgoing","multi_route_chambers")},sort_keys=True))
if __name__=="__main__":main()
