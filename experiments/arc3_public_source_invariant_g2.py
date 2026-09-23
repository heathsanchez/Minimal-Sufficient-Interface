from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-source-invariant-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
A=(58,46)
B=(58,11)
MAX_LEVEL_ACTIONS=60

def env():
    l=logging.getLogger("source-invariant");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def comps(f):
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

def blue3(f):
    return [x for x in comps(f) if x["color"]==1 and x["size"]==3]

def gray3(f):
    return [x for x in comps(f) if x["color"]==5 and x["size"]==3]

def enter2(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    return e.observation_space

def run_once():
    e=env();enter2(e)
    trace=[];actions=0

    for label,rc in [("A0",A),("B",B)]:
      f=click(e,rc);actions+=1
      trace.append({"action":actions,"label":label,"rc":list(rc),
                    "blue3":len(blue3(f)),"gray3":len(gray3(f)),
                    "level":int(f.levels_completed),"state":str(f.state)})
      if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
        break

    while actions < MAX_LEVEL_ACTIONS-1 and int(e.observation_space.levels_completed)==1 and e.observation_space.state==GameState.NOT_FINISHED:
      bs=blue3(e.observation_space)
      if not bs:break
      before=len(bs);before_gray=len(gray3(e.observation_space))
      # Click the middle cell of the first spatially ordered blue 3-component.
      comp=sorted(bs,key=lambda x:x["cells"])[0]
      rc=comp["cells"][len(comp["cells"])//2]
      f=click(e,rc);actions+=1
      after=len(blue3(f));after_gray=len(gray3(f))
      trace.append({"action":actions,"label":"toggle","rc":list(rc),
                    "blue_before":before,"blue_after":after,
                    "gray_before":before_gray,"gray_after":after_gray,
                    "level":int(f.levels_completed),"state":str(f.state)})
      if after>=before:
        # This candidate did not consume a blue component; avoid an infinite loop.
        break
      if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
        break

    preterminal={"blue3":len(blue3(e.observation_space)),"gray3":len(gray3(e.observation_space)),
                 "actions":actions,"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}
    if actions < MAX_LEVEL_ACTIONS and int(e.observation_space.levels_completed)==1 and e.observation_space.state==GameState.NOT_FINISHED:
      f=click(e,A);actions+=1
      trace.append({"action":actions,"label":"A1","rc":list(A),
                    "blue3":len(blue3(f)),"gray3":len(gray3(f)),
                    "level":int(f.levels_completed),"state":str(f.state)})

    return {
      "preterminal":preterminal,"actions":actions,
      "progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
      "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
      "trace":trace,
    }

def main():
    trials=[run_once(),run_once()]
    ok=all(x["progressed"] for x in trials)
    out={
      "source_schema":"A,B,consume every blue size-3 component,return A",
      "A":list(A),"B":list(B),"trials":trials,
      "status":"PROMOTED" if ok else "RESIDUAL",
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"exact public tn36 G2 source-shaped dynamic blue3->gray3 invariant"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SOURCE_INVARIANT_G2="+out["status"])

if __name__=="__main__":
    main()
