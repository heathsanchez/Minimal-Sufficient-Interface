from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-source-delta-trace-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

DELTA_KINDS=["xor","on","off"]
FIRST_COL=["state","zero"]
TIME_ORDERS=["forward","reverse"]

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def source_bits(f):
    rows,src,targets=sem.semantic_surface(f)
    return rows,list(src),targets

def collect_trace():
    e,_=g3.enter_level3()
    rows,s0,targets=source_bits(e.observation_space)
    states=[s0]
    trace=[{"stage":"initial","state":s0}]
    for name,rc in KNOWN:
        z=ab.click(e,rc)
        rows2,s,_=source_bits(e.observation_space)
        if rows2!=rows:
            raise AssertionError("row identity changed")
        states.append(s)
        trace.append({
            "stage":name,
            "state":s,
            "level":int(z.levels_completed),
            "game_state":str(z.state),
        })
        if protected(z)!="CONTINUE":
            raise AssertionError(f"generator unexpectedly terminated at {name}")
    if len(states)!=6:
        raise AssertionError(states)
    return e,rows,states,trace

def delta(a,b,kind):
    if kind=="xor":
        return [int(x!=y) for x,y in zip(a,b)]
    if kind=="on":
        return [int(x==0 and y==1) for x,y in zip(a,b)]
    if kind=="off":
        return [int(x==1 and y==0) for x,y in zip(a,b)]
    raise ValueError(kind)

def compile_matrix(states,kind,first_col,time_order):
    cols=[]
    cols.append(list(states[0]) if first_col=="state" else [0]*6)
    for i in range(1,len(states)):
        cols.append(delta(states[i-1],states[i],kind))
    if time_order=="reverse":
        cols=list(reversed(cols))
    M=[[cols[j][i] for j in range(6)] for i in range(6)]
    return cols,M

def write_matrix(e,M,complement):
    rows,src,targets=source_bits(e.observation_space)
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
            if protected(z)!="CONTINUE":
                return actions
    return actions

def run_variant(kind,first_col,time_order,complement):
    e,rows,states,trace=collect_trace()
    cols,M=compile_matrix(states,kind,first_col,time_order)
    actions=write_matrix(e,M,complement)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "kind":kind,
        "first_col":first_col,
        "time_order":time_order,
        "complement":complement,
        "states":states,
        "columns":cols,
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

    for kind in DELTA_KINDS:
        for first_col in FIRST_COL:
            for time_order in TIME_ORDERS:
                for complement in (False,True):
                    row=run_variant(kind,first_col,time_order,complement)
                    tested.append({
                        "kind":kind,
                        "first_col":first_col,
                        "time_order":time_order,
                        "complement":complement,
                        "columns":row["columns"],
                        "write_count":row["write_count"],
                        "progressed":row["progressed"],
                        "outcome":row["outcome"],
                        "level":row["level"],
                    })
                    if row["progressed"]:
                        vv=[run_variant(kind,first_col,time_order,complement),run_variant(kind,first_col,time_order,complement)]
                        if all(x["progressed"] for x in vv):
                            selected={
                                "kind":kind,
                                "first_col":first_col,
                                "time_order":time_order,
                                "complement":complement,
                                "columns":row["columns"],
                                "write_count":row["write_count"],
                            }
                            verification=vv
                            break
                if selected: break
            if selected: break
        if selected: break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "parent_directed_edge_head":"8deef2f9f45ce3a4e7bec4bc25a3f0c13b354a96",
        "parent_directed_edge_run":35951703611,
        "hypothesis":"the five adjacent top-stage markers license a six-stage temporal axis (initial,A,B,C,D,E); after direct snapshot encoding failed, the target may encode the discrete derivative of the six-row source predicate over those stages",
        "delta_kinds":DELTA_KINDS,
        "first_column_conventions":FIRST_COL,
        "time_orders":TIME_ORDERS,
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; generate the canonical A/B/C/D/E stage sequence and observe all six source predicates; target columns are only state-plus-delta or zero-plus-delta under xor/on/off change semantics, forward/reverse order, direct/complement color; submit A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SOURCE_DELTA_TRACE_G3="+status)

if __name__=="__main__":
    main()
