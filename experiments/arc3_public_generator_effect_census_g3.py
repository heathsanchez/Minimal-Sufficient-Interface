from __future__ import annotations

import json
import os
from collections import Counter, deque
from pathlib import Path

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-generator-effect-census-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
MARKERS=[("M61",(1,61)),("M59",(1,59)),("M57",(1,57))]

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return [[int(v) for v in row] for row in x]

def source_panel(f):
    rows,src,targets=sem.semantic_surface(f)
    panel=[[sem.bit(x["color"]) for x in row] for row in targets]
    return rows,list(src),panel

def marker_vals(f):
    g=grid(f)
    return {name:g[r][c] for name,(r,c) in MARKERS}

def components(points):
    pts=set(points); out=[]
    while pts:
        p=next(iter(pts)); pts.remove(p)
        q=deque([p]); comp=[p]
        while q:
            r,c=q.popleft()
            for n in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if n in pts:
                    pts.remove(n); q.append(n); comp.append(n)
        out.append(comp)
    return sorted(out,key=len,reverse=True)

def classify_bbox(box):
    r0,c0,r1,c1=box
    if r1 <= 4:
        return "top_marker_band"
    if c1 < 31:
        return "left_source_region"
    if r0 >= 30 and c0 >= 31:
        return "right_target_region"
    return "other"

def main():
    e,trace=g3.enter_level3()
    results=[]

    for name,rc in KNOWN:
        bg=grid(e.observation_space)
        brows,bsrc,bpanel=source_panel(e.observation_space)
        bmarkers=marker_vals(e.observation_space)

        z=ab.click(e,rc)

        ag=grid(e.observation_space)
        arows,asrc,apanel=source_panel(e.observation_space)
        amarkers=marker_vals(e.observation_space)

        if brows!=arows:
            raise AssertionError("row identities changed")

        changed=[]
        trans=Counter()
        for i in range(len(bg)):
            for j in range(len(bg[i])):
                if bg[i][j]!=ag[i][j]:
                    changed.append((i,j))
                    trans[(bg[i][j],ag[i][j])]+=1

        comps=components(changed)
        boxes=[]
        region_counts=Counter()
        for comp in comps:
            rs=[x[0] for x in comp]; cs=[x[1] for x in comp]
            box=[min(rs),min(cs),max(rs),max(cs)]
            region=classify_bbox(box)
            region_counts[region]+=1
            boxes.append({
                "size":len(comp),
                "bbox":box,
                "region":region,
                "sample":[list(x) for x in sorted(comp)[:12]],
            })

        results.append({
            "action":name,
            "rc":list(rc),
            "source_before":bsrc,
            "source_after":asrc,
            "source_changed":bsrc!=asrc,
            "panel_changed":bpanel!=apanel,
            "marker_before":bmarkers,
            "marker_after":amarkers,
            "marker_changed":bmarkers!=amarkers,
            "changed_pixels":len(changed),
            "color_transitions":{f"{a}->{b}":n for (a,b),n in sorted(trans.items())},
            "component_regions":dict(region_counts),
            "component_boxes":boxes[:20],
            "outcome":"PROGRESS" if int(z.levels_completed)>2 else ("GAME_OVER" if str(z.state).endswith("GAME_OVER") else "CONTINUE"),
        })

    out={
        "status":"DIAGNOSTIC",
        "parent_head":"86758053a743f9e512a192a5d1b649a117d30dbb",
        "parent_run":35946950110,
        "hypothesis":"canonical G3 generator actions may decompose into distinct semantic channels; census exact one-step effects before proposing another target encoding",
        "results":results,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; sequential canonical A/B/C/D/E generator actions; record exact source-predicate, target-panel, marker and full-frame effect classes; diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_GENERATOR_EFFECT_CENSUS_G3=DIAGNOSTIC")

if __name__=="__main__":
    main()
