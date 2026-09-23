from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-semantic-relation-g3"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def truth(mask,a,b):
    return (mask >> ((a << 1) | b)) & 1


def bit(color):
    if color == 1:
        return 0
    if color == 5:
        return 1
    raise ValueError(color)


def color(b):
    return 5 if b else 1


def semantic_surface(f):
    left,right=g3.size3_by_side(f)
    L=defaultdict(list); R=defaultdict(list)
    for x in left: L[x["rc"][0]].append(x)
    for x in right: R[x["rc"][0]].append(x)

    rows=sorted(set(L)&set(R))
    if len(rows)!=6:
        raise AssertionError(f"expected six shared row identities, got {rows}")

    source=[]
    targets=[]
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:
            raise AssertionError(f"expected 4->6 row arity at {r}, got {len(l)}->{len(q)}")
        vals={bit(x["color"]) for x in l}
        if len(vals)!=1:
            raise AssertionError(f"source row {r} not a single predicate value: {vals}")
        source.append(next(iter(vals)))
        targets.append(q)

    if sum(source)!=2:
        raise AssertionError(f"expected exactly two selected source rows, got {source}")

    return rows,source,targets


def run_candidate(prefix, mask):
    e,trace=g3.enter_level3()
    start=int(e.observation_space.levels_completed)

    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({
            "phase":"g3-prefix","name":name,"rc":list(rc),
            "level":int(z.levels_completed),"state":str(z.state)
        })
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "progressed":int(z.levels_completed)>start or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),
                "early":True,"trace":trace,
            }

    rows,source,targets=semantic_surface(e.observation_space)
    desired=[[truth(mask,source[i],source[j]) for j in range(6)] for i in range(6)]
    actions=[]

    for i,r in enumerate(rows):
        for j,tgt in enumerate(targets[i]):
            want=desired[i][j]
            cur=bit(tgt["color"])
            if cur==want:
                continue
            rc=tuple(tgt["rc"])
            z=ab.click(e,rc)
            actions.append({
                "i":i,"j":j,"row":r,"rc":list(rc),
                "source_i":source[i],"source_j":source[j],
                "before":cur,"want":want,
            })
            trace.append({
                "phase":"g3-semantic-relation-write","i":i,"j":j,
                "rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)
            })
            if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
                break
        if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    remaining=None
    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        rows2,source2,targets2=semantic_surface(e.observation_space)
        desired2=[[truth(mask,source2[i],source2[j]) for j in range(6)] for i in range(6)]
        remaining=sum(
            1
            for i in range(6)
            for j in range(6)
            if bit(targets2[i][j]["color"]) != desired2[i][j]
        )
        if remaining!=0:
            raise AssertionError(f"semantic relation write incomplete: {remaining}")

        z=ab.click(e,A)
        trace.append({
            "phase":"g3-submit","name":"A","rc":list(A),
            "level":int(z.levels_completed),"state":str(z.state)
        })

    return {
        "mask":mask,
        "truth_table_00_01_10_11":[truth(mask,a,b) for a,b in ((0,0),(0,1),(1,0),(1,1))],
        "prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
        "source_predicate":source,
        "source_rows":rows,
        "desired_relation":desired,
        "write_count":len(actions),
        "remaining":remaining,
        "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace,
    }


def main():
    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    tested=[]
    selected=None
    verification=[]

    for k,prefix in enumerate(prefixes):
        for mask in range(16):
            row=run_candidate(prefix,mask)
            tested.append({
                "prefix_len":k,
                "mask":mask,
                "truth_table_00_01_10_11":row.get("truth_table_00_01_10_11"),
                "source_predicate":row.get("source_predicate"),
                "write_count":row.get("write_count"),
                "remaining":row.get("remaining"),
                "progressed":row.get("progressed"),
                "level":row.get("level"),
                "state":row.get("state"),
            })
            if row.get("progressed"):
                vv=[run_candidate(prefix,mask),run_candidate(prefix,mask)]
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_len":k,
                        "prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
                        "mask":mask,
                        "truth_table_00_01_10_11":row["truth_table_00_01_10_11"],
                        "source_predicate":row["source_predicate"],
                        "write_count":row["write_count"],
                    }
                    verification=vv
                    break
        if selected is not None:
            break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_row_color_head":"796b3c7685ae3c086a942fc81c1ccebc669df1b0",
        "parent_row_color_run":35929793423,
        "hypothesis":"the G3 left panel denotes a six-element unary predicate and the 6x6 target is a binary relation compiled uniformly as R_ij=f(s_i,s_j)",
        "source_bit":"gray=1, blue=0",
        "candidate_family":"all 16 binary Boolean relation constructors on ordered source predicate values",
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; six source row identities ordered geometrically; each source row is an observed monochromatic predicate value; target columns use the same six rank identities; all 16 uniform Boolean binary relations tested over ordered pairs; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SEMANTIC_RELATION_G3="+status)


if __name__=="__main__":
    main()
