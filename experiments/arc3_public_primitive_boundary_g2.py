from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-primitive-boundary-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC_STEPS=55

def env():
    l=logging.getLogger("primitive-boundary");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def mouse(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def boundary(e):
    if int(e.observation_space.levels_completed)==0:
        for rc in G1: mouse(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in ANCHOR: mouse(e,rc)
    for _ in range(REC_STEPS):
        f=mouse(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"boundary drift {f.levels_completed} {f.state}")
    return e.observation_space

def reset_boundary(e):
    f=e.reset()
    if int(f.levels_completed)==0:
        return boundary(e)
    if int(f.levels_completed)!=1:raise RuntimeError(f"reset {f.levels_completed}")
    for rc in ANCHOR: mouse(e,rc)
    for _ in range(REC_STEPS):
        f=mouse(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"boundary drift {f.levels_completed} {f.state}")
    return e.observation_space

def main():
    e=env();boundary(e)
    rows=[];winner=None
    names=[x.name for x in GameAction]
    for name in names:
        if name in ("ACTION6","RESET"):continue
        reset_boundary(e)
        try:
            f=e.step(GameAction[name])
            row={"action":name,"level":int(f.levels_completed),"state":str(f.state),
                 "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN}
        except Exception as ex:
            row={"action":name,"error":type(ex).__name__+":"+str(ex)}
        rows.append(row)
        if row.get("progressed") and winner is None:winner=name
    verify=[]
    if winner:
        for _ in range(2):
            z=env();boundary(z);f=z.step(GameAction[winner])
            verify.append({"level":int(f.levels_completed),"state":str(f.state),"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN})
    out={"enum":names,"tested":rows,"selected":winner,"verification":verify,
         "status":"PROMOTED" if verify and all(x["progressed"] for x in verify) else "RESIDUAL",
         "model_calls":0,"source_inspection":False}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PRIMITIVE_BOUNDARY_G2="+out["status"])
if __name__=="__main__":main()
