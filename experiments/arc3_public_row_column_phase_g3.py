from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-row-column-phase-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=g3.A
KNOWN=g3.KNOWN


def truth(mask,a,b):
    return (mask >> ((a<<1)|b)) & 1


def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x["color"])


def source_target(f):
    left,right=g3.panel_groups(f)
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(L)
    if rows!=sorted(R) or len(rows)!=6:
        return None,{"reason":"rows","L":rows,"R":sorted(R)}

    src=[];targets=[]
    target_cols=None
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:
            return None,{"reason":"arity","row":r,"ln":len(l),"rn":len(q)}
        vals=[bit(x) for x in l]
        if len(set(vals))!=1:
            return None,{"reason":"source_row_nonuniform","row":r,"vals":vals}
        src.append(vals[0]); targets.append(q)
        cols=[x["rc"][1] for x in q]
        if target_cols is None: target_cols=cols
        elif cols!=target_cols:
            return None,{"reason":"target_col_drift","row":r,"cols":cols,"expected":target_cols}
    return (rows,src,target_cols,targets),{"rows":rows,"source":src,"target_cols":target_cols}


def column_phase_bits(f,target_cols):
    # Read the fixed upper-right checker field directly from the observation.
    # For each writable target column, compare yellow vs gray occupancy in the
    # upper relation field (rows 4..31). Purple/magenta overlays are ignored.
    grid=g3.ab.grid(f)
    bits=[];evidence=[]
    for c in target_cols:
        yellow=sum(1 for r in range(4,32) if grid[r][c]==4)
        gray=sum(1 for r in range(4,32) if grid[r][c]==5)
        b=1 if yellow>gray else 0
        bits.append(b)
        evidence.append({"col":c,"yellow":yellow,"gray":gray,"phase":b})
    return bits,evidence


def apply(mask,prefix_len):
    e=g3.make_g3()
    start=int(e.observation_space.levels_completed)
    trace=[]

    for name,rc in KNOWN[:prefix_len]:
        z=g3.ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"mask":mask,"prefix_len":prefix_len,
                    "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                    "early":True,"trace":trace}

    data,meta=source_target(e.observation_space)
    if data is None:
        return {"mask":mask,"prefix_len":prefix_len,"progressed":False,"meta":meta}

    rows,src,target_cols,targets=data
    colbits,col_evidence=column_phase_bits(e.observation_space,target_cols)

    writes=[];desired=[]
    for i,rowtargets in enumerate(targets):
        rr=[]
        for j,t in enumerate(rowtargets):
            want=truth(mask,src[i],colbits[j])
            rr.append(want)
            if bit(t)!=want:
                rc=tuple(t["rc"])
                z=g3.ab.click(e,rc)
                writes.append(list(rc))
                trace.append({"name":"axis-write","rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
                if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
                    break
        desired.append(rr)
        if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
        trace.append({"name":"terminal:A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})

    return {
        "mask":mask,
        "truth_00_01_10_11":[truth(mask,a,b) for a,b in ((0,0),(0,1),(1,0),(1,1))],
        "prefix_len":prefix_len,
        "meta":meta,
        "column_bits":colbits,
        "column_evidence":col_evidence,
        "desired":desired,
        "writes":writes,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace,
    }


def verify(mask,k):
    return [apply(mask,k),apply(mask,k)]


def main():
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
        for mask in range(16):
            row=apply(mask,k)
            tested.append({x:y for x,y in row.items() if x!="trace"})
            if row.get("progressed"):
                vv=verify(mask,k)
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_len":k,
                        "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                        "mask":mask,
                        "truth_00_01_10_11":row.get("truth_00_01_10_11"),
                        "source":row.get("meta",{}).get("source"),
                        "column_bits":row.get("column_bits"),
                        "column_evidence":row.get("column_evidence"),
                    }
                    verification=vv
                    break
        if selected:break

    out={
        "status":"PROMOTED" if selected else "RESIDUAL",
        "hypothesis":"G3 writable 6x6 target is a binary relation between six generated source-row bits and six independently observed upper-right checker-phase column bits",
        "candidate_family":"all 16 Boolean functions f(rowBit,columnPhaseBit) across known A/B/C/D/E prefixes",
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"hard-restart exact public tn36 after qualified G1+G2; row bits come only from uniform lower-left source rows; column bits are derived from yellow-vs-gray occupancy in the observed upper-right field at the six writable target-column coordinates; all 16 binary relations; terminal A; two replay verification"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ROW_COLUMN_PHASE_G3="+out["status"])


if __name__=="__main__":
    main()
