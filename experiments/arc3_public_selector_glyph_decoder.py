from __future__ import annotations

import json
import os
from pathlib import Path

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-selector-glyph-decoder")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
G2_GEN=[("A",A),("B",B),("C",C)]
G3_GEN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

def protected(f):
    if int(f.levels_completed)>2 or str(f.state).endswith("WIN"):
        return "PROGRESS"
    if str(f.state).endswith("GAME_OVER"):
        return "GAME_OVER"
    return "CONTINUE"

def frame_grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return [[int(v) for v in row] for row in x]

def source_bits(f):
    from collections import defaultdict
    L=defaultdict(list)
    for comp in ab.comps(f):
        if int(comp["size"])!=3 or int(comp["color"]) not in (1,5):
            continue
        cells=sorted(tuple(x) for x in comp["cells"])
        rc=cells[len(cells)//2]
        if rc[1]<31:
            L[rc[0]].append({"rc":rc,"color":int(comp["color"])})
    rows=sorted(L)
    if len(rows)!=6:
        raise AssertionError(rows)
    src=[]
    for r in rows:
        xs=sorted(L[r],key=lambda x:x["rc"][1])
        colors={x["color"] for x in xs}
        if len(colors)!=1:
            raise AssertionError((r,colors))
        src.append(1 if xs[0]["color"]==5 else 0)
    return rows,src

def singleton_points(f):
    pts=[]
    for comp in ab.comps(f):
        if int(comp["color"])==0 and int(comp["size"])==1:
            cells=[tuple(x) for x in comp["cells"]]
            if len(cells)==1 and cells[0][1]<31:
                pts.append(cells[0])
    return sorted(pts)

def selector_boxes(f):
    out=[]
    grid=frame_grid(f)
    singles=singleton_points(f)
    for comp in ab.comps(f):
        if int(comp["color"])!=5:
            continue
        cells=[tuple(x) for x in comp["cells"]]
        rs=[r for r,c in cells]; cs=[c for r,c in cells]
        r0,c0,r1,c1=min(rs),min(cs),max(rs),max(cs)
        h=r1-r0+1; w=c1-c0+1
        # Selector glyphs are compact bottom-left components containing singleton holes.
        if r0<50 or c1>=31 or h>9 or w>9 or h<5 or w<5:
            continue
        holes=[p for p in singles if r0<=p[0]<=r1 and c0<=p[1]<=c1]
        if not holes:
            continue
        patch=[[grid[r][c] for c in range(c0,c1+1)] for r in range(r0,r1+1)]
        out.append({
            "color":int(comp["color"]),
            "size":int(comp["size"]),
            "bbox":[r0,c0,r1,c1],
            "holes":[list(p) for p in holes],
            "holes_local":[[p[0]-r0,p[1]-c0] for p in holes],
            "patch":patch,
        })
    out.sort(key=lambda x:x["bbox"][1])
    return out

def enter_g2_generated():
    e=ab.env()
    ab.enter2(e)
    for _,rc in G2_GEN:
        ab.click(e,rc)
    return e

def enter_g3_initial():
    e,_=g3.enter_level3()
    return e

def label_boxes(level):
    if level=="g2":
        base=enter_g2_generated()
    else:
        base=enter_g3_initial()
    boxes=selector_boxes(base.observation_space)
    labeled=[]
    for box in boxes:
        hole=tuple(box["holes"][0])
        e=enter_g2_generated() if level=="g2" else enter_g3_initial()
        before=source_bits(e.observation_space)[1]
        z=ab.click(e,hole)
        after=source_bits(e.observation_space)[1]
        row=dict(box)
        row.update({
            "probe_hole":list(hole),
            "before_source":before,
            "after_source":after,
            "outcome":protected(z),
        })
        labeled.append(row)
    return {
        "level":level,
        "base_source":source_bits(base.observation_space)[1],
        "selector_count":len(boxes),
        "singleton_count":len(singleton_points(base.observation_space)),
        "boxes":labeled,
    }

def normalize_patch(patch,bbox):
    # represent each glyph by equality-to-its component color / holes / other.
    return patch

def main():
    g2=label_boxes("g2")
    g3=label_boxes("g3")

    out={
        "status":"DIAGNOSTIC",
        "g2":g2,
        "g3":g3,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36; G2 state is qualified A/B/C source-generation state before target write; G3 state is qualified level-3 initial state; selector glyphs are compact color-5 connected components in the bottom-left control region containing color-0 singleton holes; each glyph is labeled by source predicate after clicking one contained singleton; full local patch and hole coordinates retained",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SELECTOR_GLYPH_DECODER=DIAGNOSTIC")

if __name__=="__main__":
    main()
