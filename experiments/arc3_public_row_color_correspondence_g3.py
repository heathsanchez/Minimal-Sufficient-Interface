from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-row-color-correspondence-g3"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def row_panels(f):
    left,right=g3.size3_by_side(f)
    L=defaultdict(list); R=defaultdict(list)
    for x in left: L[x["rc"][0]].append(x)
    for x in right: R[x["rc"][0]].append(x)
    rows=sorted(set(L)&set(R))
    if len(rows)!=6:
        raise AssertionError(f"expected 6 shared rows, got {rows}")
    for r in rows:
        L[r]=sorted(L[r],key=lambda x:x["rc"][1])
        R[r]=sorted(R[r],key=lambda x:x["rc"][1])
        if len(L[r])!=4 or len(R[r])!=6:
            raise AssertionError(f"expected G3 row arity 4->6 on {r}, got {len(L[r])}->{len(R[r])}")
        colors={x["color"] for x in L[r]}
        if len(colors)!=1:
            raise AssertionError(f"source row {r} is not monochromatic: {colors}")
    return rows,L,R


def run_variant(prefix):
    e,trace=g3.enter_level3()

    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({
            "phase":"g3-prefix","name":name,"rc":list(rc),
            "level":int(z.levels_completed),"state":str(z.state)
        })
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "progressed":int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),
                "state":str(z.state),
                "early":True,
                "trace":trace,
            }

    rows,L,R=row_panels(e.observation_space)
    before={}
    actions=[]

    for r in rows:
        want=L[r][0]["color"]
        before[str(r)]={
            "source_color":want,
            "left":[x["color"] for x in L[r]],
            "right":[x["color"] for x in R[r]],
            "right_rc":[list(x["rc"]) for x in R[r]],
        }
        for tgt in R[r]:
            if tgt["color"]==want:
                continue
            rc=tuple(tgt["rc"])
            z=ab.click(e,rc)
            actions.append({"row":r,"rc":list(rc),"before":tgt["color"],"want":want})
            trace.append({
                "phase":"g3-row-color-write","row":r,"rc":list(rc),
                "level":int(z.levels_completed),"state":str(z.state)
            })
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                break
        if int(e.observation_space.levels_completed)>2 or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    remaining=None
    after=None
    if e.observation_space.state==GameState.NOT_FINISHED:
        rows2,L2,R2=row_panels(e.observation_space)
        remaining=0
        after={}
        for r in rows2:
            want=L2[r][0]["color"]
            rem=sum(1 for x in R2[r] if x["color"]!=want)
            remaining+=rem
            after[str(r)]={
                "source_color":want,
                "right":[x["color"] for x in R2[r]],
                "remaining":rem,
            }
        if remaining!=0:
            raise AssertionError(f"row-color write incomplete: {remaining}")

        z=ab.click(e,A)
        trace.append({
            "phase":"g3-submit","name":"A","rc":list(A),
            "level":int(z.levels_completed),"state":str(z.state)
        })

    return {
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "write_count":len(actions),
        "remaining":remaining,
        "before":before,
        "after":after,
        "actions":actions,
        "trace":trace,
    }


def main():
    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    variants=[]
    selected=None
    verification=[]

    for i,prefix in enumerate(prefixes):
        row=run_variant(prefix)
        row["variant"]=i
        row["prefix"]=[{"name":n,"rc":list(rc)} for n,rc in prefix]
        variants.append(row)
        if row.get("progressed"):
            vv=[run_variant(prefix),run_variant(prefix)]
            if all(x.get("progressed") for x in vv):
                selected={
                    "variant":i,
                    "prefix":row["prefix"],
                    "write_count":row.get("write_count"),
                }
                verification=vv
                break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_embedding_head":"3b28ff619eb413a7512e788e6b5c55edd0414853",
        "parent_embedding_run":35929337801,
        "hypothesis":"panel correspondence is arity-invariant at row level: each monochromatic source row specifies the color of every writable target bar in that row",
        "variants":variants,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36 G3; qualified G2 entry; source rows must be observed monochromatic 4-bar rows and target rows observed 6-bar rows; all target bars in each row are written to the source-row color; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ROW_COLOR_CORRESPONDENCE_G3="+status)


if __name__=="__main__":
    main()
