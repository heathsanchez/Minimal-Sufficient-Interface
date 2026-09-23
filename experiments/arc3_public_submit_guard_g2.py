from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-submit-guard-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC_STEPS=55
SUBMIT=(58,46)

def env():
    l=logging.getLogger("submit-guard");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def run_once():
    e=env()
    for rc in G1:
        f=click(e,rc)
    if int(e.observation_space.levels_completed)!=1:
        raise RuntimeError("G1 drift")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return {"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,"stage":"anchor","level":int(f.levels_completed),"state":str(f.state)}
    for i in range(REC_STEPS):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return {"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,"stage":f"recurrence-{i+1}","level":int(f.levels_completed),"state":str(f.state)}
    f=click(e,SUBMIT)
    return {
        "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,
        "stage":"submit",
        "level":int(f.levels_completed),
        "state":str(f.state),
    }

def main():
    trials=[run_once(),run_once()]
    ok=all(x["progressed"] for x in trials)
    out={
        "program":{"anchor":[list(x) for x in ANCHOR],"recurrence":list(REC),"recurrence_steps":REC_STEPS,"submit":list(SUBMIT)},
        "level2_actions":len(ANCHOR)+REC_STEPS+1,
        "trials":trials,
        "status":"PROMOTED" if ok else "RESIDUAL",
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G2 guarded submit hypothesis",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SUBMIT_GUARD_G2="+out["status"])

if __name__=="__main__":
    main()
