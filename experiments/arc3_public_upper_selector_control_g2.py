from __future__ import annotations

import hashlib
import json
import os
from collections import deque
from pathlib import Path

from arcengine import GameState
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-upper-selector-control-g2")).resolve()
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
        rc=comp["cells"][len(comp["cells"])//2]
        if side=="left" and rc[1] < 31: out.append((comp,rc))
        if side=="right" and rc[1] >= 31: out.append((comp,rc))
    return out

def pick_center(comp):
    cells=comp["cells"]
    mr=sum(r for r,c in cells)/len(cells)
    mc=sum(c for r,c in cells)/len(cells)
    return min(cells,key=lambda rc:((rc[0]-mr)**2+(rc[1]-mc)**2,rc))

def selectors(f):
    out=[]
    for comp in ab.comps(f):
        cells=comp["cells"]
        rs=[r for r,c in cells];cs=[c for r,c in cells]
        color=comp["color"]
        if max(rs)>=32: continue
        if color==4 and max(cs)<31:
            out.append(("yellow-left",pick_center(comp)))
        if color==11 and min(cs)>=31:
            out.append(("purple-right",pick_center(comp)))
    # Deduplicate while retaining stable spatial order.
    seen=set();uniq=[]
    for name,rc in sorted(out,key=lambda x:(x[0],x[1])):
        if rc not in seen:
            seen.add(rc);uniq.append((f"{name}:{rc[0]},{rc[1]}",rc))
    return uniq

def enter_selected(e,selector,path=()):
    ab.enter2(e)
    z=ab.click(e,A)
    if z is None: raise RuntimeError("opening A returned None")
    z=ab.click(e,selector)
    if z is None: raise RuntimeError("selector returned None")
    if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
        return e.observation_space
    for name in path:
        z=ab.click(e,dict(CONTROLS)[name])
        if z is None: raise RuntimeError("control returned None")
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e.observation_space

def finish_trial(selector,path):
    e=ab.env();f=enter_selected(e,selector,path)
    trace=[]
    left0=len(blue3_region(f,"left"));right0=len(blue3_region(f,"right"))
    if int(f.levels_completed)>1 or f.state==GameState.WIN:
        return {"progressed":True,"reason":"pre-finish-progress","left":left0,"right":right0,"trace":trace,
                "level":int(f.levels_completed),"state":str(f.state)}
    if f.state==GameState.GAME_OVER:
        return {"progressed":False,"reason":"game-over-before-finish","left":left0,"right":right0,"trace":trace}
    if left0!=0:
        return {"progressed":False,"reason":"left_not_closed","left":left0,"right":right0,"trace":trace}
    tried=set()
    while True:
        rs=blue3_region(e.observation_space,"right")
        if not rs: break
        choices=sorted(rc for _,rc in rs if rc not in tried)
        if not choices:
            return {"progressed":False,"reason":"right_stuck","left":0,"right":len(rs),"trace":trace}
        rc=choices[0];before=len(rs)
        z=ab.click(e,rc);tried.add(rc)
        after=len(blue3_region(z,"right"))
        trace.append({"kind":"right-toggle","rc":list(rc),"before":before,"after":after,
                      "level":int(z.levels_completed),"state":str(z.state)})
        if z.state==GameState.GAME_OVER:
            return {"progressed":False,"reason":"game_over_during_right","left":0,"right":after,"trace":trace}
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
            return {"progressed":True,"reason":"progress-during-right","left":0,"right":after,"trace":trace,
                    "level":int(z.levels_completed),"state":str(z.state)}
    z=ab.click(e,A)
    trace.append({"kind":"terminal","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})
    return {"progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,
            "reason":"terminal","left":len(blue3_region(z,"left")),
            "right":len(blue3_region(z,"right")),"trace":trace,
            "level":int(z.levels_completed),"state":str(z.state)}

def search_selector(selector_name,selector):
    e=ab.env();root=enter_selected(e,selector,())
    initial={"left":len(blue3_region(root,"left")),"right":len(blue3_region(root,"right")),
             "level":int(root.levels_completed),"state":str(root.state),"hash":bh(root)}
    if int(root.levels_completed)>1 or root.state==GameState.WIN:
        return {"selector":selector_name,"selector_rc":list(selector),"initial":initial,
                "status":"DIRECT_PROGRESS","best":{"left":initial["left"],"path":[],"right":initial["right"]},
                "unique_states":1,"states":[]}
    if root.state==GameState.GAME_OVER:
        return {"selector":selector_name,"selector_rc":list(selector),"initial":initial,
                "status":"GAME_OVER","best":{"left":initial["left"],"path":[],"right":initial["right"]},
                "unique_states":1,"states":[]}

    q=deque([()])
    seen={bh(root):()}
    states=[]
    best={"left":initial["left"],"path":[],"right":initial["right"],"hash":bh(root)}
    closures=[]
    while q and len(seen)<=MAX_STATES:
        path=q.popleft()
        f=enter_selected(e,selector,path)
        left=len(blue3_region(f,"left"));right=len(blue3_region(f,"right"))
        row={"path":list(path),"depth":len(path),"left_blue3":left,"right_blue3":right,"hash":bh(f)}
        states.append(row)
        if (left,len(path)) < (best["left"],len(best["path"])):
            best={"left":left,"path":list(path),"right":right,"hash":bh(f)}
        if left==0:
            closures.append(row)
            trial=finish_trial(selector,path)
            if trial["progressed"]:
                verify=[trial,finish_trial(selector,path)]
                if all(x["progressed"] for x in verify):
                    return {"selector":selector_name,"selector_rc":list(selector),"initial":initial,
                            "status":"PROMOTED","best":best,"closure":row,"control_path":list(path),
                            "verification":verify,"unique_states":len(seen),"states":states}
        if len(path)>=MAX_DEPTH: continue
        for name,rc in CONTROLS:
            f0=enter_selected(e,selector,path)
            if int(f0.levels_completed)>1 or f0.state in (GameState.WIN,GameState.GAME_OVER): continue
            z=ab.click(e,rc)
            if z is None or z.state==GameState.GAME_OVER: continue
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                verify=[finish_trial(selector,path+(name,)),finish_trial(selector,path+(name,))]
                if all(x["progressed"] for x in verify):
                    return {"selector":selector_name,"selector_rc":list(selector),"initial":initial,
                            "status":"PROMOTED","best":best,"control_path":list(path+(name,)),
                            "verification":verify,"unique_states":len(seen),"states":states}
            h=bh(z)
            if h not in seen:
                np=path+(name,);seen[h]=np;q.append(np)
    return {"selector":selector_name,"selector_rc":list(selector),"initial":initial,
            "status":"RESIDUAL","best":best,"closures":closures,
            "unique_states":len(seen),"states":states}

def main():
    e=ab.env();start=ab.enter2(e)
    sels=selectors(start)
    if not sels:
        raise AssertionError("no upper selectors found")
    results=[]
    for name,rc in sels:
        r=search_selector(name,rc);results.append(r)
        if r["status"]=="PROMOTED":
            out={"status":"PROMOTED","selectors":[{"name":n,"rc":list(c)} for n,c in sels],
                 "selected":r,"results":results,"max_depth":MAX_DEPTH,"max_states":MAX_STATES,
                 "max_level2_actions":1+1+MAX_DEPTH+24+1,
                 "model_calls":0,"source_inspection":False,
                 "claim_boundary":"upper-object selector after opening A, then exact-screen B/C control closure, direct right-panel closure, and terminal on exact public tn36 G2"}
            (OUT/"result.json").write_text(json.dumps(out,indent=2))
            print(json.dumps(out,indent=2));print("ARC3_PUBLIC_UPPER_SELECTOR_CONTROL_G2=PROMOTED");return
    best=min((r["best"]["left"],len(r["best"]["path"]),r["selector"],r["best"]) for r in results)
    out={"status":"RESIDUAL","selectors":[{"name":n,"rc":list(c)} for n,c in sels],
         "results":results,"global_best":{"selector":best[2],**best[3]},
         "max_depth":MAX_DEPTH,"max_states":MAX_STATES,
         "max_level2_actions":1+1+MAX_DEPTH+24+1,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"finite upper-object-selector-conditioned exact-screen B/C control automata on exact public tn36 G2; residual does not exclude other selector timing, other bottom action classes, or hidden same-screen states"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_UPPER_SELECTOR_CONTROL_G2=RESIDUAL")

if __name__=="__main__": main()
