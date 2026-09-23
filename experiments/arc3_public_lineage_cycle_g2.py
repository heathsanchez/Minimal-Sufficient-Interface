from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-lineage-cycle-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

# G1 source identity pattern:
# a,b,c,d,e,f,g,h,a
# Strict effect transport found exact G2 realizations for c..h.
# Source-side target probes independently identify distinct witnesses for a,b.
A=(58,46)
B=(58,11)
MID=[(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]
PROGRAM=[A,B,*MID,A]

def env():
    l=logging.getLogger("lineage-cycle");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game unavailable")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def run_once():
    e=env();trace=[]
    for i,rc in enumerate(PROGRAM):
        z=click(e,rc)
        if z is None: return {"progressed":False,"error":"None","trace":trace}
        trace.append({"i":i,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>0 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return {
        "progressed":int(e.observation_space.levels_completed)>0 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "actions":len(trace),
        "trace":trace,
    }

def main():
    trials=[run_once(),run_once()]
    ok=all(x["progressed"] for x in trials)
    out={
        "source_identity_pattern":"a,b,c,d,e,f,g,h,a",
        "program":[list(x) for x in PROGRAM],
        "distinct_preterminal_witnesses":len(set(PROGRAM[:-1])),
        "terminal_returns_to_opening":PROGRAM[-1]==PROGRAM[0],
        "strict_transport_run":35868730738,
        "probe_alignment_run":35861739794,
        "trials":trials,
        "status":"PROMOTED" if ok else "RESIDUAL",
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"lineage-preserving witness transport on exact public tn36 G2",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_LINEAGE_CYCLE_G2="+out["status"])

if __name__=="__main__":
    main()
