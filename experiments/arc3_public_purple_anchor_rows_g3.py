from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-purple-anchor-rows-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=g3.A
KNOWN=g3.KNOWN


def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)


def target_rows(f):
    left,right=g3.panel_groups(f)
    R=defaultdict(list)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(R)
    if len(rows)!=6:return None
    out=[]
    for r in rows:
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(q)!=6:return None
        out.append(q)
    return rows,out


def purple_anchor_rows(f):
    anchors=[]
    evidence=[]
    for comp in g3.ab.comps(f):
        if comp["color"]!=11:continue
        cells=comp["cells"]
        rs=[r for r,c in cells]; cs=[c for r,c in cells]
        if max(rs)>=32 or min(cs)<32:continue
        minr=min(rs)
        cell_row=(minr-4)//4
        evidence.append({
            "size":len(cells),
            "bbox":[min(rs),min(cs),max(rs),max(cs)],
            "anchor_checker_row":cell_row,
        })
        anchors.append(cell_row)
    anchors=sorted(set(anchors))
    return anchors,evidence


def apply(prefix_len):
    e=g3.make_g3()
    start=int(e.observation_space.levels_completed)
    trace=[]

    for name,rc in KNOWN[:prefix_len]:
        z=g3.ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "prefix_len":prefix_len,
                "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                "early":True,"trace":trace,
            }

    surf=target_rows(e.observation_space)
    if surf is None:
        return {"prefix_len":prefix_len,"progressed":False,"reason":"target_surface"}
    rows,tgt=surf
    anchors,anchor_evidence=purple_anchor_rows(e.observation_space)
    if len(anchors)!=2 or any(a<0 or a>=6 for a in anchors):
        return {"prefix_len":prefix_len,"progressed":False,"reason":"purple_anchor_arity",
                "anchors":anchors,"anchor_evidence":anchor_evidence}

    writes=[]
    for i,row in enumerate(tgt):
        want=1 if i in anchors else 0
        for t in row:
            if bit(t)!=want:
                rc=tuple(t["rc"])
                z=g3.ab.click(e,rc)
                writes.append(list(rc))
                trace.append({"name":"purple-anchor-row-write","rc":list(rc),
                              "level":int(z.levels_completed),"state":str(z.state)})
                if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
                    break
        if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
        trace.append({"name":"terminal:A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})

    return {
        "prefix_len":prefix_len,
        "anchors":anchors,
        "anchor_evidence":anchor_evidence,
        "target_rows":rows,
        "writes":writes,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace,
    }


def verify(k):
    return [apply(k),apply(k)]


def main():
    variants=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
        row=apply(k)
        variants.append({x:y for x,y in row.items() if x!="trace"})
        if row.get("progressed"):
            vv=verify(k)
            if all(x.get("progressed") for x in vv):
                selected={
                    "prefix_len":k,
                    "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                    "anchors":row.get("anchors"),
                    "anchor_evidence":row.get("anchor_evidence"),
                    "writes":row.get("writes"),
                }
                verification=vv
                break

    out={
        "status":"PROMOTED" if selected else "RESIDUAL",
        "training_consistency":"Solved G2 target gray rows are exactly checker-row anchors 0 and 5 of its two upper-right purple components.",
        "hypothesis":"G3 target rows are selected directly by the checker-row anchors of the two observed upper-right purple components; selected rows are gray across all writable columns.",
        "variants":variants,
        "selected":selected,
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1/G2; use only the two upper-right purple connected components, map each minimum physical row into its observed 4-cell checker row, gray the corresponding entire writable target rows, terminal A, verify twice"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PURPLE_ANCHOR_ROWS_G3="+out["status"])


if __name__=="__main__":
    main()
