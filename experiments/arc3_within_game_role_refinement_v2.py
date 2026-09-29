"""Counterexample-driven refinement of the within-game ARC role quotient.

Start with V1. Refine ONLY coarse roles that actually make a held-out-level
mistake, using canonical local geometry summaries. Nonconflicting roles remain
byte-for-byte V1. No game ID, exact hash, or raw pixel tuple enters the role.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path

def board(row):
    b=row.get("board",[])
    if b and isinstance(b[0],list) and b[0] and isinstance(b[0][0],list): b=b[0]
    return b

def base(g):
    h=len(g);w=len(g[0]) if h else 0; c=Counter(str(v) for r in g for v in r)
    area=max(1,h*w);nz=sum(v for k,v in c.items() if k not in ("0","0.0"))
    return (h,w,min(len(c),8),0 if nz==0 else 1 if nz/area<.1 else 2 if nz/area<.5 else 3)

def geom(g):
    h=len(g);w=len(g[0]) if h else 0
    nz=[(r,c) for r,row in enumerate(g) for c,v in enumerate(row) if str(v) not in ("0","0.0")]
    if not nz:return (0,0,0,0,0)
    rs=[p[0] for p in nz];cs=[p[1] for p in nz]
    bh=max(rs)-min(rs)+1;bw=max(cs)-min(cs)+1
    border=sum(r in (0,h-1) or c in (0,w-1) for r,c in nz)
    comps=0;todo=set(nz)
    while todo:
        comps+=1;stack=[todo.pop()]
        while stack:
            r,c=stack.pop()
            for q in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if q in todo:todo.remove(q);stack.append(q)
    return (min(bh,8),min(bw,8),min(comps,8),min(border,8),
            int(len(nz)==bh*bw))

def out(a,b):
    aa,bb=base(a),base(b)
    return ("same" if a==b else "changed",
            (bb[2]>aa[2])-(bb[2]<aa[2]),(bb[3]>aa[3])-(bb[3]<aa[3]))

def traces(path):
    z=[];prev=None;level=0
    for line in path.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            name=str(x.get("action_name",""))
            if name=="RESET":prev=now;continue
            if name.startswith("ACTION"):
                aid=int(name.replace("ACTION",""))
                if prev is not None and aid!=6:
                    coarse=(aid,)+base(prev)
                    z.append((level,coarse,coarse+geom(prev),out(prev,now)))
                if bool(x.get("level_completed")):level+=1
        prev=now
    return z

def eval_fold(trs,target,refine):
    seen=defaultdict(set)
    for tr in trs:
        for lev,coarse,fine,y in tr:
            if lev<target:seen[fine if coarse in refine else coarse].add(y)
    mapping={r:next(iter(v)) for r,v in seen.items() if len(v)==1}
    k=w=n=0;bad=set()
    for tr in trs:
        for lev,coarse,fine,y in tr:
            if lev!=target:continue
            n+=1;r=fine if coarse in refine else coarse
            if r in mapping:
                k+=1
                if mapping[r]!=y:w+=1;bad.add(coarse)
    return k,w,n,bad

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):
        games[p.name.split("_p",1)[0]].append(traces(p))
    folds=[];K=W=N=0
    for game,trs in sorted(games.items()):
        for target in sorted({lev for tr in trs for lev,*_ in tr if lev>0}):
            k0,w0,n,bad=eval_fold(trs,target,set())
            k,w,n,bad2=eval_fold(trs,target,bad)
            folds.append(dict(game=game,target_level=target,cells=n,
                coarse_known=k0,coarse_wrong=w0,refined_roles=len(bad),
                known=k,wrong=w,coverage=k/n if n else 0,
                remaining_bad_roles=len(bad2)))
            K+=k;W+=w;N+=n
    out=dict(schema="msi.arc3-within-game-counterexample-refinement-v2",
        heldout_cells=N,predicted_cells=K,wrong_predictions=W,
        coverage=K/N if N else 0,folds=folds,
        status="ZERO_ERROR_CANDIDATE" if K and W==0 else "REJECTED",
        boundary=("Only V1 roles that cause a held-out-level error are refined. "
                  "Refinement adds canonical nonzero bounding-box/component/border "
                  "summaries; no game ID, exact board hash, or raw pixel tuple."))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
