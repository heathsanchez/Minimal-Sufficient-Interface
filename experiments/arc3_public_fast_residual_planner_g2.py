from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-fast-residual-planner-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
SETUP=[(58,46),(58,11)]
TERMINAL=(58,46)
KNOWN=[(58,20),(58,22),(55,20),(54,17),(32,37),(32,42),(32,47),(32,52),(35,37),(35,42),(35,47),(35,52)]
MAX_POLICY=55

def env():
    l=logging.getLogger("fast-residual");l.setLevel(logging.WARNING)
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

def components(f):
    g=grid(f);h,w=len(g),len(g[0]);seen=set();out=[]
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
        out.append({"color":z,"size":len(cells),"cells":sorted(cells)})
    return out

def blue3(f): return sum(1 for x in components(f) if x["color"]==1 and x["size"]==3)
def gray3(f): return sum(1 for x in components(f) if x["color"]==5 and x["size"]==3)

def enter2(e,path=()):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    for rc in SETUP+list(path):
      z=click(e,rc)
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space

def candidates(f):
    out=[];seen=set()
    def add(rc):
      if 0<=rc[0]<64 and 0<=rc[1]<64 and rc not in seen:
        seen.add(rc);out.append(rc)
    for rc in KNOWN:add(rc)
    for x in components(f):
      cells=x["cells"]
      # Every cell of small components because click semantics may depend on subcell position.
      if x["size"]<=16:
        for rc in cells:add(rc)
      else:
        add(cells[len(cells)//2])
        add(cells[0]);add(cells[-1])
    # Both bottom control boxes are tiny and important.
    for r in range(52,63):
      for c in range(4,27):add((r,c))
    return out

def verify(path,terminal=True):
    outs=[]
    for _ in range(2):
      e=env();enter2(e,path)
      if terminal and int(e.observation_space.levels_completed)==1 and e.observation_space.state==GameState.NOT_FINISHED:
        z=click(e,TERMINAL)
      outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                   "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)})
    return outs

def main():
    e=env();path=[];trace=[];probes=0
    for step in range(MAX_POLICY):
      f=enter2(e,path)
      if int(f.levels_completed)>1 or f.state==GameState.WIN:break
      before=blue3(f)
      if before==0:break
      best=None
      for rc in candidates(f):
        b=enter2(e,path);z=click(e,rc);probes+=1
        if z is None or z.state==GameState.GAME_OVER:continue
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
          p=path+[rc];v=verify(p,terminal=False)
          if all(x["progressed"] for x in v):
            out={"status":"PROMOTED","program":[list(x) for x in SETUP+p],"terminal":None,
                 "verification":v,"trace":trace,"probes":probes,"model_calls":0,"source_inspection":False}
            (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_FAST_RESIDUAL_PLANNER_G2=PROMOTED");return
        after=blue3(z);gain=before-after
        if gain<=0:continue
        cand=(-gain,rc[0],rc[1])
        if best is None or cand<best[0]:
          best=(cand,rc,gain,after,gray3(z))
      if best is None:
        trace.append({"step":step,"blue_before":before,"status":"NO_REDUCING_SEMANTIC_ACTION","candidate_count":len(candidates(f))})
        break
      _,rc,gain,after,gray=best
      path.append(rc)
      trace.append({"step":step,"chosen":list(rc),"blue_before":before,"blue_after":after,
                    "gain":gain,"gray_after":gray,"candidate_count":len(candidates(f))})

    f=enter2(e,path)
    pre={"blue3":blue3(f),"gray3":gray3(f),"level":int(f.levels_completed),"state":str(f.state),
         "policy_actions":len(SETUP)+len(path)}
    ver=verify(path,terminal=True)
    ok=all(x["progressed"] for x in ver)
    out={"status":"PROMOTED" if ok else "RESIDUAL",
         "program":[list(x) for x in SETUP+path+[TERMINAL]],"preterminal":pre,
         "verification":ver,"trace":trace,"probes":probes,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"semantic-witness residual-reducing planner with fixed setup and terminal on exact public tn36 G2"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_FAST_RESIDUAL_PLANNER_G2="+out["status"])

if __name__=="__main__":main()
