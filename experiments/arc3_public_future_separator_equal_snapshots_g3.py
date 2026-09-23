from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
from typing import Iterable

from arcengine import GameState

import arc3_public_compiled_state_trace_g3 as st
import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-future-separator-equal-snapshots-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
PAIR_PREFIXES=[
    ("S0_vs_SA",0,1),
    ("SB_vs_SC",2,3),
    ("SD_vs_SE",4,5),
]
MAX_DEPTH=2


def frame_grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return [[int(v) for v in row] for row in x]


def frame_hash(f):
    return hashlib.sha256(
        json.dumps(frame_grid(f),separators=(",",":")).encode()
    ).hexdigest()


def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"


def replay_prefix(k:int):
    e,_=g3.enter_level3()
    trace=[]
    for name,rc in KNOWN[:k]:
        z=ab.click(e,rc)
        trace.append({
            "name":name,"rc":list(rc),
            "level":int(z.levels_completed),"state":str(z.state),
        })
        if protected(z)!="CONTINUE":
            break
    return e,trace


def target_centers():
    e,_=replay_prefix(0)
    rows,source,targets=sem.semantic_surface(e.observation_space)
    out=[]
    for i,r in enumerate(rows):
        for j,t in enumerate(targets[i]):
            out.append((f"T{i}{j}",tuple(t["rc"])))
    return out


def alphabet():
    seen=set()
    out=[]
    for name,rc in KNOWN+target_centers():
        if rc in seen:
            continue
        seen.add(rc)
        out.append((name,rc))
    return out


def execute(k:int,suffix:Iterable[tuple[str,tuple[int,int]]]):
    e,prefix_trace=replay_prefix(k)
    before_hash=frame_hash(e.observation_space)
    trace=list(prefix_trace)
    early=None

    for name,rc in suffix:
        z=ab.click(e,rc)
        trace.append({
            "phase":"suffix","name":name,"rc":list(rc),
            "level":int(z.levels_completed),"state":str(z.state),
        })
        po=protected(z)
        if po!="CONTINUE":
            early=po
            break

    after_suffix_hash=frame_hash(e.observation_space)
    if early is None:
        z=ab.click(e,A)
        trace.append({
            "phase":"terminal","name":"A","rc":list(A),
            "level":int(z.levels_completed),"state":str(z.state),
        })
        outcome=protected(z)
    else:
        outcome=early

    return {
        "prefix_len":k,
        "before_hash":before_hash,
        "after_suffix_hash":after_suffix_hash,
        "outcome":outcome,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace,
    }


def suffixes(alpha):
    yield ()
    for depth in range(1,MAX_DEPTH+1):
        for seq in itertools.product(alpha,repeat=depth):
            yield seq


def compact_suffix(seq):
    return [{"name":name,"rc":list(rc)} for name,rc in seq]


def verify_separator(left_k,right_k,seq):
    rows=[]
    for _ in range(2):
        l=execute(left_k,seq)
        r=execute(right_k,seq)
        rows.append({
            "left":l["outcome"],"right":r["outcome"],
            "left_hash":l["after_suffix_hash"],
            "right_hash":r["after_suffix_hash"],
        })
    return rows


def main():
    alpha=alphabet()

    equality=[]
    for label,l,r in PAIR_PREFIXES:
        le,_=replay_prefix(l)
        re,_=replay_prefix(r)
        lh=frame_hash(le.observation_space)
        rh=frame_hash(re.observation_space)
        equality.append({
            "pair":label,"left_prefix":l,"right_prefix":r,
            "left_hash":lh,"right_hash":rh,"exact_equal":lh==rh,
        })
        if lh!=rh:
            raise AssertionError(f"{label} not exact-equal: {lh} != {rh}")

    protected_separator=None
    first_response_separator=None
    evaluations=0
    tested_by_depth={str(d):0 for d in range(MAX_DEPTH+1)}

    for label,l,r in PAIR_PREFIXES:
        for seq in suffixes(alpha):
            depth=len(seq)
            L=execute(l,seq)
            R=execute(r,seq)
            evaluations+=2
            tested_by_depth[str(depth)]+=1

            if (
                first_response_separator is None
                and L["after_suffix_hash"]!=R["after_suffix_hash"]
            ):
                first_response_separator={
                    "pair":label,
                    "left_prefix":l,"right_prefix":r,
                    "suffix":compact_suffix(seq),
                    "left_after_suffix_hash":L["after_suffix_hash"],
                    "right_after_suffix_hash":R["after_suffix_hash"],
                    "left_outcome":L["outcome"],
                    "right_outcome":R["outcome"],
                }

            if L["outcome"]!=R["outcome"]:
                vv=verify_separator(l,r,seq)
                if all(x["left"]!=x["right"] for x in vv):
                    protected_separator={
                        "pair":label,
                        "left_prefix":l,"right_prefix":r,
                        "suffix":compact_suffix(seq),
                        "left_outcome":L["outcome"],
                        "right_outcome":R["outcome"],
                        "verification":vv,
                    }
                    break
        if protected_separator is not None:
            break

    if protected_separator is not None:
        status="PROTECTED_SEPARATOR"
    elif first_response_separator is not None:
        status="RESPONSE_SEPARATOR_ONLY"
    else:
        status="NO_SEPARATOR"

    out={
        "status":status,
        "parent_trace_head":"159756b180570a284569e5011b41866931d4eb37",
        "parent_trace_run":35932608382,
        "hypothesis":"repeated exact-equal G3 snapshots may still be continuation-distinct; search for the shortest common lawful suffix that separates their protected future response",
        "equal_snapshot_pairs":equality,
        "alphabet":[{"name":n,"rc":list(rc)} for n,rc in alpha],
        "alphabet_size":len(alpha),
        "max_suffix_depth":MAX_DEPTH,
        "tested_suffix_counts":tested_by_depth,
        "candidate_evaluations":evaluations,
        "protected_separator":protected_separator,
        "first_response_separator":first_response_separator,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_live_actions":8,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; three exact-equal snapshot pairs S0/SA, SB/SC, SD/SE; common suffixes of depth 0..2 over A/B/C/D/E plus all 36 observed target-bar centers; every suffix followed by terminal A unless progress/game-over occurs early; protected separator requires PROGRESS/GAME_OVER/CONTINUE divergence and two independent replays; raw screen divergence is diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_FUTURE_SEPARATOR_EQUAL_SNAPSHOTS_G3="+status)


if __name__=="__main__":
    main()
