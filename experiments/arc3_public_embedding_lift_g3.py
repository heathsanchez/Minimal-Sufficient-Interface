from __future__ import annotations

import itertools
import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-embedding-lift-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=g3.A
KNOWN=g3.KNOWN
SUBSETS=list(itertools.combinations(range(6),4))


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
    out=[]
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:
            return None,{"reason":"arity","row":r,"ln":len(l),"rn":len(q)}
        src=[bit(x) for x in l]
        if len(set(src))!=1:
            return None,{"reason":"source_nonuniform","row":r,"src":src}
        out.append((r,src[0],q))
    return out,{"rows":rows}


def apply(subset,bg,prefix_len):
    e=g3.make_g3()
    start=int(e.observation_space.levels_completed)
    trace=[]
    for name,rc in KNOWN[:prefix_len]:
        z=g3.ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"subset":list(subset),"bg":bg,"prefix_len":prefix_len,
                    "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                    "early":True,"trace":trace}

    rows,meta=source_target(e.observation_space)
    if rows is None:
        return {"subset":list(subset),"bg":bg,"prefix_len":prefix_len,"progressed":False,"meta":meta}

    writes=[];desired=[]
    image=set(subset)
    for r,s,q in rows:
        row=[]
        for j,t in enumerate(q):
            want=s if j in image else bg
            row.append(want)
            if bit(t)!=want:
                rc=tuple(t["rc"])
                z=g3.ab.click(e,rc)
                writes.append(list(rc))
                trace.append({"name":"embed-write","rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
                if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
                    break
        desired.append({"row":r,"source":s,"desired":row})
        if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
        trace.append({"name":"terminal:A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})

    return {
        "subset":list(subset),"bg":bg,"prefix_len":prefix_len,"meta":meta,
        "desired":desired,"writes":writes,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
        "trace":trace,
    }


def verify(subset,bg,k):
    return [apply(subset,bg,k),apply(subset,bg,k)]


def main():
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
        for subset in SUBSETS:
            for bg in (0,1):
                row=apply(subset,bg,k)
                tested.append({x:y for x,y in row.items() if x!="trace"})
                if row.get("progressed"):
                    vv=verify(subset,bg,k)
                    if all(x.get("progressed") for x in vv):
                        selected={
                            "prefix_len":k,
                            "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                            "subset":list(subset),
                            "background":bg,
                        }
                        verification=vv
                        break
            if selected:break
        if selected:break

    out={
        "status":"PROMOTED" if selected else "RESIDUAL",
        "hypothesis":"G3 target width 6 contains an order-preserving four-column embedding of the uniform source-row bit; the two non-image columns share a fixed background bit",
        "candidate_family":"15 four-of-six subsets x 2 background bits across known A/B/C/D/E prefixes",
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"hard-restart exact public tn36 after qualified G1+G2; source rows must be uniform; target rows have six spatially ordered bars; test all four-column image subsets and both background bits; terminal A; verify twice on progress"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_EMBEDDING_LIFT_G3="+out["status"])


if __name__=="__main__":
    main()
