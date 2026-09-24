from __future__ import annotations

import json
import os
from pathlib import Path

import arc3_public_future_separator_predicate_quotient_g3 as q
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-stage-marker-effect-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

MARKERS=[("M61",(1,61)),("M59",(1,59)),("M57",(1,57))]

def marker_vals(f):
    g=q.frame_grid(f)
    return {name:g[r][c] for name,(r,c) in MARKERS}

def panel_sig(targets):
    return [[sem.bit(x["color"]) for x in row] for row in targets]

def inspect(prefix_len,name,rc):
    e,rows,src,targets=q.replay_prefix(prefix_len)
    before={
        "source":src,
        "panel":panel_sig(targets),
        "markers":marker_vals(e.observation_space),
        "frame_hash":q.frame_hash(e.observation_space),
    }
    z=ab.click(e,rc)
    rows2,src2,targets2=sem.semantic_surface(e.observation_space)
    after={
        "source":src2,
        "panel":panel_sig(targets2),
        "markers":marker_vals(e.observation_space),
        "frame_hash":q.frame_hash(e.observation_space),
        "outcome":q.protected(z),
        "level":int(z.levels_completed),
        "state":str(z.state),
    }
    return {
        "prefix_len":prefix_len,
        "marker":name,
        "rc":list(rc),
        "source_changed":before["source"]!=after["source"],
        "panel_changed":before["panel"]!=after["panel"],
        "marker_values_changed":before["markers"]!=after["markers"],
        "frame_changed":before["frame_hash"]!=after["frame_hash"],
        "before":before,
        "after":after,
    }

def main():
    rows=[]
    for _,l,r in q.PAIR_PREFIXES:
        for k in (l,r):
            for name,rc in MARKERS:
                rows.append(inspect(k,name,rc))

    out={
        "status":"DIAGNOSTIC",
        "parent_head":"ff8273801039783661302db2bfd9bd4229595fe0",
        "parent_run":35939036882,
        "rows":rows,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3; inspect one-step effect of diagnosed stage-marker coordinates on source predicate, writable 6x6 target panel, marker pixels, full frame and protected outcome for all six relevant prefixes",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_STAGE_MARKER_EFFECT_G3=DIAGNOSTIC")

if __name__=="__main__":
    main()
