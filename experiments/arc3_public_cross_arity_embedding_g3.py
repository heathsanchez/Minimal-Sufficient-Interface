from __future__ import annotations

import itertools
import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-cross-arity-embedding-g3"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
EMBEDDINGS=list(itertools.combinations(range(6),4))


def rows_of_size3(f):
    left,right=g3.size3_by_side(f)
    L=defaultdict(list); R=defaultdict(list)
    for x in left: L[x["rc"][0]].append(x)
    for x in right: R[x["rc"][0]].append(x)
    rows=sorted(set(L)&set(R))
    if len(rows)!=6:
        raise AssertionError(f"expected 6 shared rows, got {rows}")
    for r in rows:
        L[r]=sorted(L[r],key=lambda x:x["rc"][1])
        R[r]=sorted(R[r],key=lambda x:x["rc"][1])
        if len(L[r])!=4 or len(R[r])!=6:
            raise AssertionError(
                f"expected 4->6 arity on row {r}, got {len(L[r])}->{len(R[r])}"
            )
    return rows,L,R


def run_candidate(prefix, embedding):
    e,trace=g3.enter_level3()

    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({
            "phase":"g3-prefix","name":name,"rc":list(rc),
            "level":int(z.levels_completed),"state":str(z.state)
        })
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "progressed":int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),
                "state":str(z.state),
                "early":True,
                "trace":trace,
            }

    rows,L,R=rows_of_size3(e.observation_space)
    before={
        str(r):{
            "left":[x["color"] for x in L[r]],
            "right":[x["color"] for x in R[r]],
            "left_rc":[list(x["rc"]) for x in L[r]],
            "right_rc":[list(x["rc"]) for x in R[r]],
        }
        for r in rows
    }

    actions=[]
    for r in rows:
        for src_rank,tgt_rank in enumerate(embedding):
            src=L[r][src_rank]
            tgt=R[r][tgt_rank]
            if src["color"]==tgt["color"]:
                continue
            rc=tuple(tgt["rc"])
            z=ab.click(e,rc)
            actions.append({
                "row":r,
                "src_rank":src_rank,
                "tgt_rank":tgt_rank,
                "rc":list(rc),
                "want":src["color"],
                "before":tgt["color"],
            })
            trace.append({
                "phase":"g3-cross-arity-write","rc":list(rc),
                "row":r,"src_rank":src_rank,"tgt_rank":tgt_rank,
                "level":int(z.levels_completed),"state":str(z.state)
            })
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                break
        if int(e.observation_space.levels_completed)>2 or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break

    selected_remaining=None
    nonimage=None
    if e.observation_space.state==GameState.NOT_FINISHED:
        rows2,L2,R2=rows_of_size3(e.observation_space)
        selected_remaining=sum(
            1
            for r in rows2
            for src_rank,tgt_rank in enumerate(embedding)
            if L2[r][src_rank]["color"] != R2[r][tgt_rank]["color"]
        )
        image=set(embedding)
        nonimage={
            str(r):[
                {"rank":j,"rc":list(R2[r][j]["rc"]),"color":R2[r][j]["color"]}
                for j in range(6) if j not in image
            ]
            for r in rows2
        }

        z=ab.click(e,A)
        trace.append({
            "phase":"g3-submit","name":"A","rc":list(A),
            "level":int(z.levels_completed),"state":str(z.state)
        })

    return {
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "embedding":list(embedding),
        "write_count":len(actions),
        "selected_remaining":selected_remaining,
        "before":before,
        "nonimage_after_write":nonimage,
        "actions":actions,
        "trace":trace,
    }


def main():
    variants=[]
    selected=None
    verification=[]

    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    for pi,prefix in enumerate(prefixes):
        for embedding in EMBEDDINGS:
            row=run_candidate(prefix,embedding)
            row["prefix_index"]=pi
            row["prefix"]=[{"name":n,"rc":list(rc)} for n,rc in prefix]
            variants.append(row)

            if row.get("selected_remaining") not in (0,None):
                raise AssertionError(
                    f"embedding write failed exact selected match: {embedding} "
                    f"remaining={row['selected_remaining']}"
                )

            if row.get("progressed"):
                vv=[run_candidate(prefix,embedding),run_candidate(prefix,embedding)]
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_index":pi,
                        "prefix":row["prefix"],
                        "embedding":list(embedding),
                        "write_count":row.get("write_count"),
                    }
                    verification=vv
                    break
        if selected is not None:
            break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_g3_head":"57c2770c6affa0bd7199d683f230137f2772544f",
        "parent_g3_run":35927057975,
        "hypothesis":"G3 is a pure 4-to-6 rank embedding lift of the qualified G2 source-to-target panel correspondence law",
        "embeddings_tested":len(EMBEDDINGS),
        "prefixes_declared":len(prefixes),
        "candidate_variants_executed":len(variants),
        "variants":[
            {
                "prefix_index":v["prefix_index"],
                "prefix":v["prefix"],
                "embedding":v.get("embedding"),
                "write_count":v.get("write_count"),
                "selected_remaining":v.get("selected_remaining"),
                "progressed":v.get("progressed"),
                "level":v.get("level"),
                "state":v.get("state"),
                "nonimage_after_write":v.get("nonimage_after_write"),
            }
            for v in variants
        ],
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":30,
        "claim_boundary":"exact public tn36 G3; frozen qualified G2 entry; all 15 shared order-preserving 4-of-6 target rank embeddings tested across successive A/B/C/D/E prefixes; only mapped right bars are toggled to observed left colors; terminal A; any progress independently replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_CROSS_ARITY_EMBEDDING_G3="+status)


if __name__=="__main__":
    main()
