"""Test whether V3 residuals are caused by an under-specified effect quotient.

For primitive actions, classify visible nonzero support displacement and shape
preservation. This refines the CONSEQUENCE label, not the state role.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

def board(x):
    b=x.get("board",[])
    if b and isinstance(b[0],list) and b[0] and isinstance(b[0][0],list):b=b[0]
    return b
def support(g):
    return {(r,c) for r,row in enumerate(g) for c,v in enumerate(row) if str(v) not in ("0","0.0")}
def effect(a,b):
    A=support(a);B=support(b)
    if A==B:return ("support_same",0,0,1)
    if not A or not B:return ("support_birthdeath",0,0,0)
    ar=sum(r for r,c in A)/len(A);ac=sum(c for r,c in A)/len(A)
    br=sum(r for r,c in B)/len(B);bc=sum(c for r,c in B)/len(B)
    dr=round(br-ar);dc=round(bc-ac)
    shifted={(r+dr,c+dc) for r,c in A}
    return ("support_changed",max(-3,min(3,dr)),max(-3,min(3,dc)),int(shifted==B))
def base(g):
    h=len(g);w=len(g[0]) if h else 0;c=Counter(str(v) for row in g for v in row)
    area=max(1,h*w);nz=sum(v for k,v in c.items() if k not in ("0","0.0"))
    return (h,w,min(len(c),8),0 if nz==0 else 1 if nz/area<.1 else 2 if nz/area<.5 else 3)
def rows(p):
    z=[];prev=None;lev=0
    for line in p.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            n=str(x.get("action_name",""))
            if n=="RESET":prev=now;continue
            if n.startswith("ACTION"):
                aid=int(n.replace("ACTION",""))
                if prev is not None and aid!=6:z.append((lev,(aid,)+base(prev),effect(prev,now)))
                if bool(x.get("level_completed")):lev+=1
        prev=now
    return z
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):games[p.name.split("_p",1)[0]].append(rows(p))
    folds=[];K=W=N=0
    for game,trs in sorted(games.items()):
        cal=[tr for i,tr in enumerate(trs) if i%2==0];ev=[tr for i,tr in enumerate(trs) if i%2==1]
        for target in sorted({l for tr in trs for l,_,_ in tr if l>0}):
            seen=defaultdict(set)
            for tr in cal:
                for l,r,y in tr:
                    if l<target:seen[r].add(y)
            m={r:next(iter(v)) for r,v in seen.items() if len(v)==1}
            k=w=n=0
            for tr in ev:
                for l,r,y in tr:
                    if l!=target:continue
                    n+=1
                    if r in m:k+=1;w+=m[r]!=y
            if n:folds.append(dict(game=game,target_level=target,cells=n,known=k,wrong=w,coverage=k/n));K+=k;W+=w;N+=n
    out=dict(schema="msi.arc3-effect-quotient-prospective-v1",heldout_cells=N,predicted_cells=K,wrong_predictions=W,coverage=K/N if N else 0,folds=folds,status="ZERO_ERROR_CANDIDATE" if K and W==0 else "REJECTED",boundary="Disjoint trace split; primitive actions only; state role is unchanged V1; output quotient records nonzero-support displacement and exact translation.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
