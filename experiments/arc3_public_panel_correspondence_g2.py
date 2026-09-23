from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-panel-correspondence-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def size3_by_side(f):
    left=[];right=[]
    for comp in ab.comps(f):
        if comp["size"]!=3 or comp["color"] not in (1,5):
            continue
        rc=comp["cells"][len(comp["cells"])//2]
        row={"rc":rc,"color":comp["color"]}
        if rc[1] < 31: left.append(row)
        elif rc[1] >=31: right.append(row)
    return sorted(left,key=lambda x:x["rc"]),sorted(right,key=lambda x:x["rc"])


def pair_panels(f):
    left,right=size3_by_side(f)
    if len(left)!=24 or len(right)!=24:
        raise AssertionError(f"expected 24/24 segment bars, got {len(left)}/{len(right)}")
    # Pair by rank within each row: six rows x four bars. This uses only observed geometry.
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    if sorted(L)!=sorted(R):
        raise AssertionError(f"row mismatch {sorted(L)} vs {sorted(R)}")
    pairs=[]
    for r in sorted(L):
        l=sorted(L[r],key=lambda x:x["rc"][1]); q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=4: raise AssertionError("expected four bars per row")
        for a,b in zip(l,q):
            pairs.append({"left":a,"right":b})
    return pairs


def replay(prefix):
    e=ab.env();ab.enter2(e);trace=[]
    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER): break
    return e,trace


def match_right_to_left(e,trace):
    pairs=pair_panels(e.observation_space)
    mismatches=[p for p in pairs if p["left"]["color"]!=p["right"]["color"]]
    actions=[]
    for p in mismatches:
        rc=tuple(p["right"]["rc"])
        before_left=p["left"]["color"];before_right=p["right"]["color"]
        z=ab.click(e,rc)
        actions.append({"rc":list(rc),"left_color":before_left,"right_before":before_right})
        trace.append({"name":"match-right","rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    final_pairs=pair_panels(e.observation_space) if e.observation_space.state==GameState.NOT_FINISHED else []
    remaining=sum(1 for p in final_pairs if p["left"]["color"]!=p["right"]["color"])
    return mismatches,actions,remaining


def run_variant(prefix,submit=True):
    e,trace=replay(prefix)
    if int(e.observation_space.levels_completed)>1 or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
        return {"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                "trace":trace,"early":True}
    before_pairs=pair_panels(e.observation_space)
    before_left=[[p["left"]["rc"],p["left"]["color"]] for p in before_pairs]
    before_right=[[p["right"]["rc"],p["right"]["color"]] for p in before_pairs]
    mismatches,actions,remaining=match_right_to_left(e,trace)
    if remaining!=0:
        return {"progressed":False,"trace":trace,"reason":"failed_exact_match","remaining":remaining}
    if submit and e.observation_space.state==GameState.NOT_FINISHED:
        z=ab.click(e,A)
        trace.append({"name":"terminal:A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})
    return {
        "progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
        "mismatch_count":len(mismatches),"match_actions":actions,"remaining_mismatch":remaining,
        "left_snapshot":before_left,"right_snapshot":before_right,"trace":trace
    }


def main():
    variants=[]
    prefixes=[[]]
    for k in range(1,len(KNOWN)+1):
        prefixes.append(KNOWN[:k])

    selected=None;verification=[]
    for i,prefix in enumerate(prefixes):
        row=run_variant(prefix)
        row["variant"]=i
        row["prefix"]=[{"name":n,"rc":list(rc)} for n,rc in prefix]
        variants.append(row)
        if row.get("progressed"):
            vv=[run_variant(prefix),run_variant(prefix)]
            if all(x.get("progressed") for x in vv):
                selected={"variant":i,"prefix":row["prefix"],"mismatch_count":row.get("mismatch_count")}
                verification=vv
                break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "hypothesis":"the generated left 6x4 segment panel is the source relation and the directly writable right 6x4 panel should be made exactly color-correspondent before submit",
        "known_prefix_actions":[{"name":n,"rc":list(rc)} for n,rc in KNOWN],
        "variants":variants,
        "selected":selected,
        "verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"exact public tn36 G2 geometric row/rank correspondence between observed 6x4 left and right size-3 panels; prefixes are only successive prefixes of known target probes A/B/C/D/E; right panel toggled only where color differs; terminal A verified twice on any progress"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_PANEL_CORRESPONDENCE_G2="+status)


if __name__=="__main__":main()
