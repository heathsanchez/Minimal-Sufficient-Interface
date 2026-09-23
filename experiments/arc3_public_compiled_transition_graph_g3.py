from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-compiled-transition-graph-g3"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

MODES=[
    "pair_graph",
    "pair_graph_reflexive",
    "seen_clique",
    "seen_clique_reflexive",
    "replacement_forward",
    "replacement_reverse",
    "replacement_symmetric",
    "state_transition_operator",
]


def selected_pair(f):
    rows,source,_=sem.semantic_surface(f)
    active=tuple(i for i,b in enumerate(source) if b)
    if len(active)!=2:
        raise AssertionError(f"expected active pair, got {active}")
    return rows,active


def compile_relation(history, mode):
    rel=set()
    seen=set()
    for p in history:
        seen.update(p)

    if mode.startswith("pair_graph"):
        for a,b in history:
            rel.add((a,b)); rel.add((b,a))
        if mode.endswith("reflexive"):
            for x in seen: rel.add((x,x))

    elif mode.startswith("seen_clique"):
        for i in seen:
            for j in seen:
                if i!=j or mode.endswith("reflexive"):
                    rel.add((i,j))

    elif mode in ("replacement_forward","replacement_reverse","replacement_symmetric","state_transition_operator"):
        # Only changes between successive distinct pair states carry replacement meaning.
        prev=history[0]
        for cur in history[1:]:
            if cur==prev:
                if mode=="state_transition_operator":
                    for x in cur:
                        rel.add((x,x))
                continue
            old=set(prev); new=set(cur)
            removed=sorted(old-new)
            added=sorted(new-old)
            kept=sorted(old&new)
            if len(removed)!=1 or len(added)!=1:
                raise AssertionError(f"non-single replacement {prev}->{cur}")
            r=removed[0]; a=added[0]
            if mode=="replacement_forward":
                rel.add((r,a))
            elif mode=="replacement_reverse":
                rel.add((a,r))
            elif mode=="replacement_symmetric":
                rel.add((r,a)); rel.add((a,r))
            elif mode=="state_transition_operator":
                for x in kept: rel.add((x,x))
                rel.add((r,a))
            prev=cur
    else:
        raise ValueError(mode)

    return rel


def write_relation(e, rel):
    rows,source,targets=sem.semantic_surface(e.observation_space)
    actions=[]
    desired=[[1 if (i,j) in rel else 0 for j in range(6)] for i in range(6)]
    for i in range(6):
        for j in range(6):
            cur=sem.bit(targets[i][j]["color"])
            want=desired[i][j]
            if cur==want:
                continue
            rc=tuple(targets[i][j]["rc"])
            z=ab.click(e,rc)
            actions.append({"i":i,"j":j,"rc":list(rc),"before":cur,"want":want})
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                return actions,desired
    return actions,desired


def run_variant(prefix_len, mode):
    e,trace=g3.enter_level3()
    rows,p0=selected_pair(e.observation_space)
    history=[p0]

    for name,rc in KNOWN[:prefix_len]:
        z=ab.click(e,rc)
        _,p=selected_pair(e.observation_space) if z.state==GameState.NOT_FINISHED and int(z.levels_completed)==2 else (rows,p0)
        history.append(p)
        trace.append({
            "phase":"observe-generator",
            "name":name,"rc":list(rc),
            "pair":list(p),
            "level":int(z.levels_completed),"state":str(z.state),
        })
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {
                "prefix_len":prefix_len,"mode":mode,"history":[list(x) for x in history],
                "progressed":int(z.levels_completed)>2 or z.state==GameState.WIN,
                "level":int(z.levels_completed),"state":str(z.state),"early":True,"trace":trace,
            }

    rel=compile_relation(history,mode)
    actions,desired=write_relation(e,rel)
    if int(e.observation_space.levels_completed)==2 and e.observation_space.state==GameState.NOT_FINISHED:
        z=ab.click(e,A)
        trace.append({
            "phase":"submit","name":"A","rc":list(A),
            "level":int(z.levels_completed),"state":str(z.state),
        })

    return {
        "prefix_len":prefix_len,
        "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:prefix_len]],
        "mode":mode,
        "history":[list(x) for x in history],
        "relation_edges":[list(x) for x in sorted(rel)],
        "desired_relation":desired,
        "write_count":len(actions),
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "trace":trace,
    }


def main():
    tested=[]
    selected=None
    verification=[]

    for k in range(len(KNOWN)+1):
        for mode in MODES:
            row=run_variant(k,mode)
            tested.append({
                "prefix_len":k,
                "mode":mode,
                "history":row.get("history"),
                "relation_edges":row.get("relation_edges"),
                "write_count":row.get("write_count"),
                "progressed":row.get("progressed"),
                "level":row.get("level"),
                "state":row.get("state"),
            })
            if row.get("progressed"):
                vv=[run_variant(k,mode),run_variant(k,mode)]
                if all(x.get("progressed") for x in vv):
                    selected={
                        "prefix_len":k,
                        "prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                        "mode":mode,
                        "history":row["history"],
                        "relation_edges":row["relation_edges"],
                        "write_count":row["write_count"],
                    }
                    verification=vv
                    break
        if selected is not None:
            break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_semantic_relation_head":"8fd8f3f57d88f1cc70de1abfb0525df50f1f70b0",
        "parent_semantic_relation_run":35930578306,
        "hypothesis":"G3 target is the relation/operator compiled from the observed sequence of two-active-row source states, not a static function of the final predicate",
        "modes":MODES,
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; pair states are observed after each known A/B/C/D/E generator action; only eight small graph/operator compilers are tested; target rows/columns use the same six geometric identities; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_COMPILED_TRANSITION_GRAPH_G3="+status)


if __name__=="__main__":
    main()
