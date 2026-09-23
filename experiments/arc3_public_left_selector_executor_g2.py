from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from arcengine import GameState
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-left-selector-executor-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46)
C=(58,20)
MAX_CYCLES=8


def bh(f):
    x=ab.grid(f)
    return hashlib.sha256(json.dumps(x,separators=(",",":")).encode()).hexdigest()


def size3_region(f,side,colors=(1,5)):
    out=[]
    for comp in ab.comps(f):
        if comp["color"] not in colors or comp["size"]!=3:
            continue
        rc=comp["cells"][len(comp["cells"])//2]
        if side=="left" and rc[1] < 31: out.append((comp,rc))
        if side=="right" and rc[1] >= 31: out.append((comp,rc))
    return sorted(out,key=lambda x:x[1])


def blue_region(f,side):
    return [(comp,rc) for comp,rc in size3_region(f,side,(1,))]


def replay(prefix):
    e=ab.env();ab.enter2(e);trace=[]
    for name,rc in prefix:
        before=bh(e.observation_space)
        z=ab.click(e,rc)
        trace.append({
            "name":name,"rc":list(rc),
            "visible_changed":bh(z)!=before,
            "left_blue":len(blue_region(z,"left")),
            "right_blue":len(blue_region(z,"right")),
            "level":int(z.levels_completed),"state":str(z.state)
        })
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e,trace


def state(prefix):
    e,trace=replay(prefix);f=e.observation_space
    return {
        "left_blue":len(blue_region(f,"left")),
        "right_blue":len(blue_region(f,"right")),
        "left_all":[list(rc) for _,rc in size3_region(f,"left")],
        "level":int(f.levels_completed),"state":str(f.state),"trace":trace
    }


def finish(prefix):
    e,trace=replay(prefix);f=e.observation_space
    if int(f.levels_completed)>1 or f.state==GameState.WIN:
        return {"progressed":True,"level":int(f.levels_completed),"state":str(f.state),"trace":trace}
    if f.state==GameState.GAME_OVER:
        return {"progressed":False,"state":str(f.state),"trace":trace,"reason":"game_over_before_finish"}
    if len(blue_region(f,"left"))!=0:
        return {"progressed":False,"state":str(f.state),"trace":trace,"reason":"left_not_closed",
                "left_blue":len(blue_region(f,"left"))}

    # Right panel is already known to be directly actionable. Close only still-blue bars.
    tried=set()
    while True:
        rows=blue_region(e.observation_space,"right")
        if not rows: break
        choices=[rc for _,rc in rows if rc not in tried]
        if not choices:
            return {"progressed":False,"trace":trace,"reason":"right_stuck",
                    "right_blue":len(rows)}
        rc=choices[0];tried.add(rc)
        before=bh(e.observation_space)
        z=ab.click(e,rc)
        trace.append({
            "name":"right-direct","rc":list(rc),"visible_changed":bh(z)!=before,
            "left_blue":len(blue_region(z,"left")),"right_blue":len(blue_region(z,"right")),
            "level":int(z.levels_completed),"state":str(z.state)
        })
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
            return {"progressed":True,"level":int(z.levels_completed),"state":str(z.state),"trace":trace}
        if z.state==GameState.GAME_OVER:
            return {"progressed":False,"state":str(z.state),"trace":trace,"reason":"right_game_over"}

    z=ab.click(e,A)
    trace.append({
        "name":"terminal:A","rc":list(A),
        "left_blue":len(blue_region(z,"left")),"right_blue":len(blue_region(z,"right")),
        "level":int(z.levels_completed),"state":str(z.state)
    })
    return {"progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,
            "level":int(z.levels_completed),"state":str(z.state),"trace":trace}


def main():
    # Establish the known one-shot executor residual.
    prefix=[("A",A),("C",C)]
    base=state(prefix)
    if base["left_blue"]!=16 or base["right_blue"]!=24:
        raise AssertionError(f"expected A,C residual 16/24, got {base['left_blue']}/{base['right_blue']}")

    cycles=[]
    for cycle in range(MAX_CYCLES):
        cur=state(prefix)
        left0=cur["left_blue"]
        if left0==0: break

        # Key new test: every individual left-panel size-3 bar identity, including
        # already-gray bars, is treated as a possible no-visible selector.
        selectors=[tuple(rc) for rc in cur["left_all"]]
        tests=[];best=None
        for rc in selectors:
            cand=prefix+[(f"left-selector:{rc[0]},{rc[1]}",rc),("C",C)]
            s=state(cand)
            selector_step=s["trace"][-2]
            row={
                "selector":list(rc),
                "selector_visible_changed":selector_step["visible_changed"],
                "left_before":left0,
                "left_after":s["left_blue"],
                "right_after":s["right_blue"],
                "level":s["level"],"state":s["state"]
            }
            tests.append(row)
            key=(s["left_blue"], int(selector_step["visible_changed"]), rc[0], rc[1])
            if best is None or key<best[0]:
                best=(key,row,cand[len(prefix):])

        improved=best is not None and best[1]["left_after"]<left0
        cycles.append({
            "cycle":cycle,"left_before":left0,"selector_count":len(selectors),
            "tests":tests,"selected":best[1] if best else None,"improved":improved
        })
        if not improved:
            break
        prefix+=best[2]

        # If the selected selector+executor completes the left panel, finish immediately.
        if state(prefix)["left_blue"]==0:
            break

    final=state(prefix)
    verification=[]
    if final["left_blue"]==0:
        verification=[finish(prefix),finish(prefix)]
        if all(x["progressed"] for x in verification):
            out={
                "status":"PROMOTED",
                "base":base,"cycles":cycles,
                "prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
                "final":final,"verification":verification,
                "model_calls":0,"source_inspection":False,
                "claim_boundary":"exact public tn36 G2 recursive left-bar selector -> C executor closure; direct right closure; terminal A; two independent replay verifications"
            }
            (OUT/"result.json").write_text(json.dumps(out,indent=2))
            print(json.dumps(out,indent=2));print("ARC3_PUBLIC_LEFT_SELECTOR_EXECUTOR_G2=PROMOTED");return

    out={
        "status":"RESIDUAL",
        "base":base,"cycles":cycles,
        "prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
        "final":final,"verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"finite exact left-panel selector identity test after A,C; every visible size-3 left bar tested individually as selector immediately followed by C; recursive only on strict left-residual improvement"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_LEFT_SELECTOR_EXECUTOR_G2=RESIDUAL")


if __name__=="__main__": main()
