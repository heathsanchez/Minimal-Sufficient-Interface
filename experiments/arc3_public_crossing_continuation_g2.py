from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-crossing-continuation-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
MAX_REC=70

def env():
    l=logging.getLogger("crossing"); l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard(); e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter2(e):
    if int(e.observation_space.levels_completed)==0:
        for rc in G1:
            f=click(e,rc)
            if f is None: raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:
        raise RuntimeError("g1 drift")
    return e.observation_space

def run_once():
    e=env(); enter2(e)
    trace=[]
    for rc in ANCHOR:
        f=click(e,rc)
        trace.append({"kind":"anchor","rc":list(rc),"level":int(f.levels_completed),"state":str(f.state)})
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return {"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,"trace":trace,"rec_steps":0,"level":int(f.levels_completed),"state":str(f.state)}
    for i in range(1,MAX_REC+1):
        f=click(e,REC)
        trace.append({"kind":"recurrence","i":i,"rc":list(REC),"level":int(f.levels_completed),"state":str(f.state)})
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return {"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,"trace":trace,"rec_steps":i,"level":int(f.levels_completed),"state":str(f.state)}
    return {"progressed":False,"trace":trace,"rec_steps":MAX_REC,"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

def main():
    trials=[run_once(),run_once()]
    ok=all(t["progressed"] for t in trials)
    out={
        "hypothesis":"same recurrence operator continues through 30<->31 identity swap",
        "anchor":[list(x) for x in ANCHOR],
        "recurrence":list(REC),
        "max_recurrence_steps":MAX_REC,
        "trials":[{k:v for k,v in t.items() if k!="trace"} for t in trials],
        "status":"PROMOTED" if ok else "RESIDUAL",
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 level-2 recurrence continuation only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_CROSSING_CONTINUATION_G2="+out["status"])

if __name__=="__main__":
    main()
