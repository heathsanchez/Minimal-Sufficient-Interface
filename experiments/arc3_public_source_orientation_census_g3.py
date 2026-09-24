from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-source-orientation-census-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

def orient(cells):
    rs={r for r,c in cells}
    cs={c for r,c in cells}
    if len(rs)==1 and len(cs)==3:
        return "H"
    if len(rs)==3 and len(cs)==1:
        return "V"
    return "OTHER"

def left_panel(f):
    rows=defaultdict(list)
    for comp in ab.comps(f):
        if comp["size"]!=3 or comp["color"] not in (1,5):
            continue
        cells=sorted(tuple(x) for x in comp["cells"])
        rc=cells[len(cells)//2]
        if rc[1]>=31:
            continue
        rows[rc[0]].append({
            "rc":list(rc),
            "color":comp["color"],
            "orientation":orient(cells),
            "cells":[list(x) for x in cells],
        })
    out=[]
    for r in sorted(rows):
        xs=sorted(rows[r],key=lambda x:x["rc"][1])
        out.append({
            "row":r,
            "colors":[x["color"] for x in xs],
            "orientations":[x["orientation"] for x in xs],
            "centers":[x["rc"] for x in xs],
        })
    return out

def replay(k):
    e,_=g3.enter_level3()
    for _,rc in KNOWN[:k]:
        ab.click(e,rc)
    return e

def main():
    snapshots=[]
    for k in range(6):
        e=replay(k)
        p=left_panel(e.observation_space)
        if len(p)!=6 or any(len(x["orientations"])!=4 for x in p):
            raise AssertionError(f"expected 6x4 left panel at k={k}: {p}")
        snapshots.append({
            "prefix_len":k,
            "prefix":[n for n,_ in KNOWN[:k]],
            "rows":p,
            "orientation_matrix":[x["orientations"] for x in p],
            "color_matrix":[x["colors"] for x in p],
        })

    distinct_orient=[]
    seen=set()
    for x in snapshots:
        key=json.dumps(x["orientation_matrix"],separators=(",",":"))
        if key not in seen:
            seen.add(key)
            distinct_orient.append({"prefix_len":x["prefix_len"],"matrix":x["orientation_matrix"]})

    out={
        "status":"DIAGNOSTIC",
        "parent_automaton_head":"bab0724ebf311692ec7a662ee2bdab62294224c5",
        "parent_automaton_run":35949026198,
        "hypothesis":"G3 4-to-6 lift may be induced by pairwise semantics over four source-bar orientation bits rather than the row-uniform color quotient",
        "snapshots":snapshots,
        "distinct_orientation_states":distinct_orient,
        "distinct_orientation_state_count":len(distinct_orient),
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; classify every observed left size-3 color-1/5 component as horizontal or vertical across canonical prefixes 0..5; diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SOURCE_ORIENTATION_CENSUS_G3=DIAGNOSTIC")

if __name__=="__main__":
    main()
