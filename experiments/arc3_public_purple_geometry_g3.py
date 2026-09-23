from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-purple-geometry-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)


def target_surface(f):
    left,right=g3.size3_by_side(f)
    R=defaultdict(list)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(R)
    if len(rows)!=6:return None
    out=[]
    cols=None
    for r in rows:
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(q)!=6:return None
        cc=[x["rc"][1] for x in q]
        if cols is None:cols=cc
        elif cc!=cols:return None
        out.append(q)
    return rows,cols,out


def purple_points(f,cols):
    comps=[]
    for x in ab.comps(f):
        if x["color"]!=11:continue
        cells=x["cells"];rs=[r for r,c in cells];cs=[c for r,c in cells]
        if max(rs)>=32 or min(cs)<32:continue
        r0=min(rs);r1=max(rs);c0=min(cs);c1=max(cs)
        row=(r0-4)//4
        mean_c=sum(cs)/len(cs)
        col=min(range(len(cols)),key=lambda j:abs(cols[j]-mean_c))
        comps.append({"point":[row,col],"bbox":[r0,c0,r1,c1],"size":len(cells),"mean_col":mean_c})
    comps=sorted(comps,key=lambda x:(x["point"][0],x["point"][1]))
    return comps


def line(a,b):
    r1,c1=a;r2,c2=b
    dr=r2-r1;dc=c2-c1
    n=max(abs(dr),abs(dc))
    if n==0:return {a}
    if dr%n!=0 or dc%n!=0:return {a,b}
    sr=dr//n;sc=dc//n
    return {(r1+k*sr,c1+k*sc) for k in range(n+1)}


def pattern_cells(name,p,q):
    r1,c1=p;r2,c2=q
    ra,rb=sorted((r1,r2));ca,cb=sorted((c1,c2))
    rows={(r,c) for r in (r1,r2) for c in range(6)}
    cols={(r,c) for c in (c1,c2) for r in range(6)}
    rect={(r,c) for r in range(ra,rb+1) for c in range(ca,cb+1)}
    border={(r,c) for r in range(ra,rb+1) for c in range(ca,cb+1)
            if r in (ra,rb) or c in (ca,cb)}
    corners={(ra,ca),(ra,cb),(rb,ca),(rb,cb)}
    diag=line(p,q)
    other=line((r1,c2),(r2,c1))
    rowsegs={(r1,c) for c in range(ca,cb+1)}|{(r2,c) for c in range(ca,cb+1)}
    colsegs={(r,c1) for r in range(ra,rb+1)}|{(r,c2) for r in range(ra,rb+1)}
    l1={(r1,c) for c in range(ca,cb+1)}|{(r,c2) for r in range(ra,rb+1)}
    l2={(r2,c) for c in range(ca,cb+1)}|{(r,c1) for r in range(ra,rb+1)}
    interior={(r,c) for r in range(ra+1,rb) for c in range(ca+1,cb)}
    mp={
      "endpoints":{p,q},
      "opposite_corners":{(r1,c2),(r2,c1)},
      "four_corners":corners,
      "rows":rows,
      "cols":cols,
      "rows_or_cols":rows|cols,
      "rows_xor_cols":rows^cols,
      "rectangle_fill":rect,
      "rectangle_border":border,
      "direct_diagonal":diag,
      "other_diagonal":other,
      "x_diagonals":diag|other,
      "row_segments":rowsegs,
      "col_segments":colsegs,
      "L_forward":l1,
      "L_reverse":l2,
      "rectangle_interior":interior,
    }
    return mp[name]


PATTERNS=[
 "endpoints","opposite_corners","four_corners","rows","cols","rows_or_cols","rows_xor_cols",
 "rectangle_fill","rectangle_border","direct_diagonal","other_diagonal","x_diagonals",
 "row_segments","col_segments","L_forward","L_reverse","rectangle_interior"
]


def apply(name,polarity,k):
    e,trace=g3.enter_level3()
    start=int(e.observation_space.levels_completed)
    for n,rc in KNOWN[:k]:
        z=ab.click(e,rc)
        trace.append({"phase":"prefix","name":n,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"pattern":name,"polarity":polarity,"prefix_len":k,
                    "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,"early":True}
    surf=target_surface(e.observation_space)
    if surf is None:return {"pattern":name,"polarity":polarity,"prefix_len":k,"progressed":False,"reason":"surface"}
    rows,cols,tgt=surf
    comps=purple_points(e.observation_space,cols)
    if len(comps)!=2:
        return {"pattern":name,"polarity":polarity,"prefix_len":k,"progressed":False,"reason":"purple_arity","components":comps}
    p=tuple(comps[0]["point"]);q=tuple(comps[1]["point"])
    if any(not(0<=v<6) for pt in (p,q) for v in pt):
        return {"pattern":name,"polarity":polarity,"prefix_len":k,"progressed":False,"reason":"point_range","components":comps}
    cells=pattern_cells(name,p,q)
    writes=[]
    for i,row in enumerate(tgt):
      for j,t in enumerate(row):
        inside=(i,j) in cells
        want=(1 if inside else 0) if polarity=="gray_on_pattern" else (0 if inside else 1)
        if bit(t)!=want:
            z=ab.click(e,tuple(t["rc"]));writes.append(list(t["rc"]))
            if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):break
      if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):break
    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=ab.click(e,A)
    return {"pattern":name,"polarity":polarity,"prefix_len":k,"components":comps,
            "points":[list(p),list(q)],"pattern_cells":[list(x) for x in sorted(cells)],"writes":writes,
            "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
            "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}


def verify(name,polarity,k):return [apply(name,polarity,k),apply(name,polarity,k)]


def main():
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
      for name in PATTERNS:
       for polarity in ("gray_on_pattern","blue_on_pattern"):
        r=apply(name,polarity,k);tested.append(r)
        if r.get("progressed"):
            vv=verify(name,polarity,k)
            if all(x.get("progressed") for x in vv):
                selected={"prefix_len":k,"prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                          "pattern":name,"polarity":polarity,"points":r.get("points"),
                          "components":r.get("components"),"pattern_cells":r.get("pattern_cells")}
                verification=vv;break
       if selected:break
      if selected:break
    out={"status":"PROMOTED" if selected else "RESIDUAL",
         "hypothesis":"G3 6x6 target is a direct 2-D geometric projection of the two observed upper-right purple component anchors",
         "patterns":PATTERNS,"tested":tested,"selected":selected,"verification":verification,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"exact public tn36 G3 after qualified G1/G2; two upper-right purple components mapped to 6x6 target coordinates from checker-row origin and nearest target column; finite geometric pattern bank and complements; A/B/C/D/E prefixes; terminal A; verify twice"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PURPLE_GEOMETRY_G3="+out["status"])

if __name__=="__main__":main()
