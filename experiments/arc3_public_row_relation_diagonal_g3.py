from __future__ import annotations
import json, os
from collections import defaultdict
from pathlib import Path
from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-row-relation-diagonal-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
A=g3.A
KNOWN=g3.KNOWN

# Six realizable equivalence classes for (s_i,s_j, i=j):
# 0=off(0,0), 1=off(0,1), 2=off(1,0), 3=off(1,1),
# 4=diag(0,0), 5=diag(1,1).
def truth(mask,a,b,eq):
    if eq:
        idx=4+a
    else:
        idx=(a<<1)|b
    return (mask>>idx)&1

def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)

def source_and_target(f):
    left,right=g3.panel_groups(f)
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(L)
    if rows!=sorted(R) or len(rows)!=6:
        return None,{"reason":"rows","L":rows,"R":sorted(R)}
    src=[];target=[]
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:
            return None,{"reason":"arity","row":r,"ln":len(l),"rn":len(q)}
        vals=[bit(x) for x in l]
        if len(set(vals))!=1:
            return None,{"reason":"source_row_nonuniform","row":r,"vals":vals}
        src.append(vals[0]);target.append(q)
    return (rows,src,target),{"rows":rows,"source":src}

def apply(mask,prefix_len):
    e=g3.make_g3()
    start=int(e.observation_space.levels_completed)
    trace=[]
    for name,rc in KNOWN[:prefix_len]:
        z=g3.ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "mask":mask,"prefix_len":prefix_len,
                "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                "early":True,"trace":trace
            }

    data,meta=source_and_target(e.observation_space)
    if data is None:
        return {"mask":mask,"prefix_len":prefix_len,"progressed":False,"meta":meta}

    rows,src,target=data
    writes=[]
    desired=[]
    for i,rowtargets in enumerate(target):
        rr=[]
        for j,t in enumerate(rowtargets):
            want=truth(mask,src[i],src[j],i==j)
            rr.append(want)
            if bit(t)!=want:
                rc=tuple(t["rc"])
                z=g3.ab.click(e,rc)
                writes.append(list(rc))
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
        "truth_classes":[truth(mask,0,0,False),truth(mask,0,1,False),truth(mask,1,0,False),
                         truth(mask,1,1,False),truth(mask,0,0,True),truth(mask,1,1,True)],
        "prefix_len":prefix_len,
        "meta":meta,
        "desired":desired,
        "writes":writes,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace
    }

def verify(mask,k):
    return [apply(mask,k),apply(mask,k)]

def main():
    tested=[]
    selected=None
    verification=[]
    for k in range(len(KNOWN)+1):
        for mask in range(64):
            row=apply(mask,k)
            tested.append({x:y for x,y in row.items() if x!="trace"})
            if row.get("progressed"):
                vv=verify(mask,k)
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_len":k,
                        "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                        "mask":mask,
                        "truth_off00_off01_off10_off11_diag00_diag11":row.get("truth_classes"),
                        "source":row.get("meta",{}).get("source"),
                        "writes":row.get("writes"),
                    }
                    verification=vv
                    break
        if selected:break

    out={
        "status":"PROMOTED" if selected else "RESIDUAL",
        "hypothesis":"G3 target 6x6 panel is a permutation-invariant binary relation on the six source-row bits, with diagonal identity available as one extra predicate",
        "candidate_family":"all 64 functions over the six realizable classes (off00,off01,off10,off11,diag00,diag11)",
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"hard-restart exact public tn36 after qualified G1+G2; source rows uniform; target row/column identities by spatial order; exhaustive 64 permutation-invariant bit+diagonal relations; known A/B/C/D/E prefixes; terminal A; two replay verification"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ROW_RELATION_DIAGONAL_G3="+out["status"])

if __name__=="__main__":main()
