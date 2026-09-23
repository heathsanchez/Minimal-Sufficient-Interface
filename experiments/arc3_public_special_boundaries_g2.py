from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-special-boundaries-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
# n = 5+k, reservoir = 56-k. Test equality/collision with fixed sizes 6,32,41,
# the n~reservoir crossing, and near exhaustion.
KS=[1,15,24,25,26,27,36,50,52,53,54]

def env():
    l=logging.getLogger("special-boundaries");l.setLevel(logging.WARNING)
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
        for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):raise RuntimeError("anchor drift")
    for i in range(k):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return f
    return e.observation_space

def verify(k,rc):
    out=[]
    for _ in range(2):
        e=env();f=enter_k(e,k);z=click(e,rc)
        out.append({"level":int(z.levels_completed),"state":str(z.state),"progressed":int(z.levels_completed)>1 or z.state==GameState.WIN})
    return out

def main():
    e=env();summaries=[];selected=None
    for k in KS:
        counts={"continue":0,"game_over":0,"progress":0}
        success=None
        for r in range(64):
            for c in range(64):
                f=enter_k(e,k)
                if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
                    raise RuntimeError(f"preterminal at k={k}")
                z=click(e,(r,c))
                if int(z.levels_completed)>1 or z.state==GameState.WIN:
                    counts["progress"]+=1
                    success=(r,c)
                    break
                elif z.state==GameState.GAME_OVER:counts["game_over"]+=1
                else:counts["continue"]+=1
            if success:break
        summaries.append({"k":k,"n":5+k,"reservoir":56-k,"counts":counts,"success":list(success) if success else None})
        if success:
            selected={"k":k,"rc":list(success)}
            break
    ver=verify(selected["k"],tuple(selected["rc"])) if selected else []
    ok=bool(selected and all(x["progressed"] for x in ver))
    out={"boundaries":summaries,"selected":selected,"verification":ver,
         "status":"PROMOTED" if ok else "RESIDUAL","model_calls":0,"source_inspection":False}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SPECIAL_BOUNDARIES_G2="+out["status"])
if __name__=="__main__":main()
