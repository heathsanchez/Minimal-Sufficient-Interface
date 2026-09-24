from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-directed-edge-incidence-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]
GENS=[
    ("none",[]),
    ("B",[("B",B)]),
    ("BD",[("B",B),("D",D)]),
    ("ABCDE",KNOWN),
]
ROLES=["both","source","target"]

def replay(prefix):
    e,_=g3.enter_level3()
    for _,rc in prefix:
        z=ab.click(e,rc)
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e

def source_state(k):
    e=replay(KNOWN[:k])
    rows,src,_=sem.semantic_surface(e.observation_space)
    return rows,list(src)

def active_vertices():
    states=[]
    for k in (0,2,4):
        rows,s=source_state(k)
        active=tuple(i for i,b in enumerate(s) if b)
        if len(active)!=2:
            raise AssertionError((k,s))
        states.append(active)
    vertices=sorted(set().union(*[set(x) for x in states]))
    if len(vertices)!=3:
        raise AssertionError((states,vertices))
    expected={tuple(sorted(x)) for x in itertools.combinations(vertices,2)}
    observed={tuple(sorted(x)) for x in states}
    if observed!=expected:
        raise AssertionError((states,vertices))
    return rows,states,vertices

def directed_edges(order):
    # Lexicographic ordered pairs under the chosen vertex ordering.
    out=[]
    for u in order:
        for v in order:
            if u!=v:
                out.append((u,v))
    if len(out)!=6:
        raise AssertionError(out)
    return out

def matrix_for(order,role):
    rows,states,vertices=active_vertices()
    edges=directed_edges(order)
    M=[]
    for i in range(6):
        row=[]
        for u,v in edges:
            if role=="both":
                bit=1 if i in (u,v) else 0
            elif role=="source":
                bit=1 if i==u else 0
            elif role=="target":
                bit=1 if i==v else 0
            else:
                raise ValueError(role)
            row.append(bit)
        M.append(row)
    return rows,states,vertices,edges,M

def write_matrix(e,M,complement):
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
            actions.append({"i":i,"j":j,"rc":list(rc),"before":cur,"want":want})
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                return actions
    return actions

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def run_variant(gen_name,prefix,order,role,complement):
    e=replay(prefix)
    rows,states,vertices,edges,M=matrix_for(order,role)
    actions=write_matrix(e,M,complement)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "generation":gen_name,
        "order":list(order),
        "role":role,
        "complement":complement,
        "source_states":[list(x) for x in states],
        "vertices":vertices,
        "directed_edges":[list(x) for x in edges],
        "matrix":M,
        "write_count":len(actions),
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def main():
    rows,states,vertices=active_vertices()
    tested=[]
    selected=None
    verification=[]

    for gen_name,prefix in GENS:
        for order in itertools.permutations(vertices):
            for role in ROLES:
                for complement in (False,True):
                    row=run_variant(gen_name,prefix,order,role,complement)
                    tested.append({
                        "generation":gen_name,
                        "order":row["order"],
                        "role":role,
                        "complement":complement,
                        "write_count":row["write_count"],
                        "progressed":row["progressed"],
                        "outcome":row["outcome"],
                        "edges":row["directed_edges"],
                    })
                    if row["progressed"]:
                        vv=[run_variant(gen_name,prefix,order,role,complement),run_variant(gen_name,prefix,order,role,complement)]
                        if all(x["progressed"] for x in vv):
                            selected={
                                "generation":gen_name,
                                "order":row["order"],
                                "role":role,
                                "complement":complement,
                                "edges":row["directed_edges"],
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
        "parent_target_orientation_head":"ff477b625d918270d6e67e53784ad89fb4e4eda0",
        "parent_target_orientation_run":35951458392,
        "hypothesis":"the three observed source states are exactly the three undirected edges on active row identities {0,1,5}; the six target columns may therefore denote the six directed edges, with row colors encoding endpoint/source/target incidence",
        "source_states":[list(x) for x in states],
        "active_vertices":vertices,
        "generation_histories":[name for name,_ in GENS],
        "roles":ROLES,
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":48,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; derive active vertices and three edge states only from observed source predicates at prefixes 0,2,4; target columns are six ordered pairs under all 3! vertex orderings; test endpoint/source/target incidence, direct/complement, after none/B/BD/ABCDE generation histories; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_DIRECTED_EDGE_INCIDENCE_G3="+status)

if __name__=="__main__":
    main()
