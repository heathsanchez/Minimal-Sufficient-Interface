from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g2 as g2
import arc3_public_all_blue_to_gray_g2 as ab

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-panel-correspondence-g3"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def enter_level3():
    # enter exact public level 2 using the known G1 solution
    e=ab.env()
    ab.enter2(e)

    # apply the qualified G2 law exactly: generate with A,B,C,
    # make right panel color-correspondent to left, submit A.
    trace=[]
    for name,rc in [("A",A),("B",B),("C",C)]:
        z=ab.click(e,rc)
        trace.append({"phase":"g2-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
    mismatches,actions,remaining=g2.match_right_to_left(e,trace)
    if remaining != 0:
        raise AssertionError(f"G2 correspondence failed: {remaining}")
    z=ab.click(e,A)
    trace.append({"phase":"g2-submit","name":"A","rc":list(A),
                  "level":int(z.levels_completed),"state":str(z.state)})
    if int(z.levels_completed) != 2 or z.state != GameState.NOT_FINISHED:
        raise AssertionError(f"expected level3 start after G2, got {z.levels_completed} {z.state}")
    return e,trace


def size3_by_side(f):
    left=[]; right=[]
    for comp in ab.comps(f):
        if comp["size"] != 3 or comp["color"] not in (1,5):
            continue
        rc=comp["cells"][len(comp["cells"])//2]
        row={"rc":rc,"color":comp["color"]}
        if rc[1] < 31:
            left.append(row)
        else:
            right.append(row)
    return sorted(left,key=lambda x:x["rc"]), sorted(right,key=lambda x:x["rc"])


def pair_observed_panels(f):
    left,right=size3_by_side(f)
    L=defaultdict(list); R=defaultdict(list)
    for x in left: L[x["rc"][0]].append(x)
    for x in right: R[x["rc"][0]].append(x)

    # Keep only rows that have equal nonzero arity on both sides.
    common=[]
    for r in sorted(set(L)&set(R)):
        if len(L[r]) == len(R[r]) and len(L[r]) > 0:
            common.append(r)

    if not common:
        raise AssertionError(
            f"no row/rank panel correspondence: left={len(left)} right={len(right)} "
            f"Lrows={dict((k,len(v)) for k,v in L.items())} "
            f"Rrows={dict((k,len(v)) for k,v in R.items())}"
        )

    pairs=[]
    for r in common:
        l=sorted(L[r],key=lambda x:x["rc"][1])
        q=sorted(R[r],key=lambda x:x["rc"][1])
        for a,b in zip(l,q):
            pairs.append({"left":a,"right":b})

    return {
        "left_count":len(left),
        "right_count":len(right),
        "paired_rows":common,
        "pair_count":len(pairs),
        "pairs":pairs,
    }


def apply_correspondence(e,trace):
    panel=pair_observed_panels(e.observation_space)
    mismatches=[p for p in panel["pairs"] if p["left"]["color"] != p["right"]["color"]]
    actions=[]
    for p in mismatches:
        rc=tuple(p["right"]["rc"])
        before=p["right"]["color"]
        want=p["left"]["color"]
        z=ab.click(e,rc)
        actions.append({"rc":list(rc),"before":before,"want":want})
        trace.append({"phase":"g3-match","rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break

    if e.observation_space.state == GameState.NOT_FINISHED:
        final=pair_observed_panels(e.observation_space)
        remaining=sum(
            1 for p in final["pairs"]
            if p["left"]["color"] != p["right"]["color"]
        )
    else:
        final=panel
        remaining=None

    return panel,mismatches,actions,remaining


def run_variant(prefix,submit=True):
    e,trace=enter_level3()
    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"phase":"g3-prefix","name":name,"rc":list(rc),
                      "level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "progressed": int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),
                "early":True,"trace":trace,
            }

    try:
        panel,mismatches,actions,remaining=apply_correspondence(e,trace)
    except AssertionError as ex:
        left,right=size3_by_side(e.observation_space)
        return {
            "progressed":False,
            "reason":"no_observed_panel_correspondence",
            "error":str(ex),
            "left_count":len(left),
            "right_count":len(right),
            "trace":trace,
        }

    if remaining not in (0,None):
        return {
            "progressed":False,
            "reason":"failed_exact_match",
            "panel":{"left_count":panel["left_count"],"right_count":panel["right_count"],
                     "paired_rows":panel["paired_rows"],"pair_count":panel["pair_count"]},
            "mismatch_count":len(mismatches),
            "remaining":remaining,
            "trace":trace,
        }

    if submit and e.observation_space.state == GameState.NOT_FINISHED:
        z=ab.click(e,A)
        trace.append({"phase":"g3-submit","name":"A","rc":list(A),
                      "level":int(z.levels_completed),"state":str(z.state)})

    return {
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "panel":{"left_count":panel["left_count"],"right_count":panel["right_count"],
                 "paired_rows":panel["paired_rows"],"pair_count":panel["pair_count"]},
        "mismatch_count":len(mismatches),
        "match_actions":actions,
        "remaining_mismatch":remaining,
        "trace":trace,
    }


def main():
    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    variants=[]
    selected=None
    verification=[]

    for i,prefix in enumerate(prefixes):
        row=run_variant(prefix)
        row["variant"]=i
        row["prefix"]=[{"name":n,"rc":list(rc)} for n,rc in prefix]
        variants.append(row)
        if row.get("progressed"):
            vv=[run_variant(prefix),run_variant(prefix)]
            if all(x.get("progressed") for x in vv):
                selected={
                    "variant":i,
                    "prefix":row["prefix"],
                    "mismatch_count":row.get("mismatch_count"),
                    "panel":row.get("panel"),
                }
                verification=vv
                break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_g2_head":"d292d799bf4f67faba95ca4f26ad2e1677f46055",
        "parent_g2_run":35926523909,
        "hypothesis":"reuse the qualified generate-observe-write-verify panel-correspondence law unchanged at the next public tn36 level, deriving panel dimensions only from observed geometry",
        "known_prefix_actions":[{"name":n,"rc":list(rc)} for n,rc in KNOWN],
        "variants":variants,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G3 continuation from qualified G2 solver; observed size-3 color-1/5 bars are paired only by shared row and within-row rank; only right-side mismatches are toggled; terminal A verified twice on progress",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PANEL_CORRESPONDENCE_G3="+status)


if __name__=="__main__":
    main()
