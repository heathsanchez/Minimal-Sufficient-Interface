from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUTDIR=Path(os.environ.get("OUTDIR","evidence/arc3-public-missing-terminal-g2")).resolve()
OUTDIR.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
PREFIX=[(58,11),(58,11),(32,37),(32,37),(32,37),(32,37),(32,37),(32,37)]

def env():
    l=logging.getLogger("g2-terminal");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter_prefix(e):
    for rc in G1:
        f=click(e,rc)
        if f is None:raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    for rc in PREFIX:
        f=click(e,rc)
        if f is None:raise RuntimeError("prefix")
        if int(f.levels_completed)>1:raise RuntimeError("prefix unexpectedly already progressed")
        if f.state==GameState.GAME_OVER:raise RuntimeError("prefix game over")
    return e.observation_space

def fresh_prefix():
    e=env(); enter_prefix(e); return e

def main():
    successes=[]; terminal_counts={"continue":0,"game_over":0,"progress":0}
    for r in range(64):
        for c in range(64):
            e=fresh_prefix()
            f=click(e,(r,c))
            if f is None:continue
            progressed=int(f.levels_completed)>1 or f.state==GameState.WIN
            if progressed:
                terminal_counts["progress"]+=1
                successes.append([r,c])
            elif f.state==GameState.GAME_OVER:
                terminal_counts["game_over"]+=1
            else:
                terminal_counts["continue"]+=1

    selected=successes[0] if successes else None
    verification=[]
    if selected:
        for _ in range(2):
            e=fresh_prefix();f=click(e,tuple(selected))
            verification.append({
                "level":int(f.levels_completed),"state":str(f.state),
                "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN
            })
    ok=bool(selected and all(x["progressed"] for x in verification))
    out={
        "source_operator_transport_run":35860716478,
        "transported_prefix":[list(x) for x in PREFIX],
        "prefix_length":len(PREFIX),
        "raw_terminal_actions_tested":4096,
        "outcomes":terminal_counts,
        "successful_terminal_actions":successes,
        "selected_terminal_action":selected,
        "program":[list(x) for x in PREFIX]+([selected] if selected else []),
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "status":"PROMOTED" if ok else "RESIDUAL",
        "claim_boundary":"single missing terminal operator search after exact 8/9 operator transport",
    }
    (OUTDIR/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_MISSING_TERMINAL_G2="+out["status"])
if __name__=="__main__":main()
