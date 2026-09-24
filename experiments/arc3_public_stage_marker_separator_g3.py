from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

import arc3_public_future_separator_predicate_quotient_g3 as q

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-stage-marker-separator-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

MARKERS=[
    ("M61",(1,61)),
    ("M59",(1,59)),
    ("M57",(1,57)),
]
MAX_DEPTH=2


def alphabet():
    base=q.alphabet()
    seen={rc for _,rc in base}
    out=list(base)
    for name,rc in MARKERS:
        if rc not in seen:
            seen.add(rc)
            out.append((name,rc))
    return out


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
        L=q.execute(l,seq)
        R=q.execute(r,seq)
        out.append({"left":L["outcome"],"right":R["outcome"]})
    return out


def main():
    alpha=alphabet()
    quotient_pairs=[]
    for label,l,r in q.PAIR_PREFIXES:
        le,lrows,lsrc,ltgt=q.replay_prefix(l)
        re,rrows,rsrc,rtgt=q.replay_prefix(r)
        if lsrc!=rsrc:
            raise AssertionError(f"{label} not merged by source-predicate quotient")
        quotient_pairs.append({
            "pair":label,
            "left_prefix":l,
            "right_prefix":r,
            "source_predicate":lsrc,
            "full_frame_equal":q.frame_hash(le.observation_space)==q.frame_hash(re.observation_space),
            "target_panel_equal":q.panel_signature(ltgt)==q.panel_signature(rtgt),
        })

    protected_separator=None
    first_response_separator=None
    marker_response_separators=[]
    evaluations=0
    suffix_counts={str(i):0 for i in range(MAX_DEPTH+1)}

    for label,l,r in q.PAIR_PREFIXES:
        for seq in suffixes(alpha):
            suffix_counts[str(len(seq))]+=1
            L=q.execute(l,seq)
            R=q.execute(r,seq)
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

            if seq and any(name.startswith("M") for name,_ in seq):
                if L["after_suffix_hash"]!=R["after_suffix_hash"] and len(marker_response_separators)<20:
                    marker_response_separators.append({
                        "pair":label,
                        "suffix":compact(seq),
                        "left_outcome":L["outcome"],
                        "right_outcome":R["outcome"],
                    })

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
        "parent_head":"7b28980f46f57d7429eb72cadc91c19e29701e24",
        "parent_run":35934455405,
        "hypothesis":"the three one-pixel stage markers omitted by the source-predicate quotient may be causally actionable; adding them to the common-suffix alphabet should reveal any protected continuation difference they control",
        "markers":[{"name":n,"rc":list(rc)} for n,rc in MARKERS],
        "quotient_pairs":quotient_pairs,
        "alphabet":[{"name":n,"rc":list(rc)} for n,rc in alpha],
        "alphabet_size":len(alpha),
        "max_suffix_depth":MAX_DEPTH,
        "tested_suffix_counts":suffix_counts,
        "candidate_evaluations":evaluations,
        "protected_separator":protected_separator,
        "first_response_separator":first_response_separator,
        "marker_response_separators":marker_response_separators,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_live_actions":8,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; compare three states merged by six-row source-predicate quotient; common suffixes depth 0..2 over prior 41-action alphabet plus the three diagnosed one-pixel marker coordinates (1,61),(1,59),(1,57), followed by terminal A; only stable PROGRESS/GAME_OVER/CONTINUE divergence is protected evidence; screen divergence remains diagnostic",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_STAGE_MARKER_SEPARATOR_G3="+status)


if __name__=="__main__":
    main()
