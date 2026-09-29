"""Prospective ARC role refinement: choose refinements on calibration traces,
then score disjoint held-out traces at the next level.

This prevents a counterexample-driven refinement from being credited merely
because the same trajectories both selected and evaluated the distinction.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path

def board(row):
    b=row.get("board",[])
    if b and isinstance(b[0],list) and b[0] and isinstance(b[0][0],list):b=b[0]
    return b
def base(g):
    h=len(g);w=len(g[0]) if h else 0;c=Counter(str(v) for r in g for v in r)
    area=max(1,h*w);nz=sum(v for k,v in c.items() if k not in ("0","0.0"))
    return (h,w,min(len(c),8),0 if nz==0 else 1 if nz/area<.1 else 2 if nz/area<.5 else 3)
def geom(g):
    h=len(g);w=len(g[0]) if h else 0;nz={(r,c) for r,row in enumerate(g) for c,v in enumerate(row) if str(v) not in ("0","0.0")}
    if not nz:return (0,0,0,0,0)
    rs=[r for r,c in nz];cs=[c for r,c in nz];bh=max(rs)-min(rs)+1;bw=max(cs)-min(cs)+1
    border=sum(r in (0,h-1) or c in (0,w-1) for r,c in nz);todo=set(nz);comps=0
    while todo:
        comps+=1;stack=[todo.pop()]
        while stack:
            r,c=stack.pop()
            for q in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if q in todo:todo.remove(q);stack.append(q)
    return (min(bh,8),min(bw,8),min(comps,8),min(border,8),int(len(nz)==bh*bw))
def outcome(a,b):
    x,y=base(a),base(b);return ("same" if a==b else "changed",(y[2]>x[2])-(y[2]<x[2]),(y[3]>x[3])-(y[3]<x[3]))
def trace(p):
    z=[];prev=None;lev=0
    for line in p.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            name=str(x.get("action_name",""))
            if name=="RESET":prev=now;continue
            if name.startswith("ACTION"):
                aid=int(name.replace("ACTION",""))
                if prev is not None and aid!=6:
                    coarse=(aid,)+base(prev);z.append((lev,coarse,coarse+geom(prev),outcome(prev,now)))
                if bool(x.get("level_completed")):lev+=1
        prev=now
    return z
def mapping(rows,target,refine):
    seen=defaultdict(set)
    for tr in rows:
        for lev,c,f,y in tr:
            if lev<target:seen[f if c in refine else c].add(y)
    return {r:next(iter(v)) for r,v in seen.items() if len(v)==1}
def score(rows,target,m,refine):
    k=w=n=0;bad=set()
    for tr in rows:
        for lev,c,f,y in tr:
            if lev!=target:continue
            n+=1;r=f if c in refine else c
            if r in m:k+=1;w+=m[r]!=y;bad|={c} if m[r]!=y else set()
    return k,w,n,bad
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):games[p.name.split("_p",1)[0]].append((p.name,trace(p)))
    folds=[];K=W=N=0
    for game,named in sorted(games.items()):
        cal=[tr for i,(n,tr) in enumerate(named) if i%2==0];ev=[tr for i,(n,tr) in enumerate(named) if i%2==1]
        for target in sorted({lev for _,tr in named for lev,*_ in tr if lev>0}):
            m0=mapping(cal,target,set());_,_,_,bad=score(cal,target,m0,set())
            m=mapping(cal,target,bad);k,w,n,_=score(ev,target,m,bad)
            if n:folds.append(dict(game=game,target_level=target,refined_roles=len(bad),cells=n,known=k,wrong=w,coverage=k/n));K+=k;W+=w;N+=n
    out=dict(schema="msi.arc3-prospective-role-refinement-v3",heldout_cells=N,predicted_cells=K,wrong_predictions=W,coverage=K/N if N else 0,folds=folds,status="ZERO_ERROR_CANDIDATE" if K and W==0 else "REJECTED",boundary="Even-index public traces choose/refine roles; odd-index traces evaluate them. Earlier levels only calibrate each target level. No game ID/hash/raw pixel role.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
