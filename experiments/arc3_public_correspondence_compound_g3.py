from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-correspondence-compound-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def bars(f):
    rows=[]
    for comp in ab.comps(f):
        if comp["size"]!=3 or comp["color"] not in (1,5):
            continue
        rc=comp["cells"][len(comp["cells"])//2]
        rows.append({"rc":rc,"color":comp["color"]})
    return sorted(rows,key=lambda x:x["rc"])


def panel_groups(f):
    xs=bars(f)
    left=[x for x in xs if x["rc"][1] < 31]
    right=[x for x in xs if x["rc"][1] >= 31]
    return left,right


def pair_observed_panels(f):
    left,right=panel_groups(f)
    if not left or not right:
        return None,{"reason":"missing_side","left":len(left),"right":len(right)}
    L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    if sorted(L)!=sorted(R):
        return None,{"reason":"row_keys","left_rows":sorted(L),"right_rows":sorted(R),
                     "left":len(left),"right":len(right)}
    pairs=[]
    for r in sorted(L):
        l=sorted(L[r],key=lambda x:x["rc"][1]); q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=len(q):
            return None,{"reason":"row_arity","row":r,"left_n":len(l),"right_n":len(q),
                         "left":len(left),"right":len(right)}
        for a,b in zip(l,q): pairs.append({"left":a,"right":b})
    return pairs,{"left":len(left),"right":len(right),"rows":sorted(L)}


def solve_g2(e):
    # G1 compiled capability.
    ab.enter2(e)
    if int(e.observation_space.levels_completed)!=1:
        raise AssertionError("failed to enter G2")

    # Qualified G2 generator prefix.
    for rc in (A,B,C):
        z=ab.click(e,rc)
        if z is None or z.state==GameState.GAME_OVER: raise RuntimeError("G2 prefix failure")

    pairs,meta=pair_observed_panels(e.observation_space)
    if pairs is None or len(pairs)!=24:
        raise AssertionError(f"G2 panel relation unavailable: {meta}")
    mismatch=[p for p in pairs if p["left"]["color"]!=p["right"]["color"]]
    if len(mismatch)!=8:
        raise AssertionError(f"expected G2 mismatch 8, got {len(mismatch)}")
    for p in mismatch:
        z=ab.click(e,tuple(p["right"]["rc"]))
        if z is None or z.state==GameState.GAME_OVER: raise RuntimeError("G2 match failure")
    pairs2,_=pair_observed_panels(e.observation_space)
    if any(p["left"]["color"]!=p["right"]["color"] for p in pairs2):
        raise AssertionError("G2 correspondence did not close")
    z=ab.click(e,A)
    if int(z.levels_completed)!=2:
        raise AssertionError(f"qualified G2 law failed to compound, levels={z.levels_completed}")


def make_g3():
    e=ab.env();solve_g2(e)
    return e


def try_variant(k):
    e=make_g3();trace=[]
    start=int(e.observation_space.levels_completed)
    for name,rc in KNOWN[:k]:
        z=ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"prefix_len":k,"early_progress":int(z.levels_completed)>start or z.state==GameState.WIN,
                    "level":int(z.levels_completed),"state":str(z.state),"trace":trace}

    pairs,meta=pair_observed_panels(e.observation_space)
    row={"prefix_len":k,"panel_meta":meta,"trace":trace}
    if pairs is None:
        row.update({"progressed":False,"reason":"no_correspondence_surface",
                    "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)})
        return row

    mismatch=[p for p in pairs if p["left"]["color"]!=p["right"]["color"]]
    row["pair_count"]=len(pairs);row["mismatch_count"]=len(mismatch)
    actions=[]
    for p in mismatch:
        rc=tuple(p["right"]["rc"])
        z=ab.click(e,rc)
        actions.append(list(rc))
        trace.append({"name":"match-right","rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    row["match_actions"]=actions

    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        p2,_=pair_observed_panels(e.observation_space)
        if p2 is not None:
            row["remaining_mismatch"]=sum(1 for p in p2 if p["left"]["color"]!=p["right"]["color"])
        z=ab.click(e,A)
        trace.append({"name":"terminal:A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})

    row.update({"progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
                "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)})
    return row


def verify(k):
    return [try_variant(k),try_variant(k)]


def main():
    # Census exact G3 start before applying any new law.
    e=make_g3()
    left,right=panel_groups(e.observation_space)
    start_census={
        "levels_completed":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "bar_count":len(left)+len(right),
        "left_bars":len(left),"right_bars":len(right),
        "left_colors":{"blue":sum(x["color"]==1 for x in left),"gray":sum(x["color"]==5 for x in left)},
        "right_colors":{"blue":sum(x["color"]==1 for x in right),"gray":sum(x["color"]==5 for x in right)}
    }

    variants=[];selected=None;verification=[]
    for k in range(0,len(KNOWN)+1):
        row=try_variant(k);variants.append(row)
        if row.get("progressed") or row.get("early_progress"):
            vv=verify(k)
            if all(x.get("progressed") or x.get("early_progress") for x in vv):
                selected={"prefix_len":k,"known_prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]]}
                verification=vv;break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "compiled_prefix":{"G1":"qualified fixed 9-action program","G2":"A,B,C -> exact observed panel correspondence -> A"},
        "g3_start_census":start_census,
        "known_g3_probe_prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN],
        "variants":variants,"selected":selected,"verification":verification,
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"hard-restart exact public tn36: replay qualified G1 then qualified dynamic G2 correspondence solver; on G3 reuse only observed left/right size-3 panel row/rank correspondence across prefixes of known A/B/C/D/E probes; no model calls or game-source inspection"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_CORRESPONDENCE_COMPOUND_G3="+status)


if __name__=="__main__":main()
