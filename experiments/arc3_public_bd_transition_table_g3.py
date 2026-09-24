from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-bd-transition-table-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
OPS=[("B",B),("D",D)]

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return [[int(v) for v in row] for row in x]

def left_hash(f):
    g=grid(f)
    crop=[row[:31] for row in g]
    return hashlib.sha256(json.dumps(crop,separators=(",",":")).encode()).hexdigest()

def state_sig(f):
    rows,src,targets=sem.semantic_surface(f)
    panel=[[sem.bit(x["color"]) for x in row] for row in targets]
    return {
        "rows":rows,
        "source":list(src),
        "target_panel":panel,
        "left_hash":left_hash(f),
    }

def replay_prefix(k):
    e,_=g3.enter_level3()
    for name,rc in KNOWN[:k]:
        ab.click(e,rc)
    return e

def protected(f):
    if int(f.levels_completed)>2 or str(f.state).endswith("WIN"):
        return "PROGRESS"
    if str(f.state).endswith("GAME_OVER"):
        return "GAME_OVER"
    return "CONTINUE"

def main():
    rows=[]
    for k in range(6):
        e0=replay_prefix(k)
        before=state_sig(e0.observation_space)
        for opname,rc in OPS:
            e=replay_prefix(k)
            b=state_sig(e.observation_space)
            z=ab.click(e,rc)
            a=state_sig(e.observation_space)
            rows.append({
                "prefix_len":k,
                "prefix":[name for name,_ in KNOWN[:k]],
                "op":opname,
                "before_source":b["source"],
                "after_source":a["source"],
                "source_changed":b["source"]!=a["source"],
                "before_left_hash":b["left_hash"],
                "after_left_hash":a["left_hash"],
                "left_changed":b["left_hash"]!=a["left_hash"],
                "target_panel_changed":b["target_panel"]!=a["target_panel"],
                "outcome":protected(z),
            })

    paired=[]
    for left,right in ((0,1),(2,3),(4,5)):
        for opname,_ in OPS:
            a=next(x for x in rows if x["prefix_len"]==left and x["op"]==opname)
            b=next(x for x in rows if x["prefix_len"]==right and x["op"]==opname)
            paired.append({
                "pair":[left,right],
                "op":opname,
                "same_before_source":a["before_source"]==b["before_source"],
                "same_after_source":a["after_source"]==b["after_source"],
                "same_outcome":a["outcome"]==b["outcome"],
                "same_left_response":a["after_left_hash"]==b["after_left_hash"],
                "left_after_source":a["after_source"],
                "right_after_source":b["after_source"],
            })

    out={
        "status":"DIAGNOSTIC",
        "parent_head":"38d5c9768ed15a246ca775cde9dcf5b31fcf5c2c",
        "parent_run":35947695990,
        "hypothesis":"B and D are the only source-transforming G3 generator operations; test whether the six-row source predicate alone determines their structural future response across marker-equivalent stages",
        "rows":rows,
        "paired_equivalence_checks":paired,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; prefixes 0..5 of canonical A/B/C/D/E; independently apply B and D once from each prefix; compare source-predicate, left-region response, target panel and protected outcome; diagnostic only",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_BD_TRANSITION_TABLE_G3=DIAGNOSTIC")

if __name__=="__main__":
    main()
