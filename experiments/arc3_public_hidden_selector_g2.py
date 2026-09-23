from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-hidden-selector-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
A=(58,46)
TOGGLES=[(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]

def env():
    l=logging.getLogger("hidden-selector");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter2(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    return e.observation_space

def trial(e,B):
    enter2(e)
    trace=[]
    for label,rc in [("A0",A),("B",B),*[(f"T{i+1}",rc) for i,rc in enumerate(TOGGLES)],("A1",A)]:
      z=click(e,rc)
      if z is None:return {"valid":False,"trace":trace}
      trace.append({"label":label,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return {"valid":True,
            "progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
            "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace}

def verify(B):
    return [trial(env(),B),trial(env(),B)]

def main():
    e=env();tested=0;selected=None;first_positive=None
    # High-value semantic order first, then exhaustive grid.
    preferred=[]
    # Top-right purple selector cells from visible board region plus top-left yellow region and control boxes.
    for r in range(0,32):
      for c in range(0,64):
        preferred.append((r,c))
    for r in range(52,63):
      for c in range(4,30):
        preferred.append((r,c))
    seen=set();order=[]
    for rc in preferred+[(r,c) for r in range(64) for c in range(64)]:
      if rc not in seen:seen.add(rc);order.append(rc)

    for B in order:
      z=trial(e,B);tested+=1
      if z.get("progressed"):
        v=verify(B)
        if all(x.get("progressed") for x in v):
          selected=B;first_positive=z;verification=v;break
    else:
      verification=[]

    out={
      "source_schema":"A,hidden-selector-B,transported-toggle^6,A",
      "A":list(A),"toggles":[list(x) for x in TOGGLES],
      "tested_selectors":tested,
      "selected_B":list(selected) if selected else None,
      "selected_trial":first_positive,
      "verification":verification,
      "status":"PROMOTED" if selected else "RESIDUAL",
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"exact public tn36 G2 exhaustive hidden-selector witness search with fixed transported six-operator suffix"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_HIDDEN_SELECTOR_G2="+out["status"])

if __name__=="__main__":main()
