"""V4 typed local refinement for ARC next-level transfer.

Use richer effect semantics ONLY for calibration roles whose coarse consequence
is falsified by held-out calibration evidence. For no-op collisions, add a
small occupancy-location state separator. Selection and evaluation traces are
disjoint. This is diagnostic, not live policy authority.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from arc3_prospective_role_refinement_v3 import trace as oldtrace

def board(x):
    b=x.get("board",[])
    if b and isinstance(b[0],list) and b[0] and isinstance(b[0][0],list):b=b[0]
    return b
def loc(g):
    h=len(g);w=len(g[0]) if h else 0;nz=[(r,c) for r,row in enumerate(g) for c,v in enumerate(row) if str(v) not in ("0","0.0")]
    if not nz:return (0,0,0,0)
    mr=sum(r for r,c in nz)/len(nz);mc=sum(c for r,c in nz)/len(nz)
    return (int(mr<h/3),int(mr>=2*h/3),int(mc<w/3),int(mc>=2*w/3))
def effect(a,b):
    A={(r,c) for r,row in enumerate(a) for c,v in enumerate(row) if str(v) not in ("0","0.0")}
    B={(r,c) for r,row in enumerate(b) for c,v in enumerate(row) if str(v) not in ("0","0.0")}
    if A==B:return ("support_same",0,0,1)
    if not A or not B:return ("support_birthdeath",0,0,0)
    ar=sum(r for r,c in A)/len(A);ac=sum(c for r,c in A)/len(A);br=sum(r for r,c in B)/len(B);bc=sum(c for r,c in B)/len(B)
    dr=round(br-ar);dc=round(bc-ac);return ("support_changed",max(-3,min(3,dr)),max(-3,min(3,dc)),int({(r+dr,c+dc) for r,c in A}==B))
def richtrace(p):
    old=oldtrace(p); raw=[];prev=None;lev=0;i=0
    for line in p.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            n=str(x.get("action_name",""))
            if n=="RESET":prev=now;continue
            if n.startswith("ACTION"):
                aid=int(n.replace("ACTION",""))
                if prev is not None and aid!=6:
                    ol,coarse,fine,y=old[i];i+=1
                    raw.append((ol,coarse,fine,coarse+loc(prev),y,effect(prev,now)))
                if bool(x.get("level_completed")):lev+=1
        prev=now
    return raw
def learn(rows,target,keyix,outix):
    s=defaultdict(set)
    for tr in rows:
        for row in tr:
            if row[0]<target:s[row[keyix]].add(row[outix])
    return {k:next(iter(v)) for k,v in s.items() if len(v)==1}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):games[p.name.split("_p",1)[0]].append(richtrace(p))
    folds=[];K=W=N=0
    for game,trs in sorted(games.items()):
        cal=[tr for i,tr in enumerate(trs) if i%2==0];ev=[tr for i,tr in enumerate(trs) if i%2==1]
        for target in sorted({r[0] for tr in trs for r in tr if r[0]>0}):
            coarse=learn(cal,target,1,4)
            # Earn collision types from calibration target only.
            effect_bad=set();noop_bad=set()
            for tr in cal:
                for lev,c,f,state,y,e in tr:
                    if lev!=target or c not in coarse or coarse[c]==y:continue
                    if y[0]=="same" or coarse[c][0]=="same":noop_bad.add(c)
                    else:effect_bad.add(c)
            me=learn(cal,target,2,5); ms=learn(cal,target,3,4)
            k=w=n=0
            for tr in ev:
                for lev,c,f,state,y,e in tr:
                    if lev!=target:continue
                    n+=1
                    if c in effect_bad:
                        pred=me.get(f); actual=e
                    elif c in noop_bad:
                        pred=ms.get(state);actual=y
                    else:
                        pred=coarse.get(c);actual=y
                    if pred is not None:k+=1;w+=pred!=actual
            if n:folds.append(dict(game=game,target_level=target,cells=n,known=k,wrong=w,coverage=k/n,effect_refined=len(effect_bad),state_refined=len(noop_bad)));K+=k;W+=w;N+=n
    out=dict(schema="msi.arc3-typed-local-refinement-v4",heldout_cells=N,predicted_cells=K,wrong_predictions=W,coverage=K/N if N else 0,folds=folds,status="ZERO_ERROR_CANDIDATE" if K and W==0 else "REJECTED",boundary="Disjoint calibration/evaluation. Effect refinement only for calibration-earned changed→changed conflicts; location/applicability refinement only for calibration-earned same↔changed conflicts. All other roles retain V1 quotient.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
