from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-row-color-broadcast-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def panel_rows(f):
    left,right=g3.size3_by_side(f)
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    return L,R


def apply_row_broadcast(e,trace):
    L,R=panel_rows(e.observation_space)
    if sorted(L) != sorted(R):
        raise AssertionError(f"row mismatch {sorted(L)} vs {sorted(R)}")

    row_targets={}
    for r in sorted(L):
        colors={x["color"] for x in L[r]}
        if len(colors)!=1:
            raise AssertionError(f"source row {r} not uniform: {sorted(colors)}")
        row_targets[r]=next(iter(colors))

    actions=[]
    before={}
    for r in sorted(R):
        want=row_targets[r]
        vals=sorted(R[r],key=lambda x:x["rc"][1])
        before[str(r)]={
            "want":want,
            "coords":[list(x["rc"]) for x in vals],
            "colors":[x["color"] for x in vals],
        }
        for x in vals:
            if x["color"]==want:
                continue
            rc=tuple(x["rc"])
            z=ab.click(e,rc)
            actions.append({"rc":list(rc),"row":r,"before":x["color"],"want":want})
            trace.append({"phase":"g3-row-broadcast","rc":list(rc),
                          "level":int(z.levels_completed),"state":str(z.state)})
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                break

    L2,R2=panel_rows(e.observation_space)
    remaining=0
    for r in sorted(L2):
        colors={x["color"] for x in L2[r]}
        if len(colors)!=1:
            remaining+=999
            continue
        want=next(iter(colors))
        remaining+=sum(1 for x in R2[r] if x["color"]!=want)

    return {
        "source_widths":{str(r):len(L[r]) for r in sorted(L)},
        "target_widths":{str(r):len(R[r]) for r in sorted(R)},
        "row_targets":{str(k):v for k,v in row_targets.items()},
        "right_before":before,
        "actions":actions,
        "remaining":remaining,
    }


def run_variant(prefix,submit=True):
    e,trace=g3.enter_level3()

    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"phase":"g3-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "progressed":int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),
                "early":True,"trace":trace,
            }

    try:
        broadcast=apply_row_broadcast(e,trace)
    except AssertionError as ex:
        return {
            "progressed":False,
            "reason":"row_broadcast_precondition_failed",
            "error":str(ex),
            "trace":trace,
        }

    if broadcast["remaining"]!=0:
        return {
            "progressed":False,
            "reason":"row_broadcast_incomplete",
            "broadcast":broadcast,
            "trace":trace,
        }

    if submit and e.observation_space.state==GameState.NOT_FINISHED:
        z=ab.click(e,A)
        trace.append({"phase":"g3-submit","name":"A","rc":list(A),
                      "level":int(z.levels_completed),"state":str(z.state)})

    return {
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "broadcast":broadcast,
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
                    "broadcast":row.get("broadcast"),
                }
                verification=vv
                break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_g2_run":35926523909,
        "parent_g3_residual_run":35927057975,
        "hypothesis":"panel correspondence is row-label correspondence: each source row is a uniform color label that should be broadcast across every writable target bar in the same row, independent of target width",
        "variants":variants,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1/G2 replay; source rows must be observed uniform color-1/5 size-3 bars; target rows must share row coordinates but may have arbitrary width; only mismatching right bars are toggled; submit A verified twice on progress",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ROW_COLOR_BROADCAST_G3="+status)


if __name__=="__main__":
    main()
