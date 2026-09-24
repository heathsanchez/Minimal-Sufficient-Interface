from __future__ import annotations

import json
import os
from pathlib import Path

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-left-component-census-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

def replay(k):
    e,_=g3.enter_level3()
    for _,rc in KNOWN[:k]:
        ab.click(e,rc)
    return e

def comp_record(comp):
    cells=[tuple(x) for x in comp["cells"]]
    rs=[r for r,c in cells]; cs=[c for r,c in cells]
    return {
        "color":int(comp["color"]),
        "size":int(comp["size"]),
        "bbox":[min(rs),min(cs),max(rs),max(cs)],
        "center":[sum(rs)//len(rs),sum(cs)//len(cs)],
        "sample":[list(x) for x in sorted(cells)[:16]],
    }

def left_components(f):
    rows=[]
    for comp in ab.comps(f):
        rec=comp_record(comp)
        # Any component touching the left half.
        if rec["bbox"][1] < 31:
            rows.append(rec)
    rows.sort(key=lambda x:(x["bbox"][0],x["bbox"][1],x["color"],x["size"]))
    return rows

def key(rec):
    return (rec["color"],rec["size"],tuple(rec["bbox"]))

def main():
    snaps=[]
    for k in range(6):
        e=replay(k)
        comps=left_components(e.observation_space)
        snaps.append({
            "prefix_len":k,
            "prefix":[n for n,_ in KNOWN[:k]],
            "components":comps,
        })

    deltas=[]
    for a,b in zip(snaps[:-1],snaps[1:]):
        Amap={key(x):x for x in a["components"]}
        Bmap={key(x):x for x in b["components"]}
        removed=[Amap[k] for k in sorted(Amap.keys()-Bmap.keys())]
        added=[Bmap[k] for k in sorted(Bmap.keys()-Amap.keys())]
        deltas.append({
            "from_prefix_len":a["prefix_len"],
            "to_prefix_len":b["prefix_len"],
            "action":KNOWN[a["prefix_len"]][0],
            "removed":removed,
            "added":added,
        })

    out={
        "status":"DIAGNOSTIC",
        "parent_delta_head":"dc3c6ae815960e1de999febb545652a554cf2eda",
        "parent_delta_run":35952157581,
        "hypothesis":"B/D change visible left-side control geometry outside the six-row panel; inventory that structure before proposing another target semantics",
        "snapshots":snaps,
        "deltas":deltas,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; connected-component census of all visible components touching columns <31 across canonical prefixes 0..5; component identity by color,size,bbox; diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_LEFT_COMPONENT_CENSUS_G3=DIAGNOSTIC")

if __name__=="__main__":
    main()
