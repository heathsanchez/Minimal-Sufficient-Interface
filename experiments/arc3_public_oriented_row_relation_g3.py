from __future__ import annotations

import itertools
import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-oriented-row-relation-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=g3.A
KNOWN=g3.KNOWN


def truth(mask,a,b):
    return (mask >> ((a<<1)|b)) & 1


def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)


def source_target(f):
    left,right=g3.panel_groups(f)
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(L)
    if rows!=sorted(R) or len(rows)!=6:
        return None,{"reason":"rows","L":rows,"R":sorted(R)}

    src=[];targets=[]
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:
            return None,{"reason":"arity","row":r,"ln":len(l),"rn":len(q)}
        vals=[bit(x) for x in l]
        if len(set(vals))!=1:
            return None,{"reason":"source_row_nonuniform","row":r,"vals":vals}
        src.append(vals[0]);targets.append(q)
    return (rows,src,targets),{"rows":rows,"source":src}


def geometry_permutations():
    # Source row order is H0,V0,H1,V1,H2,V2 from observed alternating
    # horizontal/vertical size-3 geometry. Target columns are separated into
    # two 3-column blocks by the central upper-field divider.
    H=[0,2,4]; V=[1,3,5]
    out=[]
    for side_swap in (False,True):
        for rev_h in (False,True):
            for rev_v in (False,True):
                h=list(reversed(H)) if rev_h else list(H)
                v=list(reversed(V)) if rev_v else list(V)
                perm=(v+h) if side_swap else (h+v)
                out.append({
                    "perm":perm,
                    "side_order":"V|H" if side_swap else "H|V",
                    "reverse_H":rev_h,
                    "reverse_V":rev_v,
                })
    return out


PERMS=geometry_permutations()


def apply(mask,perm_rec,prefix_len):
    e=g3.make_g3()
    start=int(e.observation_space.levels_completed)
    trace=[]

    for name,rc in KNOWN[:prefix_len]:
        z=g3.ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "mask":mask,"prefix_len":prefix_len,"perm":perm_rec,
                "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                "early":True,"trace":trace,
            }

    data,meta=source_target(e.observation_space)
    if data is None:
        return {"mask":mask,"prefix_len":prefix_len,"perm":perm_rec,"progressed":False,"meta":meta}

    rows,src,targets=data
    colbits=[src[i] for i in perm_rec["perm"]]
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
                trace.append({"name":"oriented-relation-write","rc":list(rc),
                              "level":int(z.levels_completed),"state":str(z.state)})
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
        "perm":perm_rec,
        "meta":meta,
        "column_bits":colbits,
        "desired":desired,
        "writes":writes,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace,
    }


def verify(mask,perm_rec,k):
    return [apply(mask,perm_rec,k),apply(mask,perm_rec,k)]


def main():
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
        for p in PERMS:
            for mask in range(16):
                row=apply(mask,p,k)
                tested.append({x:y for x,y in row.items() if x!="trace"})
                if row.get("progressed"):
                    vv=verify(mask,p,k)
                    if all(x.get("progressed") for x in vv):
                        selected={
                            "prefix_len":k,
                            "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                            "geometry":p,
                            "mask":mask,
                            "truth_00_01_10_11":row.get("truth_00_01_10_11"),
                            "source":row.get("meta",{}).get("source"),
                            "column_bits":row.get("column_bits"),
                        }
                        verification=vv
                        break
            if selected:break
        if selected:break

    out={
        "status":"PROMOTED" if selected else "RESIDUAL",
        "hypothesis":"G3 target columns index the same six row entities in H0,H1,H2 | V0,V1,V2 geometry rather than the alternating H0,V0,H1,V1,H2,V2 source-row order",
        "geometry_family":PERMS,
        "candidate_family":"8 orientation-preserving row-to-column reorderings x all 16 Boolean functions across A/B/C/D/E prefixes",
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"hard-restart exact public tn36 after qualified G1+G2; source rows are uniform binary states in observed alternating H/V row geometry; target columns are modeled only by the two 3-column blocks with side swap and within-side reversal; all 16 binary relations; terminal A; two replay verification"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ORIENTED_ROW_RELATION_G3="+out["status"])


if __name__=="__main__":
    main()
