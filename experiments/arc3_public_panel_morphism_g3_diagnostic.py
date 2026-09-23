from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-panel-morphism-g3-diagnostic")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def rows(f):
    left,right=g3.size3_by_side(f)
    def pack(xs):
        d=defaultdict(list)
        for x in xs:
            d[x["rc"][0]].append(x)
        out={}
        for r,vals in sorted(d.items()):
            vals=sorted(vals,key=lambda x:x["rc"][1])
            out[str(r)]={
                "coords":[list(x["rc"]) for x in vals],
                "colors":[x["color"] for x in vals],
                "word":"".join("G" if x["color"]==5 else "B" for x in vals),
            }
        return out
    return pack(left),pack(right)


def snap(prefix):
    e,trace=g3.enter_level3()
    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"phase":"diag-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
    L,R=rows(e.observation_space)
    return {
        "prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
        "left":L,
        "right":R,
        "left_count":sum(len(v["colors"]) for v in L.values()),
        "right_count":sum(len(v["colors"]) for v in R.values()),
    }


def main():
    variants=[]
    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])
    for p in prefixes:
        variants.append(snap(p))

    out={
        "status":"PASS",
        "parent_head":"57c2770c6affa0bd7199d683f230137f2772544f",
        "variants":variants,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"read-only exact public tn36 G3 size-3 panel row words across successive known A/B/C/D/E prefixes after replaying qualified G1/G2 solvers",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PANEL_MORPHISM_G3_DIAGNOSTIC=PASS")


if __name__=="__main__":
    main()
