from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-selector-hole-label-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
GENS=[
    ("none",[]),
    ("B",[("B",B)]),
    ("BD",[("B",B),("D",D)]),
    ("ABCDE",[("A",A),("B",B),("C",C),("D",D),("E",E)]),
]

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def enter_g3(prefix):
    e,_=g3.enter_level3()
    for _,rc in prefix:
        z=ab.click(e,rc)
        if protected(z)!="CONTINUE":
            break
    return e

def source_bits(f):
    rows,src,targets=sem.semantic_surface(f)
    return rows,list(src),targets

def singleton_points(f):
    pts=[]
    for comp in ab.comps(f):
        if int(comp["color"])==0 and int(comp["size"])==1:
            cells=[tuple(x) for x in comp["cells"]]
            if len(cells)==1 and cells[0][1]<31:
                pts.append(cells[0])
    return sorted(pts)

def selector_boxes(f):
    singles=singleton_points(f)
    boxes=[]
    for comp in ab.comps(f):
        if int(comp["color"])!=5:
            continue
        cells=[tuple(x) for x in comp["cells"]]
        rs=[r for r,c in cells]; cs=[c for r,c in cells]
        r0,c0,r1,c1=min(rs),min(cs),max(rs),max(cs)
        h=r1-r0+1; w=c1-c0+1
        if r0<50 or c1>=31 or h>9 or w>9 or h<5 or w<5:
            continue
        holes=sorted([p for p in singles if r0<=p[0]<=r1 and c0<=p[1]<=c1])
        if len(holes)!=2:
            continue
        boxes.append({
            "bbox":[r0,c0,r1,c1],
            "holes":holes,
            "holes_local":[(p[0]-r0,p[1]-c0) for p in holes],
        })
    boxes.sort(key=lambda x:x["bbox"][1])
    return boxes

def causal_box_labels():
    base=enter_g3([])
    boxes=selector_boxes(base.observation_space)
    if len(boxes)!=3:
        raise AssertionError(boxes)
    out=[]
    for box in boxes:
        e=enter_g3([])
        hole=box["holes"][0]
        ab.click(e,hole)
        rows,src,_=source_bits(e.observation_space)
        active=[i for i,b in enumerate(src) if b]
        if len(active)!=2:
            raise AssertionError((box,src))
        out.append({
            "bbox":box["bbox"],
            "holes":[list(x) for x in box["holes"]],
            "holes_local":[list(x) for x in box["holes_local"]],
            "active_rows":active,
        })
    return out

def columns_for_assignment(boxes,assignment,reverse=False,complement=False):
    cols=[]
    for i,box in enumerate(boxes):
        labels=list(box["active_rows"])
        if assignment[i]:
            labels=list(reversed(labels))
        for lab in labels:
            col=[1 if r==lab else 0 for r in range(6)]
            if complement:
                col=[1-x for x in col]
            cols.append(col)
    if reverse:
        cols=list(reversed(cols))
    return cols

def write_matrix(e,cols):
    if len(cols)!=6:
        raise AssertionError(len(cols))
    M=[[cols[j][i] for j in range(6)] for i in range(6)]
    rows,src,targets=source_bits(e.observation_space)
    actions=[]
    for i in range(6):
        for j in range(6):
            want=M[i][j]
            cur=sem.bit(targets[i][j]["color"])
            if cur==want:
                continue
            rc=tuple(targets[i][j]["rc"])
            z=ab.click(e,rc)
            actions.append({"i":i,"j":j,"rc":list(rc),"want":want})
            if protected(z)!="CONTINUE":
                return actions,M
    return actions,M

def run_variant(prefix,assignment,reverse,complement,boxes):
    cols=columns_for_assignment(boxes,assignment,reverse,complement)
    e=enter_g3(prefix)
    actions,M=write_matrix(e,cols)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "assignment":list(assignment),
        "reverse":reverse,
        "complement":complement,
        "columns":cols,
        "matrix":M,
        "write_count":len(actions),
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def main():
    boxes=causal_box_labels()
    tested=[]
    selected=None
    verification=[]

    for gen_name,prefix in GENS:
        for assignment in itertools.product((0,1),repeat=3):
            for reverse in (False,True):
                for complement in (False,True):
                    row=run_variant(prefix,assignment,reverse,complement,boxes)
                    tested.append({
                        "generation":gen_name,
                        "assignment":row["assignment"],
                        "reverse":reverse,
                        "complement":complement,
                        "columns":row["columns"],
                        "write_count":row["write_count"],
                        "progressed":row["progressed"],
                        "outcome":row["outcome"],
                    })
                    if row["progressed"]:
                        vv=[run_variant(prefix,assignment,reverse,complement,boxes),run_variant(prefix,assignment,reverse,complement,boxes)]
                        if all(x["progressed"] for x in vv):
                            selected={
                                "generation":gen_name,
                                "assignment":list(assignment),
                                "reverse":reverse,
                                "complement":complement,
                                "columns":row["columns"],
                                "write_count":row["write_count"],
                            }
                            verification=vv
                            break
                if selected: break
            if selected: break
        if selected: break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "selector_boxes":boxes,
        "hypothesis":"each of the three transported G3 selector glyphs contains two holes that label the two active source rows selected by that glyph; the six target columns are those six endpoint labels in spatial glyph/hole order",
        "generation_histories":[x[0] for x in GENS],
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; three selector glyphs and their two holes are observed; each glyph is causally labeled by the two active source rows reached when clicked; only the 2^3 within-glyph endpoint assignments are tested, with optional global column reversal and direct/complement convention, after none/B/BD/ABCDE generation histories; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SELECTOR_HOLE_LABEL_G3="+status)

if __name__=="__main__":
    main()
