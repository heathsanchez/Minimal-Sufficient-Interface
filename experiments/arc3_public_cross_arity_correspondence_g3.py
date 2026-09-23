from __future__ import annotations

import itertools
import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_panel_correspondence_g2 as g2
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-cross-arity-correspondence-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
EMBEDDINGS=list(itertools.combinations(range(6),4))


def rows(f):
    left,right=g3.size3_by_side(f)
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    common=sorted(set(L)&set(R))
    if len(common)!=6:
        raise AssertionError(f"expected six shared rows, got {common}")
    for r in common:
        L[r]=sorted(L[r],key=lambda x:x["rc"][1])
        R[r]=sorted(R[r],key=lambda x:x["rc"][1])
        if len(L[r])!=4 or len(R[r])!=6:
            raise AssertionError(f"expected 4->6 at row {r}, got {len(L[r])}->{len(R[r])}")
    return common,L,R


def run_variant(prefix,embedding):
    e,trace=g3.enter_level3()

    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"phase":"g3-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "progressed":int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),
                "early":True,"trace":trace,
            }

    common,L,R=rows(e.observation_space)
    planned=[]
    for r in common:
        for li,ri in enumerate(embedding):
            src=L[r][li]
            dst=R[r][ri]
            if src["color"]!=dst["color"]:
                planned.append({
                    "row":r,"source_rank":li,"target_rank":ri,
                    "source_color":src["color"],"target_before":dst["color"],
                    "rc":list(dst["rc"]),
                })

    applied=[]
    for item in planned:
        z=ab.click(e,tuple(item["rc"]))
        applied.append(item)
        trace.append({"phase":"cross-arity-match","rc":item["rc"],
                      "source_rank":item["source_rank"],"target_rank":item["target_rank"],
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break

    # Re-read and verify the selected correspondence exactly before submit.
    if e.observation_space.state==GameState.NOT_FINISHED and int(e.observation_space.levels_completed)==2:
        common2,L2,R2=rows(e.observation_space)
        remaining=[]
        for r in common2:
            for li,ri in enumerate(embedding):
                if L2[r][li]["color"]!=R2[r][ri]["color"]:
                    remaining.append({
                        "row":r,"source_rank":li,"target_rank":ri,
                        "source_color":L2[r][li]["color"],"target_color":R2[r][ri]["color"]
                    })
    else:
        remaining=[]

    if remaining:
        return {
            "progressed":False,
            "reason":"selected_correspondence_not_closed",
            "embedding":list(embedding),
            "planned":planned,"applied":applied,"remaining":remaining,
            "trace":trace,
        }

    if e.observation_space.state==GameState.NOT_FINISHED and int(e.observation_space.levels_completed)==2:
        z=ab.click(e,A)
        trace.append({"phase":"g3-submit","name":"A","rc":list(A),
                      "level":int(z.levels_completed),"state":str(z.state)})

    return {
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "embedding":list(embedding),
        "planned_count":len(planned),
        "planned":planned,
        "trace":trace,
    }


def main():
    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    attempts=[]
    selected=None
    verification=[]

    for pi,prefix in enumerate(prefixes):
        for emb in EMBEDDINGS:
            row=run_variant(prefix,emb)
            row["prefix_index"]=pi
            row["prefix"]=[{"name":n,"rc":list(rc)} for n,rc in prefix]
            attempts.append(row)
            if row.get("progressed"):
                vv=[run_variant(prefix,emb),run_variant(prefix,emb)]
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_index":pi,
                        "prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
                        "embedding":list(emb),
                        "planned_count":row.get("planned_count"),
                    }
                    verification=vv
                    break
        if selected is not None:
            break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    summary=[]
    for pi in range(len(prefixes)):
        rows_i=[x for x in attempts if x["prefix_index"]==pi]
        summary.append({
            "prefix_index":pi,
            "prefix_len":pi,
            "attempts":len(rows_i),
            "progress_count":sum(1 for x in rows_i if x.get("progressed")),
            "planned_counts":sorted(set(x.get("planned_count") for x in rows_i if x.get("planned_count") is not None)),
        })

    out={
        "status":status,
        "parent_g3_head":"57c2770c6affa0bd7199d683f230137f2772544f",
        "parent_g3_run":35927057975,
        "hypothesis":"G3 is the G2 panel-correspondence law lifted from 4->4 to one shared 4-of-6 target-rank embedding across all six rows",
        "embeddings":[list(x) for x in EMBEDDINGS],
        "embedding_count":len(EMBEDDINGS),
        "prefixes_tested":len(prefixes),
        "summary":summary,
        "attempts_tested":len(attempts),
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3; all 15 shared order-preserving injections of four source ranks into six target ranks tested across successive known A/B/C/D/E prefixes; only selected target positions are toggled to exact source colors; terminal A must progress in two independent replays",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_CROSS_ARITY_CORRESPONDENCE_G3="+status)


if __name__=="__main__":
    main()
