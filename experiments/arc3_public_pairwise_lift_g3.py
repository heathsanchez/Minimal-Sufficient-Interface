from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-pairwise-lift-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=g3.A
KNOWN=g3.KNOWN
PAIRS=[(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]


def rows4x6(f):
    left,right=g3.panel_groups(f)
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    if sorted(L)!=sorted(R):
        return None,{"reason":"row_keys","left_rows":sorted(L),"right_rows":sorted(R)}
    rows=[]
    for r in sorted(L):
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:
            return None,{"reason":"arity","row":r,"left_n":len(l),"right_n":len(q)}
        rows.append((r,l,q))
    if len(rows)!=6:
        return None,{"reason":"row_count","rows":len(rows)}
    return rows,{"rows":6,"source_arity":4,"target_arity":6}


def truth(mask,a,b):
    # bit index 00,01,10,11
    return (mask >> ((a<<1)|b)) & 1


def encode_color(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x["color"])


def apply_candidate(mask,prefix_len):
    e=g3.make_g3()
    start=int(e.observation_space.levels_completed)
    trace=[]
    for name,rc in KNOWN[:prefix_len]:
        z=g3.ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "mask":mask,"prefix_len":prefix_len,
                "early_progress":int(z.levels_completed)>start or z.state==GameState.WIN,
                "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),"trace":trace
            }

    rows,meta=rows4x6(e.observation_space)
    if rows is None:
        return {"mask":mask,"prefix_len":prefix_len,"progressed":False,"meta":meta,
                "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

    desired_rows=[]
    writes=[]
    for r,l,q in rows:
        src=[encode_color(x) for x in l]
        desired=[truth(mask,src[i],src[j]) for i,j in PAIRS]
        desired_rows.append({"row":r,"source":src,"desired":desired})
        for bit,target in zip(desired,q):
            cur=encode_color(target)
            if cur!=bit:
                rc=tuple(target["rc"])
                z=g3.ab.click(e,rc)
                writes.append(list(rc))
                trace.append({"name":"pair-write","rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
                if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
                    break
        if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
        trace.append({"name":"terminal:A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})

    return {
        "mask":mask,"truth_table":[truth(mask,a,b) for a,b in ((0,0),(0,1),(1,0),(1,1))],
        "prefix_len":prefix_len,"meta":meta,"desired_rows":desired_rows,
        "writes":writes,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
        "trace":trace
    }


def verify(mask,prefix_len):
    return [apply_candidate(mask,prefix_len),apply_candidate(mask,prefix_len)]


def main():
    tested=[];selected=None;verification=[]
    # Prefix length first: seek the smallest generator state, then smallest truth-table id.
    for k in range(len(KNOWN)+1):
        for mask in range(16):
            row=apply_candidate(mask,k)
            tested.append({k:v for k,v in row.items() if k!="trace"})
            if row.get("progressed"):
                vv=verify(mask,k)
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_len":k,
                        "known_prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                        "mask":mask,
                        "truth_table_00_01_10_11":row.get("truth_table"),
                        "pair_order":PAIRS,
                    }
                    verification=vv
                    break
        if selected:break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "hypothesis":"G3 target width 6 is the six unordered-pair lift of four binary source positions",
        "source_bit":"gray=1, blue=0",
        "pair_order":PAIRS,
        "candidate_family":"all 16 binary Boolean functions applied uniformly to each unordered pair",
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"hard-restart exact public tn36 after qualified G1+G2; natural lexicographic unordered-pair ordering only; all 16 binary pair functions; known A/B/C/D/E prefixes; terminal A; two replay verification on any progress"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PAIRWISE_LIFT_G3="+status)


if __name__=="__main__":main()
