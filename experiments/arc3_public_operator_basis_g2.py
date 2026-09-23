from __future__ import annotations

import json, logging, os
from collections import Counter, deque
from pathlib import Path
from typing import Any
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUTDIR=Path(os.environ.get("OUTDIR","evidence/arc3-public-operator-basis-g2")).resolve()
OUTDIR.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
PROBES=[(58,46),(58,11),(58,20),(58,22),(55,20)]

def grid(f):
    r=f.frame
    if isinstance(r,(list,tuple)): r=r[-1]
    if hasattr(r,"tolist"): r=r.tolist()
    return [[int(x) for x in row] for row in r]

def comps(g):
    if not g:return []
    h,w=len(g),len(g[0]); seen=set(); out=[]
    for r in range(h):
      for c in range(w):
        if (r,c) in seen:continue
        z=g[r][c]; q=deque([(r,c)]);seen.add((r,c));cells=[]
        while q:
          rr,cc=q.popleft();cells.append((rr,cc))
          for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr,nc=rr+dr,cc+dc
            if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==z:
              seen.add((nr,nc));q.append((nr,nc))
        out.append(cells)
    return out

def summ(f):
    g=grid(f);h=len(g);w=len(g[0]); total=h*w
    areas=Counter(len(x) for x in comps(g) if len(x)<=max(16,total//4))
    hist=Counter(x for row in g for x in row)
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"cc":sum(areas.values()),"areas":dict(areas),"hist":dict(hist),"rt":rt,"ct":ct}

def diffmap(a,b):
    return {str(k):b.get(k,0)-a.get(k,0) for k in set(a)|set(b) if b.get(k,0)!=a.get(k,0)}

def sig(a,b):
    hd=diffmap(a["hist"],b["hist"])
    return {"dcc":b["cc"]-a["cc"],"da":diffmap(a["areas"],b["areas"]),
            "hu":sorted(hd.values()),"dr":b["rt"]-a["rt"],"dc":b["ct"]-a["ct"]}

def dist(a,b):
    d=20*abs(a["dcc"]-b["dcc"])
    d+=25*sum(abs(a["da"].get(k,0)-b["da"].get(k,0)) for k in set(a["da"])|set(b["da"]))
    x=list(a["hu"]);y=list(b["hu"]);n=max(len(x),len(y));x += [0]*(n-len(x));y += [0]*(n-len(y))
    d+=2*sum(abs(p-q) for p,q in zip(sorted(x),sorted(y)))
    d+=abs(a["dr"]-b["dr"])+abs(a["dc"]-b["dc"])
    return d

def env():
    l=logging.getLogger("basis");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc;return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter2(e):
    if int(e.observation_space.levels_completed)==0:
      for x in G1:click(e,x)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    return e.observation_space

def reset2(e):
    f=e.reset()
    if int(f.levels_completed)==0:return enter2(e)
    if int(f.levels_completed)!=1:raise RuntimeError(f"reset {f.levels_completed}")
    return f

def replay_target(e,path):
    reset2(e)
    for x in path:
      f=click(e,x)
      if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space

def source_ops():
    e=env(); prev=summ(e.observation_space);o=[]
    for i,x in enumerate(G1):
      f=click(e,x);cur=summ(f);o.append({"i":i,"sig":sig(prev,cur),"rc":list(x)});prev=cur
    return o

def root_basis():
    e=env();enter2(e); seen={}; progressed=[]
    for r in range(64):
      for c in range(64):
        reset2(e); a=summ(e.observation_space); f=click(e,(r,c))
        if f is None or f.state==GameState.GAME_OVER:continue
        s=sig(a,summ(f));k=json.dumps(s,sort_keys=True,separators=(",",":"))
        seen.setdefault(k,{"rc":[r,c],"sig":s,"count":0});seen[k]["count"]+=1
        if int(f.levels_completed)>1: progressed.append([r,c])
    return list(seen.values()),progressed

def main():
    src=source_ops(); basis,one_step=root_basis()
    reps=[tuple(x["rc"]) for x in basis]
    for p in PROBES:
      if p not in reps:reps.insert(0,p)
    e=env();enter2(e);path=[];trace=[];residual=None
    for op in src:
      # current basis evaluation: one representative per frozen action class + historical probes.
      classes={}
      for rc in reps:
        replay_target(e,path)
        if int(e.observation_space.levels_completed)>1:break
        a=summ(e.observation_space); f=click(e,rc)
        if f is None or f.state==GameState.GAME_OVER:continue
        s=sig(a,summ(f));k=json.dumps(s,sort_keys=True,separators=(",",":"))
        classes.setdefault(k,{"rc":rc,"sig":s,"progress":int(f.levels_completed)>1})
      if not classes: residual={"source_step":op["i"],"reason":"empty-basis"};break
      ranked=sorted((dist(op["sig"],z["sig"]),z) for z in classes.values())
      bestd,best=ranked[0]; path.append(best["rc"])
      replay_target(e,path); progressed=int(e.observation_space.levels_completed)>1
      trace.append({"source_step":op["i"],"source_rc":op["rc"],"target_rc":list(best["rc"]),
                    "distance":bestd,"current_effect_classes":len(classes),"progressed":progressed})
      if progressed:break
      # Strict missing-operator criterion: if even the nearest basis realization is structurally far,
      # name it rather than silently broadening.
      if bestd>80:
        residual={"source_step":op["i"],"reason":"operator-not-in-frozen-basis","distance":bestd};break

    ver=[]
    if int(e.observation_space.levels_completed)>1:
      for _ in range(2):
        z=env();enter2(z)
        for rc in path:
          f=click(z,rc)
          if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):break
        ver.append({"level":int(z.observation_space.levels_completed),"state":str(z.observation_space.state),
                    "progressed":int(z.observation_space.levels_completed)>1})
    ok=bool(ver and all(x["progressed"] for x in ver))
    out={"source_run":35811403514,"g1_run":35854403385,"model_calls":0,"source_inspection":False,
         "root_action_basis":{"raw_actions":4096,"effect_classes":len(basis),"one_step_progress":one_step},
         "historical_probes":[list(x) for x in PROBES],"transport_trace":trace,
         "program":[list(x) for x in path],"verification":ver,"residual":residual,
         "status":"PROMOTED" if ok else "RESIDUAL"}
    (OUTDIR/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_OPERATOR_BASIS_G2="+out["status"])
if __name__=="__main__":main()
