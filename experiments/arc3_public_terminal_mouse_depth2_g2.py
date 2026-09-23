from __future__ import annotations
import hashlib, json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-terminal-mouse-depth2-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
PRE=[(58,46),(58,46),(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]

def env():
    l=logging.getLogger("mouse-depth2");l.setLevel(logging.WARNING)
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

def bh(f):
    return hashlib.sha256(json.dumps(grid(f),separators=(",",":")).encode()).hexdigest()

def enter_pre(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in PRE:
        z=click(e,rc)
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("pre drift")
    return e.observation_space

def verify(pair):
    out=[]
    for _ in range(2):
        e=env();enter_pre(e)
        trace=[]
        for rc in pair:
            z=click(e,tuple(rc));trace.append({"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
            if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
        out.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                    "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace})
    return out

def main():
    e=env();classes={};first_tested=0
    for r in range(64):
        for c in range(64):
            f=enter_pre(e);h0=bh(f);z=click(e,(r,c));first_tested+=1
            if z is None or z.state==GameState.GAME_OVER:continue
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                vv=verify([[r,c]])
                out={"status":"PROMOTED","selected":[[r,c]],"verification":vv,"first_classes":0,
                     "first_tested":first_tested,"second_tested":0,"model_calls":0,"source_inspection":False}
                (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_TERMINAL_MOUSE_DEPTH2_G2=PROMOTED");return
            h=bh(z)
            if h==h0:continue
            classes.setdefault(h,{"rc":[r,c],"count":0})
            classes[h]["count"]+=1

    second_tested=0;selected=None;ver=[]
    for rec in classes.values():
        a=tuple(rec["rc"])
        for r in range(64):
            for c in range(64):
                enter_pre(e);z1=click(e,a)
                if z1.state==GameState.GAME_OVER:continue
                z2=click(e,(r,c));second_tested+=1
                if z2 is None:continue
                if int(z2.levels_completed)>1 or z2.state==GameState.WIN:
                    pair=[list(a),[r,c]]
                    vv=verify(pair)
                    if all(x["progressed"] for x in vv):
                        selected=pair;ver=vv;break
            if selected:break
        if selected:break

    out={
        "exact_preterminal_program":[list(x) for x in PRE],
        "raw_first_actions":4096,
        "distinct_changed_first_successors":len(classes),
        "first_class_counts":sorted([x["count"] for x in classes.values()],reverse=True),
        "first_tested":first_tested,"second_tested":second_tested,
        "selected":selected,"verification":ver,
        "status":"PROMOTED" if selected else "RESIDUAL",
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"depth-2 mouse terminal synthesis at exact full-effect transported tn36 G2 preterminal state"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_TERMINAL_MOUSE_DEPTH2_G2="+out["status"])

if __name__=="__main__":main()
