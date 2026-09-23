from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-lineage-terminal-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]

A=(58,46)
B=(58,11)
TOGGLES=[(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]
LINEAGE=[A,B,*TOGGLES,A]
COLLAPSED=[A,A,*TOGGLES,A]
SWAPPED=[A,B,*TOGGLES,B]
NO_TERMINAL=[A,B,*TOGGLES]

def env():
    l=logging.getLogger("lineage-terminal"); l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard(); e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter2(e):
    f=e.reset()
    if f is None: raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            f=click(e,rc)
            if f is None: raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:
        raise RuntimeError(f"g1 drift {e.observation_space.levels_completed}")
    return e.observation_space

def run(program):
    e=env(); enter2(e); trace=[]
    for i,rc in enumerate(program):
        f=click(e,rc)
        if f is None: raise RuntimeError("click")
        trace.append({"i":i,"rc":list(rc),"level":int(f.levels_completed),"state":str(f.state)})
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return {
        "progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "actions":len(trace),
        "trace":trace,
    }

def twice(program):
    return [run(program),run(program)]

def main():
    arms={
        "lineage_return_A":twice(LINEAGE),
        "collapsed_A_A":twice(COLLAPSED),
        "terminal_B":twice(SWAPPED),
        "no_terminal":twice(NO_TERMINAL),
    }
    lineage_ok=all(x["progressed"] for x in arms["lineage_return_A"])
    controls_fail=all(not x["progressed"] for k,v in arms.items() if k!="lineage_return_A" for x in v)
    out={
        "source_pattern":"A,B,toggle^6,A",
        "source_program":[list(x) for x in G1],
        "transport":{"A":list(A),"B":list(B),"toggles":[list(x) for x in TOGGLES]},
        "program":[list(x) for x in LINEAGE],
        "arms":arms,
        "lineage_positive":lineage_ok,
        "controls_fail":controls_fail,
        "status":"PROMOTED" if lineage_ok else "RESIDUAL",
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G2 lineage-preserving witness transport",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_LINEAGE_TERMINAL_G2="+out["status"])

if __name__=="__main__":
    main()
