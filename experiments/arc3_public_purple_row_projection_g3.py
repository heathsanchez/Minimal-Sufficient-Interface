from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_panel_correspondence_g2 as g2
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-purple-row-projection-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def purple_target_rows(f):
    comps=ab.comps(f)
    # Upper-right checkerboard support gives the coarse row origin.
    bg=[x for x in comps if x["color"] in (4,5)
        and max(c for r,c in x["cells"])>=32
        and max(r for r,c in x["cells"])<32
        and x["size"]>=8]
    if not bg:
        raise AssertionError("no upper-right checkerboard support")
    top=min(min(r for r,c in x["cells"]) for x in bg)

    purple=[x for x in comps if x["color"]==11
            and min(c for r,c in x["cells"])>=32
            and max(r for r,c in x["cells"])<32]
    if len(purple)!=2:
        raise AssertionError(f"expected two upper-right purple components, got {len(purple)}")

    anchors=[]
    bboxes=[]
    for x in purple:
        rs=[r for r,c in x["cells"]];cs=[c for r,c in x["cells"]]
        r0=min(rs);r1=max(rs);c0=min(cs);c1=max(cs)
        idx=(r0-top)//4
        anchors.append(idx)
        bboxes.append([r0,c0,r1,c1])
    return sorted(anchors),top,bboxes


def right_rows(f):
    left,right=g3.size3_by_side(f)
    R=defaultdict(list)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(R)
    if len(rows)!=6:
        raise AssertionError(f"expected six target rows, got {rows}")
    for r in rows:
        R[r]=sorted(R[r],key=lambda x:x["rc"][1])
    return rows,R


def set_target_rows(e,desired_rows,trace,phase):
    rows,R=right_rows(e.observation_space)
    writes=[]
    for i,r in enumerate(rows):
        want=5 if i in desired_rows else 1
        for x in R[r]:
            if x["color"]==want:
                continue
            rc=tuple(x["rc"])
            z=ab.click(e,rc)
            writes.append({"row_index":i,"rc":list(rc),"before":x["color"],"want":want})
            trace.append({"phase":phase,"row_index":i,"rc":list(rc),
                          "level":int(z.levels_completed),"state":str(z.state)})
            if z.state in (GameState.WIN,GameState.GAME_OVER):
                break
        if e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return writes


def run_g2_control():
    e=ab.env();ab.enter2(e);trace=[]
    for name,rc in [("A",A),("B",B),("C",C)]:
        z=ab.click(e,rc)
        trace.append({"phase":"g2-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
    anchors,top,bboxes=purple_target_rows(e.observation_space)
    writes=set_target_rows(e,anchors,trace,"g2-purple-row-write")
    z=ab.click(e,A)
    trace.append({"phase":"g2-submit","rc":list(A),
                  "level":int(z.levels_completed),"state":str(z.state)})
    return {
        "anchors":anchors,"checkerboard_top":top,"purple_bboxes":bboxes,
        "writes":writes,
        "progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,
        "level":int(z.levels_completed),"state":str(z.state),"trace":trace
    }


def run_g3(prefix):
    e,trace=g3.enter_level3()
    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"phase":"g3-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "anchors":None,"writes":[],
                "progressed":int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),
                "early":True,"trace":trace
            }

    anchors,top,bboxes=purple_target_rows(e.observation_space)
    writes=set_target_rows(e,anchors,trace,"g3-purple-row-write")

    if int(e.observation_space.levels_completed)==2 and e.observation_space.state==GameState.NOT_FINISHED:
        z=ab.click(e,A)
        trace.append({"phase":"g3-submit","rc":list(A),
                      "level":int(z.levels_completed),"state":str(z.state)})

    return {
        "anchors":anchors,"checkerboard_top":top,"purple_bboxes":bboxes,
        "writes":writes,
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace
    }


def main():
    control=run_g2_control()
    if not control["progressed"]:
        raise AssertionError(f"G2 control failed: {control}")

    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    variants=[]
    selected=None
    verification=[]
    for i,prefix in enumerate(prefixes):
        row=run_g3(prefix)
        row["variant"]=i
        row["prefix"]=[{"name":n,"rc":list(rc)} for n,rc in prefix]
        variants.append(row)
        if row.get("progressed"):
            vv=[run_g3(prefix),run_g3(prefix)]
            if all(x.get("progressed") for x in vv):
                selected={
                    "variant":i,
                    "prefix":row["prefix"],
                    "anchors":row.get("anchors"),
                    "writes":row.get("writes")
                }
                verification=vv
                break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "hypothesis":"the writable panel rows are the projection of the two purple target-component coarse-row anchors; G2 copy-success is a special case of this target-derived row law",
        "g2_control":{k:v for k,v in control.items() if k!="trace"},
        "variants":variants,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 black-box geometry; upper-right color-11 components only; coarse row anchor derived from component minimum row relative to observed checkerboard origin; target size-3 panel rows gray iff their row index is an anchor; G2 ABC control and G3 A/B/C/D/E prefixes; terminal A; two-replay verification"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PURPLE_ROW_PROJECTION_G3="+status)

if __name__=="__main__":
    main()
