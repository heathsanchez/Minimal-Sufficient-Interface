from __future__ import annotations

import json
import os
from pathlib import Path

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_panel_correspondence_g2 as g2
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-cross-level-selector-law")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20)

def frame_grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return [[int(v) for v in row] for row in x]

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
        if r0<50 or c1>=31 or h>9 or w>9 or h<5 or w<5:
            continue
        holes=[p for p in singles if r0<=p[0]<=r1 and c0<=p[1]<=c1]
        if not holes:
            continue
        patch=[[grid[r][c] for c in range(c0,c1+1)] for r in range(r0,r1+1)]
        out.append({
            "bbox":[r0,c0,r1,c1],
            "size":int(comp["size"]),
            "holes":[list(x) for x in holes],
            "holes_local":[[x[0]-r0,x[1]-c0] for x in holes],
            "patch":patch,
        })
    out.sort(key=lambda x:x["bbox"][1])
    return out

def right_target_columns(f):
    cols=set()
    rows=set()
    for comp in ab.comps(f):
        if int(comp["size"])!=3 or int(comp["color"]) not in (1,5):
            continue
        cells=sorted(tuple(x) for x in comp["cells"])
        rc=cells[len(cells)//2]
        if rc[1]>=31:
            cols.add(rc[1]); rows.add(rc[0])
    return sorted(rows),sorted(cols)

def level1():
    e=ab.env()
    f=e.reset()
    return e,f

def level2():
    e=ab.env()
    f=ab.enter2(e)
    return e,f

def level3():
    e,ftrace=g3.enter_level3()
    return e,e.observation_space

def inspect(name,f):
    boxes=selector_boxes(f)
    rows,cols=right_target_columns(f)
    return {
        "level":name,
        "levels_completed":int(f.levels_completed),
        "selector_count":len(boxes),
        "singleton_count":len(singleton_points(f)),
        "selectors":boxes,
        "target_rows":rows,
        "target_cols":cols,
        "target_col_count":len(cols),
        "holes_per_selector":[len(x["holes"]) for x in boxes],
    }

def main():
    _,f1=level1()
    _,f2=level2()
    _,f3=level3()
    rows=[inspect("G1",f1),inspect("G2",f2),inspect("G3",f3)]
    out={
        "status":"DIAGNOSTIC",
        "levels":rows,
        "selector_counts":[x["selector_count"] for x in rows],
        "singleton_counts":[x["singleton_count"] for x in rows],
        "target_col_counts":[x["target_col_count"] for x in rows],
        "law_holds":[
            x["singleton_count"]==2*x["selector_count"] and
            x["target_col_count"]==x["singleton_count"]
            for x in rows
        ],
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G1/G2/G3 unsolved starting states reached only by qualified public play; same visual detector at all levels; selector glyph = compact bottom-left color-5 component containing color-0 singleton holes; target columns = centers of right-side size-3 color1/5 components",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_CROSS_LEVEL_SELECTOR_LAW=DIAGNOSTIC")

if __name__=="__main__":
    main()
