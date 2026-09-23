from __future__ import annotations
import itertools,json,os
from collections import defaultdict
from pathlib import Path
from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-endpoint-matching-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
A=g3.A; KNOWN=g3.KNOWN

def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)

def surface(f):
    left,right=g3.panel_groups(f); L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(L)
    if rows!=sorted(R) or len(rows)!=6:return None
    src=[];targets=[];cols=None
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1]);q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:return None
        vals=[bit(x) for x in l]
        if len(set(vals))!=1:return None
        src.append(vals[0]);targets.append(q)
        cc=[x["rc"][1] for x in q]
        if cols is None:cols=cc
        elif cc!=cols:return None
    return rows,src,cols,targets

def selected_columns(f,cols):
    # Use the centers of the two observed purple components in the upper-right field.
    # Map each component center to the nearest writable target-column center.
    picks=[]
    for comp in g3.ab.comps(f):
        if comp["color"]!=11:continue
        cells=comp["cells"];rs=[r for r,c in cells];cs=[c for r,c in cells]
        if max(rs)>=32 or min(cs)<32:continue
        center=cells[len(cells)//2]
        j=min(range(len(cols)),key=lambda k:abs(cols[k]-center[1]))
        picks.append({"component_center":list(center),"target_index":j,"target_col":cols[j],"size":len(cells)})
    # preserve unique target indices
    uniq=[];seen=set()
    for x in sorted(picks,key=lambda x:(x["component_center"][0],x["component_center"][1])):
        if x["target_index"] not in seen:
            seen.add(x["target_index"]);uniq.append(x)
    return uniq

def apply(pairing,polarity,k):
    e=g3.make_g3();start=int(e.observation_space.levels_completed)
    for name,rc in KNOWN[:k]:
        z=g3.ab.click(e,rc)
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"pairing":pairing,"polarity":polarity,"prefix_len":k,
                    "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,"early":True}
    d=surface(e.observation_space)
    if d is None:return {"pairing":pairing,"polarity":polarity,"prefix_len":k,"progressed":False,"reason":"surface"}
    rows,src,cols,tgt=d
    active_rows=[i for i,b in enumerate(src) if b==1]
    cp=selected_columns(e.observation_space,cols)
    active_cols=[x["target_index"] for x in cp]
    if len(active_rows)!=2 or len(active_cols)!=2:
        return {"pairing":pairing,"polarity":polarity,"prefix_len":k,"progressed":False,
                "reason":"arity","active_rows":active_rows,"active_cols":active_cols,"column_components":cp}
    active_cols=list(reversed(active_cols)) if pairing=="cross" else active_cols
    special={(active_rows[0],active_cols[0]),(active_rows[1],active_cols[1])}
    writes=[]
    for i,row in enumerate(tgt):
      for j,t in enumerate(row):
        special_cell=(i,j) in special
        want=(1 if special_cell else 0) if polarity=="gray_on_match" else (0 if special_cell else 1)
        if bit(t)!=want:
            z=g3.ab.click(e,tuple(t["rc"]));writes.append(list(t["rc"]))
            if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):break
      if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):break
    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
    return {"pairing":pairing,"polarity":polarity,"prefix_len":k,
            "source":src,"active_rows":active_rows,"column_components":cp,"active_cols":active_cols,
            "special_cells":[list(x) for x in sorted(special)],"writes":writes,
            "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
            "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

def verify(pairing,polarity,k):return [apply(pairing,polarity,k),apply(pairing,polarity,k)]

def main():
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
      for pairing in ("direct","cross"):
       for polarity in ("gray_on_match","blue_on_match"):
        r=apply(pairing,polarity,k);tested.append(r)
        if r.get("progressed"):
            vv=verify(pairing,polarity,k)
            if all(x.get("progressed") for x in vv):
                selected={"prefix_len":k,"pairing":pairing,"polarity":polarity,
                          "source":r.get("source"),"active_rows":r.get("active_rows"),
                          "column_components":r.get("column_components"),"active_cols":r.get("active_cols"),
                          "special_cells":r.get("special_cells")}
                verification=vv;break
       if selected:break
      if selected:break
    out={"status":"PROMOTED" if selected else "RESIDUAL",
         "hypothesis":"G3 target encodes a bijection between the two generated gray source rows and the two observed upper-right purple-object column anchors",
         "candidate_family":"direct/cross endpoint pairing x two polarities across A/B/C/D/E prefixes",
         "tested":tested,"selected":selected,"verification":verification,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"exact public tn36 G3 after qualified G1/G2; two active rows come from uniform gray source rows; two active columns come from centers of observed upper-right purple components mapped to writable columns; test both bijections and polarities; terminal A; verify twice"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ENDPOINT_MATCHING_G3="+out["status"])
if __name__=="__main__":main()
