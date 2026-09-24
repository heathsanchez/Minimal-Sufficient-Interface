from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-source-automaton-table-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
OPS=[("B",B),("D",D)]

GENS=[
    ("none",[]),
    ("B",[("B",B)]),
    ("BD",[("B",B),("D",D)]),
    ("ABCDE",KNOWN),
]

ORDERINGS=[
    "state_major",
    "op_major",
    "state_major_reverse",
    "op_major_reverse",
]

def source_state(f):
    rows,src,targets=sem.semantic_surface(f)
    return rows,list(src),targets

def replay_prefix(prefix):
    e,_=g3.enter_level3()
    trace=[]
    for name,rc in prefix:
        z=ab.click(e,rc)
        trace.append({"name":name,"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e,trace

def representative_states():
    reps=[]
    for k in (0,2,4):
        e,_=g3.enter_level3()
        for _,rc in KNOWN[:k]:
            ab.click(e,rc)
        rows,src,_=source_state(e.observation_space)
        reps.append((k,src))
    if len({tuple(x[1]) for x in reps})!=3:
        raise AssertionError(f"expected 3 distinct source states, got {reps}")
    return rows,reps

def successor(prefix_len,op):
    e,_=g3.enter_level3()
    for _,rc in KNOWN[:prefix_len]:
        ab.click(e,rc)
    ab.click(e,op)
    _,src,_=source_state(e.observation_space)
    return src

def transition_columns(ordering):
    rows,reps=representative_states()
    data=[]
    for state_idx,(k,src) in enumerate(reps):
        for opname,rc in OPS:
            data.append({
                "state_index":state_idx,
                "representative_prefix_len":k,
                "before":src,
                "op":opname,
                "after":successor(k,rc),
            })

    if ordering.startswith("state_major"):
        ordered=list(data)
    elif ordering.startswith("op_major"):
        ordered=[]
        for opname,_ in OPS:
            ordered.extend([x for x in data if x["op"]==opname])
    else:
        raise ValueError(ordering)

    if ordering.endswith("_reverse"):
        ordered=list(reversed(ordered))

    cols=[x["after"] for x in ordered]
    if len(cols)!=6:
        raise AssertionError(len(cols))
    M=[[cols[j][i] for j in range(6)] for i in range(6)]
    return rows,data,ordered,M

def write_matrix(e,M,complement):
    rows,src,targets=source_state(e.observation_space)
    actions=[]
    for i in range(6):
        for j in range(6):
            want=M[i][j]
            if complement:
                want=1-want
            cur=sem.bit(targets[i][j]["color"])
            if cur==want:
                continue
            rc=tuple(targets[i][j]["rc"])
            z=ab.click(e,rc)
            actions.append({"i":i,"j":j,"rc":list(rc),"before":cur,"want":want})
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                break
        if int(e.observation_space.levels_completed)>2 or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return actions

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def run_variant(gen_name,prefix,ordering,complement):
    e,trace=replay_prefix(prefix)
    rows,data,ordered,M=transition_columns(ordering)
    actions=write_matrix(e,M,complement)
    if protected(e.observation_space)=="CONTINUE":
        z=ab.click(e,A)
        trace.append({"phase":"submit","name":"A","rc":list(A),"level":int(z.levels_completed),"state":str(z.state)})
    return {
        "generation":gen_name,
        "generation_prefix":[{"name":n,"rc":list(rc)} for n,rc in prefix],
        "ordering":ordering,
        "complement":complement,
        "transition_rows":data,
        "ordered_columns":ordered,
        "matrix":M,
        "write_count":len(actions),
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def main():
    tested=[]
    selected=None
    verification=[]

    for gen_name,prefix in GENS:
        for ordering in ORDERINGS:
            for complement in (False,True):
                row=run_variant(gen_name,prefix,ordering,complement)
                tested.append({
                    "generation":gen_name,
                    "ordering":ordering,
                    "complement":complement,
                    "write_count":row["write_count"],
                    "progressed":row["progressed"],
                    "outcome":row["outcome"],
                    "level":row["level"],
                    "columns":[x["after"] for x in row["ordered_columns"]],
                })
                if row["progressed"]:
                    vv=[run_variant(gen_name,prefix,ordering,complement),run_variant(gen_name,prefix,ordering,complement)]
                    if all(x["progressed"] for x in vv):
                        selected={
                            "generation":gen_name,
                            "ordering":ordering,
                            "complement":complement,
                            "columns":[x["after"] for x in row["ordered_columns"]],
                            "write_count":row["write_count"],
                        }
                        verification=vv
                        break
            if selected: break
        if selected: break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "parent_bd_head":"bfb7fc806ae342793abc7a51c69c8972274f14df",
        "parent_bd_run":35947917695,
        "hypothesis":"the G3 6x6 target is the compiled transition table of the 3-state source automaton under its 2 consequential operators B and D; 3 states x 2 operators = 6 target columns",
        "generation_histories":[name for name,_ in GENS],
        "orderings":ORDERINGS,
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":48,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; source automaton states are the three observed six-row predicates at canonical prefixes 0,2,4; operators are B,D; independently derive all 6 successor predicates; encode as target columns under state-major/op-major orders and reversals, direct/complement; test after none/B/BD/ABCDE generation histories; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SOURCE_AUTOMATON_TABLE_G3="+status)

if __name__=="__main__":
    main()
