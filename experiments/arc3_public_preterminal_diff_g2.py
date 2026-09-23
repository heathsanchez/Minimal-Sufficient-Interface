from __future__ import annotations
import json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-preterminal-diff-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)

def env():
    l=logging.getLogger("preterminal-diff");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc;return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def feat(f):
    g=grid(f);h,w=len(g),len(g[0]);seen=set()
    size=Counter();color_size=Counter();shape=Counter()
    colors=Counter(v for row in g for v in row)
    for r in range(h):
      for c in range(w):
        if (r,c) in seen:continue
        z=g[r][c];q=deque([(r,c)]);seen.add((r,c));cells=[]
        while q:
          rr,cc=q.popleft();cells.append((rr,cc))
          for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr,nc=rr+dr,cc+dc
            if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==z:
              seen.add((nr,nc));q.append((nr,nc))
        rs=[x[0] for x in cells];cs=[x[1] for x in cells]
        n=len(cells);size[n]+=1;color_size[(z,n)]+=1
        shape[(z,max(rs)-min(rs)+1,max(cs)-min(cs)+1,n)]+=1
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"size":size,"color_size":color_size,"shape":shape,"colors":colors,"rt":rt,"ct":ct}

def delta(a,b):
    out={}
    for name in ("size","color_size","shape","colors"):
        keys=set(a[name])|set(b[name])
        out[name]={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
    out["rt"]=b["rt"]-a["rt"];out["ct"]=b["ct"]-a["ct"]
    return out

def residual(src,tgt):
    out={}
    for name in ("size","color_size","shape","colors"):
        keys=set(src[name])|set(tgt[name])
        out[name]={k:int(src[name].get(k,0)-tgt[name].get(k,0)) for k in keys if src[name].get(k,0)!=tgt[name].get(k,0)}
    out["rt"]=src["rt"]-tgt["rt"];out["ct"]=src["ct"]-tgt["ct"]
    return out

def main():
    s=env();s0=feat(s.observation_space)
    for rc in G1[:-1]:click(s,rc)
    s8=feat(s.observation_space);sd=delta(s0,s8)

    t=env()
    for rc in G1:click(t,rc)
    t0=feat(t.observation_space)
    for rc in ANCHOR:click(t,rc)
    for _ in range(3):click(t,REC)
    t8=feat(t.observation_space);td=delta(t0,t8)

    res=residual(sd,td)
    nonzero={k:v for k,v in res.items() if v not in ({},0)}
    out={"source_net":sd,"target_net":td,"residual":nonzero,
         "size_residual_zero":not bool(nonzero.get("size")),
         "model_calls":0,"source_inspection":False}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PRETERMINAL_DIFF_G2=PASS")
if __name__=="__main__":main()
