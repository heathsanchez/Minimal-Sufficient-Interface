from __future__ import annotations
import argparse,json,hashlib
from collections import Counter,defaultdict
from pathlib import Path

def freeze(g):
 if not g:return ()
 return tuple(tuple(tuple(int(v) for v in row) for row in layer) for layer in g)
def sig(grid):
 return hashlib.blake2b(json.dumps(grid,separators=(",",":")).encode(),digest_size=8).hexdigest()
def features(row):
 a=freeze(row.get("state")); b=freeze(row.get("next_state")); x=a[-1] if a else (); y=b[-1] if b else ()
 h=len(x); w=len(x[0]) if h else 0; args=row.get("action_args") or {}; px=int(args.get("x",-1) or -1); py=int(args.get("y",-1) or -1)
 ch=[]
 if len(y)==h and (not h or len(y[0])==w):
  for r in range(h):
   for c in range(w):
    if x[r][c]!=y[r][c]:ch.append((r,c))
 bbox=None if not ch else (min(r for r,c in ch),min(c for r,c in ch),max(r for r,c in ch),max(c for r,c in ch))
 # deliberately discard literal game/color identity; retain relational intervention geometry.
 role=(int(row.get("action_id",-1)),h,w,-1 if px<0 else min(7,8*px//max(1,w)),-1 if py<0 else min(7,8*py//max(1,h)),
       int(row.get("level_id",0))==1)
 outcome=("done" if row.get("level_done") else "live",len(ch),bbox)
 return role,outcome

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--limit",type=int,default=400000);ap.add_argument("--out",required=True);a=ap.parse_args()
 from datasets import load_dataset
 splits=("rollouts_novelty_gen","rollouts_positive","rollouts","hhazard"); per=a.limit//4
 evidence=defaultdict(lambda:defaultdict(lambda:defaultdict(int))); n=0
 for split in splits:
  for row in load_dataset("fredericowieser/arc-agi-3-wm-traces",split=split,streaming=True).take(per):
   r,o=features(row); g=str(row.get("game_id")); evidence[repr(r)][g][repr(o)]+=1;n+=1
 promoted=[]; rejected=[]; unknown=[]
 for r,bygame in evidence.items():
  games=sorted(bygame)
  # Leave-one-game-out: each game may only be predicted by OTHER games.
  tests=0;wrong=0;covered=0
  for hold in games:
   train=Counter()
   for g in games:
    if g!=hold: train.update(bygame[g])
   if not train:continue
   if len(train)!=1:continue
   pred=next(iter(train)); covered+=sum(bygame[hold].values()); tests+=1
   wrong+=sum(v for o,v in bygame[hold].items() if o!=pred)
  support=sum(sum(c.values()) for c in bygame.values())
  rec={"role":r,"games":len(games),"support":support,"holdout_games_tested":tests,"covered":covered,"wrong":wrong}
  if tests>=2 and covered>=3 and wrong==0:promoted.append(rec)
  elif wrong>0:rejected.append(rec)
  else:unknown.append(rec)
 promoted.sort(key=lambda z:(-z["games"],-z["support"],z["role"]));rejected.sort(key=lambda z:(-z["wrong"],-z["support"]))
 out={"schema":"msi.arc3-crystal-game-exclusive-v1","rows":n,"roles":len(evidence),"promoted_zero_wrong":len(promoted),
      "rejected_transfer":len(rejected),"unknown":len(unknown),"top_promoted":promoted[:512],"top_rejected":rejected[:128],
      "boundary":"Promotion requires leave-one-game-out deterministic consequence from other games, at least two held-out games tested, and zero wrong covered transitions. This is bounded public-trace transfer evidence, not hidden-game authority."}
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
 print(json.dumps({k:out[k] for k in ("rows","roles","promoted_zero_wrong","rejected_transfer","unknown")},sort_keys=True))
if __name__=="__main__":main()
