from __future__ import annotations

import json
import os
from collections import Counter, deque
from pathlib import Path

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-equal-predicate-diff-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
PAIRS=[("S0_vs_SA",0,1),("SB_vs_SC",2,3),("SD_vs_SE",4,5)]


def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return [[int(v) for v in row] for row in x]


def replay(k):
    e,_=g3.enter_level3()
    for name,rc in KNOWN[:k]:
        ab.click(e,rc)
    rows,source,targets=sem.semantic_surface(e.observation_space)
    return e,rows,list(source),targets


def components(points):
    pts=set(points)
    out=[]
    while pts:
        start=next(iter(pts))
        pts.remove(start)
        q=deque([start]); comp=[start]
        while q:
            r,c=q.popleft()
            for p in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if p in pts:
                    pts.remove(p); q.append(p); comp.append(p)
        out.append(comp)
    return sorted(out,key=len,reverse=True)


def panel_signature(targets):
    return [[sem.bit(x["color"]) for x in row] for row in targets]


def main():
    results=[]
    for label,l,r in PAIRS:
        le,lrows,lsrc,ltgt=replay(l)
        re,rrows,rsrc,rtgt=replay(r)
        if lrows!=rrows:
            raise AssertionError("row identities differ")
        if lsrc!=rsrc:
            raise AssertionError(f"{label} source predicate differs: {lsrc} vs {rsrc}")

        lg=grid(le.observation_space); rg=grid(re.observation_space)
        changed=[]
        transitions=Counter()
        for i in range(len(lg)):
            for j in range(len(lg[i])):
                if lg[i][j]!=rg[i][j]:
                    changed.append((i,j))
                    transitions[(lg[i][j],rg[i][j])]+=1

        comps=components(changed)
        boxes=[]
        for comp in comps:
            rs=[x[0] for x in comp]; cs=[x[1] for x in comp]
            boxes.append({
                "size":len(comp),
                "bbox":[min(rs),min(cs),max(rs),max(cs)],
                "sample":[list(x) for x in sorted(comp)[:12]],
            })

        lpanel=panel_signature(ltgt)
        rpanel=panel_signature(rtgt)

        results.append({
            "pair":label,
            "left_prefix":l,
            "right_prefix":r,
            "source_predicate":lsrc,
            "target_panel_equal":lpanel==rpanel,
            "target_panel_left":lpanel,
            "target_panel_right":rpanel,
            "changed_pixels":len(changed),
            "color_transitions":{f"{a}->{b}":n for (a,b),n in sorted(transitions.items())},
            "changed_components":len(comps),
            "component_boxes":boxes[:20],
        })

    out={
        "status":"DIAGNOSTIC",
        "parent_failed_separator_head":"83a1dd2aace1a86bb32033bb439237095046910b",
        "parent_failed_run":35933302781,
        "hypothesis":"pairs previously equal only under the six-row source-predicate quotient may differ visibly elsewhere; localize the omitted observable before rerunning future-relative separation",
        "pairs":results,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; compare full rendered frames and writable target-panel signatures for source-predicate-equal prefix pairs S0/SA, SB/SC, SD/SE; diagnostic only, no protected-future claim",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_EQUAL_PREDICATE_DIFF_G3=DIAGNOSTIC")


if __name__=="__main__":
    main()
