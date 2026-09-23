from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-rearm-c-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46)
B=(58,11)
C=(58,20)
D=(58,22)
E=(55,20)
BUNDLE=(54,17)
REC=(2,20)

MAX_CYCLES=8

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

def candidate_actions(f):
    rows=[]
    # Known public control/probe coordinates retained as named representatives.
    for name,rc in [("A",A),("B",B),("C",C),("D",D),("E",E),("BUNDLE",BUNDLE),("REC",REC)]:
        rows.append((name,rc))
    # Add one representative for each compact visible upper selector or bottom control component.
    for i,comp in enumerate(ab.comps(f)):
        cells=comp["cells"]
        rs=[r for r,c in cells];cs=[c for r,c in cells]
        size=len(cells);color=comp["color"]
        upper=(max(rs)<32 and color in (4,11))
        bottom=(max(rs)>=52 and size<=200)
        if not (upper or bottom): continue
        rc=pick_center(comp)
        rows.append((f"comp:{i}:color{color}:size{size}",rc))
    # Deduplicate coordinates deterministically.
    out=[];seen=set()
    for name,rc in rows:
        if rc in seen: continue
        seen.add(rc);out.append((name,rc))
    return out[:64]

def replay(prefix):
    e=ab.env();ab.enter2(e)
    trace=[]
    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"left":len(blue3_region(z,"left")),
                      "right":len(blue3_region(z,"right")),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e,trace

def score(prefix):
    e,trace=replay(prefix)
    f=e.observation_space
    return {
        "left":len(blue3_region(f,"left")),
        "right":len(blue3_region(f,"right")),
        "level":int(f.levels_completed),
        "state":str(f.state),
        "trace":trace,
    }

def finish(prefix):
    e,trace=replay(prefix)
    f=e.observation_space
    if int(f.levels_completed)>1 or f.state==GameState.WIN:
        return {"progressed":True,"trace":trace,"level":int(f.levels_completed),"state":str(f.state)}
    if f.state==GameState.GAME_OVER or len(blue3_region(f,"left"))!=0:
        return {"progressed":False,"trace":trace,"left":len(blue3_region(f,"left")),
                "right":len(blue3_region(f,"right")),"state":str(f.state)}
    tried=set()
    while True:
        rs=blue3_region(e.observation_space,"right")
        if not rs: break
        choices=sorted(rc for _,rc in rs if rc not in tried)
        if not choices:
            return {"progressed":False,"trace":trace,"reason":"right_stuck",
                    "right":len(rs)}
        rc=choices[0];tried.add(rc)
        z=ab.click(e,rc)
        trace.append({"name":"right-toggle","rc":list(rc),
                      "left":len(blue3_region(z,"left")),"right":len(blue3_region(z,"right")),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if z.state==GameState.GAME_OVER:
            return {"progressed":False,"trace":trace,"reason":"right_game_over"}
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
            return {"progressed":True,"trace":trace,"level":int(z.levels_completed),"state":str(z.state)}
    z=ab.click(e,A)
    trace.append({"name":"terminal:A","rc":list(A),
                  "left":len(blue3_region(z,"left")),"right":len(blue3_region(z,"right")),
                  "level":int(z.levels_completed),"state":str(z.state)})
    return {"progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,
            "trace":trace,"level":int(z.levels_completed),"state":str(z.state)}

def main():
    prefix=[("A",A),("C",C)]
    base=score(prefix)
    if base["left"]!=16:
        raise AssertionError(f"expected A,C residual left=16, got {base['left']}")
    cycles=[]
    for cycle in range(MAX_CYCLES):
        e,_=replay(prefix)
        f=e.observation_space
        left0=len(blue3_region(f,"left"))
        if left0==0: break
        candidates=candidate_actions(f)
        tests=[]
        variants=[
            ("candidate-C", lambda n,rc:[(n,rc),("C",C)]),
            ("candidate-B-C", lambda n,rc:[(n,rc),("B",B),("C",C)]),
            ("B-candidate-C", lambda n,rc:[("B",B),(n,rc),("C",C)]),
        ]
        best=None
        for name,rc in candidates:
            for vname,mk in variants:
                suffix=mk(name,rc)
                s=score(prefix+suffix)
                row={"candidate":name,"rc":list(rc),"variant":vname,
                     "left_before":left0,"left_after":s["left"],"right_after":s["right"],
                     "level":s["level"],"state":s["state"]}
                tests.append(row)
                if s["level"]>1 or "WIN" in s["state"]:
                    trial=finish(prefix+suffix)
                    verify=[trial,finish(prefix+suffix)]
                    if all(x["progressed"] for x in verify):
                        out={"status":"PROMOTED","reason":"direct_progress","base":base,
                             "cycles":cycles+[{"cycle":cycle,"tests":tests,"selected":row}],
                             "prefix":[{"name":n,"rc":list(r)} for n,r in prefix+suffix],
                             "verification":verify,"model_calls":0,"source_inspection":False,
                             "claim_boundary":"residual-local semantic-component re-arm search after A,C on exact public tn36 G2"}
                        (OUT/"result.json").write_text(json.dumps(out,indent=2))
                        print(json.dumps(out,indent=2));print("ARC3_PUBLIC_REARM_C_G2=PROMOTED");return
                key=(s["left"],len(suffix),name,vname)
                if best is None or key<best[0]:
                    best=(key,row,suffix)
        improved=best is not None and best[1]["left_after"]<left0
        cycles.append({"cycle":cycle,"left_before":left0,"candidate_count":len(candidates),
                       "tests":tests,"selected":best[1] if best else None,"improved":improved})
        if not improved: break
        prefix+=best[2]
    final=score(prefix)
    if final["left"]==0:
        verify=[finish(prefix),finish(prefix)]
        if all(x["progressed"] for x in verify):
            out={"status":"PROMOTED","reason":"left_closed_then_finish","base":base,
                 "cycles":cycles,"prefix":[{"name":n,"rc":list(r)} for n,r in prefix],
                 "final":final,"verification":verify,"model_calls":0,"source_inspection":False,
                 "claim_boundary":"residual-local semantic-component re-arm search after A,C on exact public tn36 G2"}
            (OUT/"result.json").write_text(json.dumps(out,indent=2))
            print(json.dumps(out,indent=2));print("ARC3_PUBLIC_REARM_C_G2=PROMOTED");return
    out={"status":"RESIDUAL","base":base,"cycles":cycles,
         "prefix":[{"name":n,"rc":list(r)} for n,r in prefix],"final":final,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"finite residual-local candidate→C / candidate→B→C / B→candidate→C consequence atlas over visible semantic selector/control representatives after A,C; no claim outside tested action classes"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_REARM_C_G2=RESIDUAL")

if __name__=="__main__": main()
