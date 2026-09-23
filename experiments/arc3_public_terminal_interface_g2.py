from __future__ import annotations
import itertools, json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-terminal-interface-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
PRE=[(58,46),(58,46),(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]
PRIMS=["ACTION1","ACTION2","ACTION3","ACTION4","ACTION5","ACTION7"]
MAX_DEPTH=4

def env():
    l=logging.getLogger("terminal-interface");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def mouse(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def prim(e,name):
    return e.step(getattr(GameAction,name))

def enter_exact_preterminal(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            f=mouse(e,rc)
            if f is None:raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:
        raise RuntimeError(f"g1 drift {e.observation_space.levels_completed}")
    for i,rc in enumerate(PRE):
        f=mouse(e,rc)
        if f is None:raise RuntimeError("pre")
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"preterminal drift at {i}")
    return e.observation_space

def try_seq(e,seq):
    enter_exact_preterminal(e)
    trace=[]
    for name in seq:
        try:
            z=prim(e,name)
        except Exception as ex:
            return {"valid":False,"error":type(ex).__name__,"message":str(ex),"trace":trace}
        if z is None:return {"valid":False,"error":"NoneFrame","trace":trace}
        row={"action":name,"level":int(z.levels_completed),"state":str(z.state)}
        trace.append(row)
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
            return {"valid":True,"progressed":True,"trace":trace,"level":int(z.levels_completed),"state":str(z.state)}
        if z.state==GameState.GAME_OVER:
            return {"valid":True,"progressed":False,"game_over":True,"trace":trace,"level":int(z.levels_completed),"state":str(z.state)}
    return {"valid":True,"progressed":False,"game_over":False,"trace":trace,"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

def verify(seq):
    out=[]
    for _ in range(2):
        e=env();z=try_seq(e,seq)
        out.append({"progressed":bool(z.get("progressed")),"level":z.get("level"),"state":z.get("state"),"trace":z.get("trace")})
    return out

def main():
    e=env();tested=0;per_depth={};selected=None;selected_result=None
    for depth in range(1,MAX_DEPTH+1):
        counts={"tested":0,"progress":0,"game_over":0,"continue":0,"invalid":0}
        for seq in itertools.product(PRIMS,repeat=depth):
            z=try_seq(e,seq);tested+=1;counts["tested"]+=1
            if not z.get("valid"):counts["invalid"]+=1;continue
            if z.get("progressed"):
                counts["progress"]+=1;selected=list(seq);selected_result=z;break
            if z.get("game_over"):counts["game_over"]+=1
            else:counts["continue"]+=1
        per_depth[str(depth)]=counts
        if selected:break
    ver=verify(selected) if selected else []
    ok=bool(selected and all(x["progressed"] for x in ver))
    out={
        "source_strict_transport_run":35868730738,
        "exact_preterminal_program":[list(x) for x in PRE],
        "mouse_terminal_exhausted":True,
        "primitive_alphabet":PRIMS,
        "max_depth":MAX_DEPTH,
        "tested_sequences":tested,
        "per_depth":per_depth,
        "selected":selected,
        "selected_result":selected_result,
        "verification":ver,
        "status":"PROMOTED" if ok else "RESIDUAL",
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"non-mouse terminal-interface search only at exact full-effect transported tn36 G2 preterminal state"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_TERMINAL_INTERFACE_G2="+out["status"])

if __name__=="__main__":
    main()
