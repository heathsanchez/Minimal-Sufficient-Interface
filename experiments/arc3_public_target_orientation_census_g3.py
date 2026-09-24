from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-target-orientation-census-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

def orient(cells):
    rs={r for r,c in cells}; cs={c for r,c in cells}
    if len(rs)==1 and len(cs)==3: return "H"
    if len(rs)==3 and len(cs)==1: return "V"
    return "OTHER"

def panels(f):
    left=defaultdict(list); right=defaultdict(list)
    for comp in ab.comps(f):
        if comp["size"]!=3 or comp["color"] not in (1,5):
            continue
        cells=sorted(tuple(x) for x in comp["cells"])
        rc=cells[len(cells)//2]
        row={"rc":list(rc),"color":comp["color"],"orientation":orient(cells)}
        (left if rc[1]<31 else right)[rc[0]].append(row)
    def norm(D):
        out=[]
        for r in sorted(D):
            xs=sorted(D[r],key=lambda x:x["rc"][1])
            out.append({
                "row":r,
                "centers":[x["rc"] for x in xs],
                "colors":[x["color"] for x in xs],
                "orientations":[x["orientation"] for x in xs],
            })
        return out
    return norm(left),norm(right)

def replay(k):
    e,_=g3.enter_level3()
    for _,rc in KNOWN[:k]:
        ab.click(e,rc)
    return e

def main():
    snaps=[]
    for k in range(6):
        e=replay(k)
        left,right=panels(e.observation_space)
        if len(left)!=6 or len(right)!=6:
            raise AssertionError((k,len(left),len(right)))
        if any(len(x["orientations"])!=4 for x in left): raise AssertionError(("left",k,left))
        if any(len(x["orientations"])!=6 for x in right): raise AssertionError(("right",k,right))
        R=[x["orientations"] for x in right]
        cols=[[R[i][j] for i in range(6)] for j in range(6)]
        snaps.append({
            "prefix_len":k,
            "prefix":[n for n,_ in KNOWN[:k]],
            "left_orientation_matrix":[x["orientations"] for x in left],
            "right_orientation_matrix":R,
            "right_column_signatures":cols,
            "right_centers":[x["centers"] for x in right],
        })
    distinct_right={json.dumps(x["right_orientation_matrix"],separators=(",",":")) for x in snaps}
    distinct_cols={json.dumps(x["right_column_signatures"],separators=(",",":")) for x in snaps}
    out={
        "status":"DIAGNOSTIC",
        "parent_source_orientation_head":"9f9ae1d8715187ff49a9c5b8aba2aa07590be802",
        "parent_source_orientation_run":35950390662,
        "hypothesis":"target 6x6 geometry may supply semantic column identities through H/V orientation signatures omitted by color-only target models",
        "snapshots":snaps,
        "distinct_right_orientation_state_count":len(distinct_right),
        "distinct_right_column_signature_state_count":len(distinct_cols),
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; classify all size-3 source and target components by H/V orientation over canonical prefixes 0..5; diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_TARGET_ORIENTATION_CENSUS_G3=DIAGNOSTIC")

if __name__=="__main__": main()
