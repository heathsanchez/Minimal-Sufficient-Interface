from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-known-operator-timing-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
KNOWN=[(58,46),(58,11),(58,20),(58,22),(55,20),(32,37),(2,20)]
MAX_K=55

def env():
    l=logging.getLogger("known-op-timing");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter_k(e,k):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1: click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("anchor drift")
    for i in range(k):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return f
    return e.observation_space

def main():
    e=env();rows=[];selected=None
    for k in range(MAX_K+1):
        for rc in KNOWN:
            f=enter_k(e,k)
            if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
                rows.append({"k":k,"rc":list(rc),"preterminal":True,"level":int(f.levels_completed),"state":str(f.state)})
                continue
            z=click(e,rc)
            row={"k":k,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state),
                 "progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,
                 "game_over":z.state==GameState.GAME_OVER}
            rows.append(row)
            if row["progressed"]:
                selected={"k":k,"rc":list(rc)}
                break
        if selected:break
    ver=[]
    if selected:
        for _ in range(2):
            z=env();enter_k(z,selected["k"]);f=click(z,tuple(selected["rc"]))
            ver.append({"level":int(f.levels_completed),"state":str(f.state),
                        "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN})
    ok=bool(selected and all(x["progressed"] for x in ver))
    out={"known_operators":[list(x) for x in KNOWN],"tested":len(rows),"selected":selected,"verification":ver,
         "status":"PROMOTED" if ok else "RESIDUAL","model_calls":0,"source_inspection":False,
         "rows":rows}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!="rows"},indent=2))
    print("ARC3_PUBLIC_KNOWN_OPERATOR_TIMING_G2="+out["status"])
if __name__=="__main__":main()
