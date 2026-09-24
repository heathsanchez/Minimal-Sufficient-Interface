from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g2 as g2
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-five-lens-rapid-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
G2_ACTIONS=[("A",A),("B",B),("C",C)]
G3_ACTIONS=[("A",A),("B",B),("C",C),("D",D),("E",E)]

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def source_bits(f):
    L=defaultdict(list)
    for comp in ab.comps(f):
        if comp["size"]!=3 or comp["color"] not in (1,5):
            continue
        cells=sorted(tuple(x) for x in comp["cells"])
        rc=cells[len(cells)//2]
        if rc[1] < 31:
            L[rc[0]].append({"rc":rc,"color":int(comp["color"])})
    rows=sorted(L)
    if len(rows)!=6:
        raise AssertionError(f"expected 6 source rows, got {rows}")
    out=[]
    for r in rows:
        xs=sorted(L[r],key=lambda x:x["rc"][1])
        if not xs:
            raise AssertionError(r)
        colors={x["color"] for x in xs}
        if len(colors)!=1:
            raise AssertionError((r,colors))
        out.append(1 if xs[0]["color"]==5 else 0)
    return rows,out

def right_cols(f):
    cols=set()
    for comp in ab.comps(f):
        if comp["size"]!=3 or comp["color"] not in (1,5):
            continue
        cells=sorted(tuple(x) for x in comp["cells"])
        rc=cells[len(cells)//2]
        if rc[1] >= 31:
            cols.add(rc[1])
    return sorted(cols)

def top_endpoint(f):
    best=None
    for comp in ab.comps(f):
        if int(comp["color"])!=9:
            continue
        cells=[tuple(x) for x in comp["cells"]]
        if not cells or any(r!=1 for r,c in cells):
            continue
        mn=min(c for r,c in cells); mx=max(c for r,c in cells)
        if mn!=1:
            continue
        if best is None or len(cells)>best[0]:
            best=(len(cells),mx)
    if best is None:
        raise AssertionError("no top stage track")
    return best[1]

def enter_g2():
    e=ab.env()
    ab.enter2(e)
    return e

def enter_g3(prefix=None):
    e,_=g3.enter_level3()
    for _,rc in (prefix or []):
        ab.click(e,rc)
    return e

def stage_trace(level):
    if level=="g2":
        e=enter_g2(); actions=G2_ACTIONS
    else:
        e=enter_g3(); actions=G3_ACTIONS
    endpoints=[top_endpoint(e.observation_space)]
    states=[source_bits(e.observation_space)[1]]
    for _,rc in actions:
        ab.click(e,rc)
        endpoints.append(top_endpoint(e.observation_space))
        states.append(source_bits(e.observation_space)[1])
    return endpoints,states,right_cols(e.observation_space)

def intervention_matrix(prefix,slots):
    before_env=enter_g3(prefix)
    rows,before=source_bits(before_env.observation_space)
    cols_after=[]; cols_delta=[]; records=[]
    for slot in slots:
        e=enter_g3(prefix)
        _,b=source_bits(e.observation_space)
        z=ab.click(e,(1,slot))
        _,a=source_bits(e.observation_space)
        d=[int(x!=y) for x,y in zip(b,a)]
        cols_after.append(a)
        cols_delta.append(d)
        records.append({
            "slot":slot,
            "before":b,
            "after":a,
            "delta":d,
            "outcome":protected(z),
        })
    return before,cols_after,cols_delta,records

def cols_to_matrix(cols,reverse=False):
    cc=list(cols)
    if reverse:
        cc=list(reversed(cc))
    if len(cc)!=6 or any(len(x)!=6 for x in cc):
        raise AssertionError((len(cc),cc))
    return [[cc[j][i] for j in range(6)] for i in range(6)]

def write_matrix(e,M,complement=False):
    rows,src,targets=sem.semantic_surface(e.observation_space)
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
            actions.append({"i":i,"j":j,"rc":list(rc),"want":want})
            if protected(z)!="CONTINUE":
                return actions
    return actions

def terminal_variant(prefix,cols,reverse,complement):
    e=enter_g3(prefix)
    M=cols_to_matrix(cols,reverse=reverse)
    actions=write_matrix(e,M,complement=complement)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "reverse":reverse,
        "complement":complement,
        "matrix":M,
        "write_count":len(actions),
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def main():
    # 1 STATIC + 4 TRANSPORT: derive ordered stage-slot systems and target columns in both levels.
    g2_slots,g2_states,g2_cols=stage_trace("g2")
    g3_slots,g3_states,g3_cols=stage_trace("g3")
    transport={
        "g2_stage_slots":g2_slots,
        "g3_stage_slots":g3_slots,
        "g2_target_cols":g2_cols,
        "g3_target_cols":g3_cols,
        "g2_count_match":len(g2_slots)==len(g2_cols)==4,
        "g3_count_match":len(g3_slots)==len(g3_cols)==6,
        "stage_growth":"4->6",
    }

    # 2 COVARIANCE: which stage transitions actually alter the consequential source predicate?
    covariance=[]
    for i,name in enumerate(["A","B","C","D","E"]):
        covariance.append({
            "action":name,
            "slot_from":g3_slots[i],
            "slot_to":g3_slots[i+1],
            "source_before":g3_states[i],
            "source_after":g3_states[i+1],
            "source_changed":g3_states[i]!=g3_states[i+1],
        })

    # 3 INTERVENTION: use all six transported stage slots as candidate experiments.
    init_before,init_after,init_delta,init_records=intervention_matrix([],g3_slots)
    final_before,final_after,final_delta,final_records=intervention_matrix(G3_ACTIONS,g3_slots)

    # 5 TERMINAL FALSIFICATION: compile causal response columns and submit.
    families=[
        ("initial_after",[],init_after),
        ("initial_delta",[],init_delta),
        ("final_after",G3_ACTIONS,final_after),
        ("final_delta",G3_ACTIONS,final_delta),
    ]
    tested=[]; selected=None; verification=[]
    seen=set()
    for fname,prefix,cols in families:
        for reverse in (False,True):
            for complement in (False,True):
                key=json.dumps({"cols":list(reversed(cols)) if reverse else cols,"complement":complement},sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                row=terminal_variant(prefix,cols,reverse,complement)
                tested.append({
                    "family":fname,
                    "reverse":reverse,
                    "complement":complement,
                    "write_count":row["write_count"],
                    "progressed":row["progressed"],
                    "outcome":row["outcome"],
                })
                if row["progressed"]:
                    vv=[terminal_variant(prefix,cols,reverse,complement),terminal_variant(prefix,cols,reverse,complement)]
                    if all(x["progressed"] for x in vv):
                        selected={
                            "family":fname,
                            "reverse":reverse,
                            "complement":complement,
                            "columns":list(reversed(cols)) if reverse else cols,
                            "write_count":row["write_count"],
                        }
                        verification=vv
                        break
            if selected: break
        if selected: break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "literature_lenses":{
            "static_correspondence":"stable object/test identity",
            "covariance":"changes that co-move with consequential state",
            "intervention":"do(candidate) causal response",
            "transport":"G2-to-G3 invariant structure with 4-to-6 cardinality",
            "terminal_falsification":"compile candidate meaning and let protected terminal oracle decide",
        },
        "transport":transport,
        "covariance":covariance,
        "intervention":{
            "initial_before":init_before,
            "initial_records":init_records,
            "initial_after_columns":init_after,
            "initial_delta_columns":init_delta,
            "final_before":final_before,
            "final_records":final_records,
            "final_after_columns":final_after,
            "final_delta_columns":final_delta,
            "initial_unique_after":len({tuple(x) for x in init_after}),
            "initial_unique_delta":len({tuple(x) for x in init_delta}),
            "final_unique_after":len({tuple(x) for x in final_after}),
            "final_unique_delta":len({tuple(x) for x in final_delta}),
        },
        "terminal_tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":48,
        "claim_boundary":"exact public tn36 G2/G3; stage slots inferred from top-track endpoint under canonical generators, not hard-coded as column meaning; covariance observed on exact source predicate; all six G3 slots intervened from initial and ABCDE states; causal after-state/delta vectors tested as target columns under forward/reverse and direct/complement conventions; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_FIVE_LENS_RAPID_G3="+status)

if __name__=="__main__":
    main()
