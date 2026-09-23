from __future__ import annotations

import hashlib
import json
import os
from collections import deque
from pathlib import Path

from arcengine import GameState
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-control-closure-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46)
B=(58,11)
C=(58,20)
CONTROLS=[("B",B),("C",C)]
MAX_DEPTH=20
MAX_STATES=256

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def bh(f):
    return hashlib.sha256(json.dumps(grid(f),separators=(",",":")).encode()).hexdigest()

def blue3_region(f,side):
    out=[]
    for comp in ab.blue3(f):
        cells=comp["cells"]
        rc=cells[len(cells)//2]
        if side=="left" and rc[1] < 31:
            out.append((comp,rc))
        if side=="right" and rc[1] >= 31:
            out.append((comp,rc))
    return out

def replay(e,path):
    ab.enter2(e)
    z=ab.click(e,A)
    if z is None:raise RuntimeError("opening A returned None")
    for name in path:
        rc=dict(CONTROLS)[name]
        z=ab.click(e,rc)
        if z is None:raise RuntimeError("control returned None")
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e.observation_space

def finish_trial(path):
    e=ab.env();f=replay(e,path)
    trace=[]
    left0=len(blue3_region(f,"left"))
    right0=len(blue3_region(f,"right"))
    if left0!=0:
        return {"progressed":False,"reason":"left_not_closed","left":left0,"right":right0,"trace":trace}
    tried=set()
    while True:
        rs=blue3_region(e.observation_space,"right")
        if not rs:break
        choices=sorted(rc for _,rc in rs if rc not in tried)
        if not choices:
            return {"progressed":False,"reason":"right_stuck","left":0,
                    "right":len(rs),"trace":trace}
        rc=choices[0]
        before=len(rs);z=ab.click(e,rc);tried.add(rc)
        after=len(blue3_region(z,"right"))
        trace.append({"kind":"right-toggle","rc":list(rc),"before":before,"after":after,
                      "level":int(z.levels_completed),"state":str(z.state)})
        if z.state==GameState.GAME_OVER:
            return {"progressed":False,"reason":"game_over_during_right","left":0,
                    "right":after,"trace":trace}
    z=ab.click(e,A)
    trace.append({"kind":"terminal","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})
    return {"progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,
            "reason":"terminal","left":len(blue3_region(z,"left")),
            "right":len(blue3_region(z,"right")),"trace":trace,
            "level":int(z.levels_completed),"state":str(z.state)}

def main():
    e=ab.env()
    root=replay(e,())
    initial_left=len(blue3_region(root,"left"))
    initial_right=len(blue3_region(root,"right"))
    q=deque([()])
    seen={bh(root):()}
    states=[]
    closures=[]
    best={"left":initial_left,"path":[],"right":initial_right,"hash":bh(root)}

    while q and len(seen)<=MAX_STATES:
        path=q.popleft()
        f=replay(e,path)
        left=len(blue3_region(f,"left"));right=len(blue3_region(f,"right"))
        row={"path":list(path),"depth":len(path),"left_blue3":left,"right_blue3":right,
             "hash":bh(f)}
        states.append(row)
        if (left,len(path)) < (best["left"],len(best["path"])):
            best={"left":left,"path":list(path),"right":right,"hash":bh(f)}
        if left==0:
            closures.append(row)
            trial=finish_trial(path)
            if trial["progressed"]:
                verification=[trial,finish_trial(path)]
                if all(x["progressed"] for x in verification):
                    program=[list(A)]+[list(dict(CONTROLS)[x]) for x in path]
                    # Exact direct-right clicks are recorded in the trial trace.
                    out={"status":"PROMOTED","initial":{"left_blue3":initial_left,"right_blue3":initial_right},
                         "control_path":list(path),"control_program":program,
                         "closure":row,"verification":verification,"states":states,
                         "best":best,"model_calls":0,"source_inspection":False,
                         "claim_boundary":"black-box B/C control closure of left operator panel, then direct closure of right operator panel and terminal on exact public tn36 G2"}
                    (OUT/"result.json").write_text(json.dumps(out,indent=2))
                    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_CONTROL_CLOSURE_G2=PROMOTED");return
        if len(path)>=MAX_DEPTH:continue
        for name,rc in CONTROLS:
            f0=replay(e,path)
            z=ab.click(e,rc)
            if z is None or z.state==GameState.GAME_OVER:continue
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                out={"status":"PROMOTED","initial":{"left_blue3":initial_left,"right_blue3":initial_right},
                     "control_path":list(path)+(name,),"direct_progress":True,"states":states,
                     "best":best,"model_calls":0,"source_inspection":False,
                     "claim_boundary":"black-box B/C control transition reaches protected progress on exact public tn36 G2"}
                (OUT/"result.json").write_text(json.dumps(out,indent=2))
                print(json.dumps(out,indent=2));print("ARC3_PUBLIC_CONTROL_CLOSURE_G2=PROMOTED");return
            h=bh(z)
            if h not in seen:
                np=path+(name,);seen[h]=np;q.append(np)

    out={"status":"RESIDUAL","initial":{"left_blue3":initial_left,"right_blue3":initial_right},
         "unique_control_states":len(seen),"states_expanded":len(states),
         "closures":closures,"best":best,"max_depth":MAX_DEPTH,"max_states":MAX_STATES,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"exact-screen quotient of B/C control automaton after opening A on public tn36 G2; residual does not exclude hidden same-screen control states"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_CONTROL_CLOSURE_G2=RESIDUAL")

if __name__=="__main__":main()
