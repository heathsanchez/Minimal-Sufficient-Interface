from __future__ import annotations
import json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-strict-operator-transport-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
HIST=[(58,46),(58,11),(58,20),(58,22),(55,20),(32,37),(2,20)]

def env():
    l=logging.getLogger("strict-transport");l.setLevel(logging.WARNING)
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
    shape=Counter();color_size=Counter();colors=Counter(v for row in g for v in row);sizes=Counter()
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
        rs=[x[0] for x in cells];cs=[x[1] for x in cells];n=len(cells)
        sizes[n]+=1;color_size[(z,n)]+=1;shape[(z,max(rs)-min(rs)+1,max(cs)-min(cs)+1,n)]+=1
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"sizes":sizes,"shape":shape,"color_size":color_size,"colors":colors,"rt":rt,"ct":ct}

def delta(a,b):
    out={}
    for name in ("sizes","shape","color_size","colors"):
      keys=set(a[name])|set(b[name])
      d={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
      if d:out[name]=d
    for name in ("rt","ct"):
      v=b[name]-a[name]
      if v:out[name]=v
    return out

def source_effects():
    e=env();prev=feat(e.observation_space);rows=[]
    for i,rc in enumerate(G1[:-1]):
      z=click(e,rc);cur=feat(z);rows.append({"i":i,"rc":list(rc),"effect":delta(prev,cur)});prev=cur
    return rows

def reset_level2(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:
        z=click(e,rc)
        if z is None:raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError(f"g1 drift {e.observation_space.levels_completed}")
    return e.observation_space

def replay(e,path):
    reset_level2(e)
    for rc in path:
      z=click(e,rc)
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space

def candidate_order():
    out=[];seen=set()
    for rc in HIST:
      if rc not in seen:seen.add(rc);out.append(rc)
    for r in range(64):
      for c in range(64):
        if (r,c) not in seen:seen.add((r,c));out.append((r,c))
    return out

def effect_distance(a,b):
    # Exact match is authority; this is diagnostic only.
    score=0
    for name,w in (("sizes",30),("shape",20),("color_size",15),("colors",2)):
      aa=a.get(name,{});bb=b.get(name,{})
      score+=w*sum(abs(int(aa.get(k,0))-int(bb.get(k,0))) for k in set(aa)|set(bb))
    score+=abs(int(a.get("rt",0))-int(b.get("rt",0)))
    score+=abs(int(a.get("ct",0))-int(b.get("ct",0)))
    return score

def verify(program):
    out=[]
    for _ in range(2):
      e=env();reset_level2(e)
      trace=[]
      for rc in program:
        z=click(e,tuple(rc));trace.append({"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
      out.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                  "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace})
    return out

def main():
    src=source_effects();e=env();path=[];trace=[];total_tested=0;failed=None
    order=candidate_order()
    for row in src:
      target=row["effect"];matches=[];best=None
      for rc in order:
        f=replay(e,path)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):continue
        before=feat(f);z=click(e,rc);total_tested+=1
        if z is None or z.state==GameState.GAME_OVER:continue
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
          matches.append({"rc":list(rc),"direct_progress":True,"effect":delta(before,feat(z))});break
        ed=delta(before,feat(z));d=effect_distance(target,ed)
        if best is None or (d,rc)<(best["distance"],tuple(best["rc"])):
          best={"rc":list(rc),"distance":d,"effect":ed}
        if ed==target:
          matches.append({"rc":list(rc),"direct_progress":False,"effect":ed});break
      if not matches:
        failed={"source_step":row["i"],"source_effect":target,"best":best}
        trace.append({"source_step":row["i"],"status":"NO_EXACT_MATCH","best":best})
        break
      chosen=matches[0]
      path.append(tuple(chosen["rc"]))
      trace.append({"source_step":row["i"],"source_rc":row["rc"],"target_rc":chosen["rc"],
                    "exact":chosen["effect"]==target,"direct_progress":chosen["direct_progress"]})
      if chosen["direct_progress"]:break

    terminal=None
    if failed is None and len(path)==len(src):
      for rc in order:
        f=replay(e,path)
        before=feat(f);z=click(e,rc);total_tested+=1
        if z is None:continue
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
          terminal=list(rc);path.append(rc);break

    program=[list(x) for x in path]
    ver=verify(program) if terminal else []
    ok=bool(terminal and all(x["progressed"] for x in ver))
    out={
      "source_effects":src,"transport_trace":trace,"failed":failed,
      "terminal":terminal,"program":program,"tested_transitions":total_tested,
      "verification":ver,"status":"PROMOTED" if ok else "RESIDUAL",
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"exact full-effect operator transport for G1 preterminal law onto public tn36 G2"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_STRICT_OPERATOR_TRANSPORT_G2="+out["status"])

if __name__=="__main__":main()
