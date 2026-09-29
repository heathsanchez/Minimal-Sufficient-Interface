"""V5: isolate the sole remaining prospective no-op applicability collision.

For calibration-earned same<->changed conflicts only, compare small relational
support geometry features. Choose the smallest feature family with zero
calibration conflict; evaluate on disjoint traces. Other V4 roles are untouched.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from arc3_typed_local_refinement_v4 import board,base,effect,richtrace,learn

def app_features(g):
    h=len(g);w=len(g[0]) if h else 0;nz={(r,c) for r,row in enumerate(g) for c,v in enumerate(row) if str(v) not in ("0","0.0")}
    if not nz:return (0,0,0,0,0,0)
    rs=[r for r,c in nz];cs=[c for r,c in nz]
    top=min(rs);bot=h-1-max(rs);left=min(cs);right=w-1-max(cs)
    # Support contact and local crowding are relational, color-invariant.
    horiz=sum((r,c+1) in nz for r,c in nz);vert=sum((r+1,c) in nz for r,c in nz)
    return (min(top,7),min(bot,7),min(left,7),min(right,7),
            min(horiz,15),min(vert,15))

def retrace(p):
    old=richtrace(p);z=[];prev=None;i=0
    for line in p.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            n=str(x.get("action_name",""))
            if n=="RESET":prev=now;continue
            if n.startswith("ACTION"):
                aid=int(n.replace("ACTION",""))
                if prev is not None and aid!=6:
                    row=old[i];i+=1
                    z.append(row+(row[1]+app_features(prev),))
        prev=now
    return z

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):games[p.name.split("_p",1)[0]].append(retrace(p))
    folds=[];K=W=N=0
    for game,trs in sorted(games.items()):
        cal=[tr for i,tr in enumerate(trs) if i%2==0];ev=[tr for i,tr in enumerate(trs) if i%2==1]
        for target in sorted({r[0] for tr in trs for r in tr if r[0]>0}):
            coarse=learn(cal,target,1,4); effect_bad=set(); noop_bad=set()
            for tr in cal:
                for row in tr:
                    lev,c,f,state,y,e,app=row
                    if lev!=target or c not in coarse or coarse[c]==y:continue
                    (noop_bad if y[0]=="same" or coarse[c][0]=="same" else effect_bad).add(c)
            me=learn(cal,target,2,5)
            ma=learn(cal,target,6,4)
            k=w=n=0
            for tr in ev:
                for lev,c,f,state,y,e,app in tr:
                    if lev!=target:continue
                    n+=1
                    if c in effect_bad:pred=me.get(f);actual=e
                    elif c in noop_bad:pred=ma.get(app);actual=y
                    else:pred=coarse.get(c);actual=y
                    if pred is not None:k+=1;w+=pred!=actual
            if n:folds.append(dict(game=game,target_level=target,cells=n,known=k,wrong=w,coverage=k/n,effect_refined=len(effect_bad),applicability_refined=len(noop_bad)));K+=k;W+=w;N+=n
    out=dict(schema="msi.arc3-relational-applicability-v5",heldout_cells=N,predicted_cells=K,wrong_predictions=W,coverage=K/N if N else 0,folds=folds,status="ZERO_ERROR_CANDIDATE" if K and W==0 else "REJECTED",boundary="Disjoint calibration/evaluation. V4 effect refinement retained. Only calibration-earned no-op conflicts receive color-invariant support-to-border and support-adjacency applicability coordinates.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
