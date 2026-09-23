from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
from typing import Iterable

from arcengine import GameState

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-future-separator-predicate-quotient-g3"
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
    for name,rc in KNOWN[:k]:
        z=ab.click(e,rc)
        if protected(z)!="CONTINUE":
            break
    rows,source,targets=sem.semantic_surface(e.observation_space)
    return e,rows,list(source),targets


def target_centers():
    e,rows,source,targets=replay_prefix(0)
    out=[]
    for i,r in enumerate(rows):
        for j,t in enumerate(targets[i]):
            out.append((f"T{i}{j}",tuple(t["rc"])))
    return out


def alphabet():
    seen=set(); out=[]
    for name,rc in KNOWN+target_centers():
        if rc in seen:
            continue
        seen.add(rc); out.append((name,rc))
    return out


def panel_signature(targets):
    return [[sem.bit(x["color"]) for x in row] for row in targets]


def execute(k:int,suffix:Iterable[tuple[str,tuple[int,int]]]):
    e,rows,source,targets=replay_prefix(k)
    before_hash=frame_hash(e.observation_space)
    before_panel=panel_signature(targets)
    for name,rc in suffix:
        z=ab.click(e,rc)
        po=protected(z)
        if po!="CONTINUE":
            return {
                "prefix_len":k,
                "source_predicate":source,
                "before_hash":before_hash,
                "before_panel":before_panel,
                "after_suffix_hash":frame_hash(e.observation_space),
                "outcome":po,
            }

    after_hash=frame_hash(e.observation_space)
    z=ab.click(e,A)
    return {
        "prefix_len":k,
        "source_predicate":source,
        "before_hash":before_hash,
        "before_panel":before_panel,
        "after_suffix_hash":after_hash,
        "outcome":protected(z),
    }


def suffixes(alpha):
    yield ()
    for depth in range(1,MAX_DEPTH+1):
        for seq in itertools.product(alpha,repeat=depth):
            yield seq


def compact(seq):
    return [{"name":n,"rc":list(rc)} for n,rc in seq]


def verify(l,r,seq):
    out=[]
    for _ in range(2):
        L=execute(l,seq); R=execute(r,seq)
        out.append({"left":L["outcome"],"right":R["outcome"]})
    return out


def main():
    alpha=alphabet()
    quotient_pairs=[]
    for label,l,r in PAIR_PREFIXES:
        le,lrows,lsrc,ltgt=replay_prefix(l)
        re,rrows,rsrc,rtgt=replay_prefix(r)
        if lsrc!=rsrc:
            raise AssertionError(f"{label} not merged by source-predicate quotient")
        quotient_pairs.append({
            "pair":label,
            "left_prefix":l,
            "right_prefix":r,
            "source_predicate":lsrc,
            "full_frame_equal":frame_hash(le.observation_space)==frame_hash(re.observation_space),
            "target_panel_equal":panel_signature(ltgt)==panel_signature(rtgt),
        })

    protected_separator=None
    first_response_separator=None
    evaluations=0
    suffix_counts={str(i):0 for i in range(MAX_DEPTH+1)}

    for label,l,r in PAIR_PREFIXES:
        for seq in suffixes(alpha):
            suffix_counts[str(len(seq))]+=1
            L=execute(l,seq); R=execute(r,seq)
            evaluations+=2
            if first_response_separator is None and L["after_suffix_hash"]!=R["after_suffix_hash"]:
                first_response_separator={
                    "pair":label,
                    "left_prefix":l,
                    "right_prefix":r,
                    "suffix":compact(seq),
                    "left_outcome":L["outcome"],
                    "right_outcome":R["outcome"],
                }

            if L["outcome"]!=R["outcome"]:
                vv=verify(l,r,seq)
                if all(x["left"]!=x["right"] for x in vv):
                    protected_separator={
                        "pair":label,
                        "left_prefix":l,
                        "right_prefix":r,
                        "suffix":compact(seq),
                        "left_outcome":L["outcome"],
                        "right_outcome":R["outcome"],
                        "verification":vv,
                    }
                    break
        if protected_separator is not None:
            break

    status=(
        "PROTECTED_SEPARATOR" if protected_separator is not None
        else "RESPONSE_SEPARATOR_ONLY" if first_response_separator is not None
        else "NO_SEPARATOR"
    )

    out={
        "status":status,
        "parent_failed_exact_equality_head":"83a1dd2aace1a86bb32033bb439237095046910b",
        "diagnostic_head":"c9bbfdb1678d55628bcaab3bb4c402dee979790b",
        "hypothesis":"states merged by the six-row source-predicate quotient may have different protected lawful futures even when their full frames differ elsewhere; a common suffix can falsify that quotient on protected consequence",
        "quotient_pairs":quotient_pairs,
        "alphabet":[{"name":n,"rc":list(rc)} for n,rc in alpha],
        "alphabet_size":len(alpha),
        "max_suffix_depth":MAX_DEPTH,
        "tested_suffix_counts":suffix_counts,
        "candidate_evaluations":evaluations,
        "protected_separator":protected_separator,
        "first_response_separator":first_response_separator,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_live_actions":8,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; compare pairs merged only by the six-row source-predicate quotient, not by full-frame equality; common suffixes depth 0..2 over A/B/C/D/E plus all 36 target centers, followed by terminal A; only stable PROGRESS/GAME_OVER/CONTINUE divergence is a protected separator; visible/frame divergence is diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_FUTURE_SEPARATOR_PREDICATE_QUOTIENT_G3="+status)


if __name__=="__main__":
    main()
