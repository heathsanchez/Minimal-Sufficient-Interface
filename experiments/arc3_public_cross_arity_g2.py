from __future__ import annotations
import json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-cross-arity-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
SETUP=[(58,46),(58,11)]
HROWS=[33,39,45]
VROWS=[36,42,48]
COLS=[39,44,49,54]

def env():
    l=logging.getLogger("cross-arity");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game unavailable")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter2(e):
    for rc in G1:
        z=click(e,rc)
        if z is None: raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("G1 drift")

def replay_preterminal(e,hrow,vrow):
    z=e.reset()
    if int(z.levels_completed)==0: enter2(e)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("level2 drift")
    prog=SETUP+[(hrow,c) for c in COLS]+[(vrow,c) for c in COLS]
    trace=[]
    for rc in prog:
        z=click(e,rc)
        trace.append({"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return prog,trace,e.observation_space

def verify(program):
    outs=[]
    for _ in range(2):
        e=env();enter2(e)
        tr=[]
        for rc in program:
            z=click(e,tuple(rc));tr.append({"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
            if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
        outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                     "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":tr})
    return outs

def main():
    e=env();enter2(e)
    attempts=[];selected=None;verification=[]
    for hr in HROWS:
      for vr in VROWS:
        pre,trace,f=replay_preterminal(e,hr,vr)
        if int(f.levels_completed)>1 or f.state==GameState.WIN:
            vv=verify([list(x) for x in pre])
            attempts.append({"hrow":hr,"vrow":vr,"terminal":None,"direct":True})
            if all(x["progressed"] for x in vv):
                selected=[list(x) for x in pre];verification=vv;break
        if f.state==GameState.GAME_OVER:
            attempts.append({"hrow":hr,"vrow":vr,"terminal":None,"direct":False,"game_over":True});continue
        # Source closes with a terminal click. Search it only after the arity-4 constructor is complete.
        tested=0;found=None
        # Highest-priority lineage suffixes first.
        order=[SETUP[0],SETUP[1]]
        seen=set(order)
        order += [(r,c) for r in range(64) for c in range(64) if (r,c) not in seen]
        for tc in order:
            pre2,_,f2=replay_preterminal(e,hr,vr)
            z=click(e,tc);tested+=1
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                full=[list(x) for x in pre2]+[list(tc)]
                vv=verify(full)
                if all(x["progressed"] for x in vv):
                    found=list(tc);selected=full;verification=vv;break
        attempts.append({"hrow":hr,"vrow":vr,"terminal":found,"direct":False,"tested_terminal":tested})
        if selected:break
      if selected:break

    out={
      "source_arity":3,
      "target_arity":4,
      "schema":"2 setup + one H row across all 4 columns + one V row across all 4 columns + terminal",
      "setup":[list(x) for x in SETUP],"hrows":HROWS,"vrows":VROWS,"cols":COLS,
      "attempts":attempts,"selected_program":selected,"verification":verification,
      "status":"PROMOTED" if selected else "RESIDUAL","model_calls":0,"source_inspection":False,
      "claim_boundary":"black-box cross-arity constructor lift from public tn36 G1 arity-3 to G2 arity-4"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_CROSS_ARITY_G2="+out["status"])

if __name__=="__main__":main()
