from __future__ import annotations

import itertools
import json
import os
from collections import defaultdict
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g2 as g2
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-macro-port-incidence-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
G3_ACTIONS=[("A",A),("B",B),("C",C),("D",D),("E",E)]
GENS=[
    ("none",[]),
    ("B",[("B",B)]),
    ("BD",[("B",B),("D",D)]),
    ("ABCDE",G3_ACTIONS),
]

PORT_SIG=(0,1)

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def enter_g2():
    e=ab.env()
    ab.enter2(e)
    return e

def enter_g3(prefix=None):
    e,_=g3.enter_level3()
    for _,rc in (prefix or []):
        ab.click(e,rc)
    return e

def comp_record(comp):
    cells=[tuple(x) for x in comp["cells"]]
    rs=[r for r,c in cells]; cs=[c for r,c in cells]
    return {
        "color":int(comp["color"]),
        "size":int(comp["size"]),
        "bbox":[min(rs),min(cs),max(rs),max(cs)],
        "center":[sum(rs)//len(rs),sum(cs)//len(cs)],
        "cells":[list(x) for x in sorted(cells)],
    }

def discrete_components(f):
    out=[]
    for comp in ab.comps(f):
        r=comp_record(comp)
        if r["bbox"][1] >= 31:
            continue
        if r["size"] > 100:
            continue
        out.append(r)
    out.sort(key=lambda x:(x["bbox"][0],x["bbox"][1],x["color"],x["size"]))
    return out

def group_by_sig(f):
    fam=defaultdict(list)
    for r in discrete_components(f):
        fam[(r["color"],r["size"])].append(r)
    for k in fam:
        fam[k]=sorted(fam[k],key=lambda x:(x["center"][1],x["center"][0]))
    return fam

def inside(point,bbox):
    r,c=point
    r0,c0,r1,c1=bbox
    return r0<=r<=r1 and c0<=c<=c1

def discover_macro_family():
    g2f=group_by_sig(enter_g2().observation_space)
    g3f=group_by_sig(enter_g3().observation_space)
    g2ports=g2f.get(PORT_SIG,[])
    g3ports=g3f.get(PORT_SIG,[])
    if len(g2ports)!=4 or len(g3ports)!=6:
        raise AssertionError(("port transport",len(g2ports),len(g3ports)))

    candidates=[]
    for sig in sorted(set(g2f)&set(g3f)):
        if len(g2f[sig])!=2 or len(g3f[sig])!=3:
            continue
        g2mac=g2f[sig]; g3mac=g3f[sig]
        g2groups=[]
        g3groups=[]
        ok=True
        for mac in g2mac:
            ps=[p for p in g2ports if inside(tuple(p["center"]),mac["bbox"])]
            if len(ps)!=2:
                ok=False; break
            g2groups.append(ps)
        if not ok: continue
        for mac in g3mac:
            ps=[p for p in g3ports if inside(tuple(p["center"]),mac["bbox"])]
            if len(ps)!=2:
                ok=False; break
            g3groups.append(ps)
        if not ok: continue
        if len({tuple(p["center"]) for grp in g2groups for p in grp})!=4:
            continue
        if len({tuple(p["center"]) for grp in g3groups for p in grp})!=6:
            continue
        candidates.append({
            "signature":{"color":sig[0],"size":sig[1]},
            "g2_macros":g2mac,
            "g3_macros":g3mac,
            "g2_groups":g2groups,
            "g3_groups":g3groups,
        })
    return candidates

def source_bits(f):
    rows,src,targets=sem.semantic_surface(f)
    return rows,list(src),targets

def macro_state(prefix,ports):
    # Click the first port of the macro; six-object test proved paired ports share response class.
    e=enter_g3(prefix)
    ab.click(e,tuple(ports[0]["center"]))
    rows,src,_=source_bits(e.observation_space)
    active=[i for i,b in enumerate(src) if b]
    if len(active)!=2:
        raise AssertionError(("macro state not pair",src,ports))
    return active,src

def write_matrix(e,M,complement=False):
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
            actions.append({"i":i,"j":j,"rc":list(rc),"want":want})
            if protected(z)!="CONTINUE":
                return actions
    return actions

def matrix_from_assignment(groups,macro_pairs,swap_bits):
    # Earned column order: left-to-right macro, then the two contained ports in
    # deterministic geometric order. Each macro's two ports are assigned to the
    # two active source-row identities; swap_bits chooses the only unknown.
    cols=[]
    mapping=[]
    for m,(ports,pair) in enumerate(zip(groups,macro_pairs)):
        ps=sorted(ports,key=lambda x:(x["center"][0],x["center"][1]))
        ids=sorted(pair)
        if swap_bits[m]:
            ids=list(reversed(ids))
        for p,row_id in zip(ps,ids):
            col=[0]*6
            col[row_id]=1
            cols.append(col)
            mapping.append({
                "macro_index":m,
                "port_center":p["center"],
                "row_id":row_id,
            })
    if len(cols)!=6:
        raise AssertionError(cols)
    M=[[cols[j][i] for j in range(6)] for i in range(6)]
    return cols,M,mapping

def run_variant(cand,gen_name,prefix,swap_bits,complement):
    groups=cand["g3_groups"]
    macro_pairs=[]
    macro_states=[]
    # Learn each macro's pair meaning from intervention at the current generation state.
    for ports in groups:
        active,src=macro_state(prefix,ports)
        macro_pairs.append(active)
        macro_states.append(src)
    cols,M,mapping=matrix_from_assignment(groups,macro_pairs,swap_bits)
    e=enter_g3(prefix)
    actions=write_matrix(e,M,complement)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "generation":gen_name,
        "swap_bits":list(swap_bits),
        "complement":complement,
        "macro_pairs":macro_pairs,
        "macro_states":macro_states,
        "mapping":mapping,
        "columns":cols,
        "matrix":M,
        "write_count":len(actions),
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def main():
    candidates=discover_macro_family()
    if not candidates:
        raise AssertionError("no 2->3 macro family containing transported ports")
    tested=[]
    selected=None
    verification=[]

    for cand in candidates:
        # Sort macros left-to-right and preserve port containment.
        order=sorted(range(len(cand["g3_macros"])),key=lambda i:cand["g3_macros"][i]["center"][1])
        cand["g3_macros"]=[cand["g3_macros"][i] for i in order]
        cand["g3_groups"]=[cand["g3_groups"][i] for i in order]

        for gen_name,prefix in GENS:
            for swap_bits in itertools.product([False,True],repeat=3):
                for complement in (False,True):
                    row=run_variant(cand,gen_name,prefix,swap_bits,complement)
                    tested.append({
                        "signature":cand["signature"],
                        "generation":gen_name,
                        "swap_bits":list(swap_bits),
                        "complement":complement,
                        "macro_pairs":row["macro_pairs"],
                        "mapping":row["mapping"],
                        "write_count":row["write_count"],
                        "progressed":row["progressed"],
                        "outcome":row["outcome"],
                    })
                    if row["progressed"] and selected is None:
                        vv=[run_variant(cand,gen_name,prefix,swap_bits,complement),
                            run_variant(cand,gen_name,prefix,swap_bits,complement)]
                        if all(x["progressed"] for x in vv):
                            selected={
                                "signature":cand["signature"],
                                "generation":gen_name,
                                "swap_bits":list(swap_bits),
                                "complement":complement,
                                "macro_pairs":row["macro_pairs"],
                                "mapping":row["mapping"],
                                "columns":row["columns"],
                                "write_count":row["write_count"],
                            }
                            verification=vv
                            break
                if selected: break
            if selected: break
        if selected: break

    status="PROMOTED" if selected else "RESIDUAL"
    summary=[]
    for cand in candidates:
        summary.append({
            "signature":cand["signature"],
            "g2_macro_count":len(cand["g2_macros"]),
            "g3_macro_count":len(cand["g3_macros"]),
            "g2_macro_bboxes":[x["bbox"] for x in cand["g2_macros"]],
            "g3_macro_bboxes":[x["bbox"] for x in cand["g3_macros"]],
            "g2_port_groups":[[p["center"] for p in grp] for grp in cand["g2_groups"]],
            "g3_port_groups":[[p["center"] for p in grp] for grp in cand["g3_groups"]],
        })

    out={
        "status":status,
        "parent_six_object_head":"557e4c6b4b0bf63cfbac957261f92bfc82c13986",
        "parent_six_object_run":35959512913,
        "hypothesis":"the transported 4->6 singleton family are two ports per transported macro-control; G2 has 2 macros x2 ports and G3 has 3 macros x2 ports. Each macro intervention reveals a two-row source pair; target columns are one-hot endpoint incidence in earned left-to-right macro/port order.",
        "macro_candidates":summary,
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":48,
        "claim_boundary":"exact public tn36 G2/G3; discover macro signatures with exact 2->3 transport and exact containment of the already-qualified 4->6 singleton port family, two ports per macro; infer each G3 macro's two active row identities by port intervention at the tested generation state; target columns use earned left-to-right macro order and geometric within-macro port order, with only 2^3 endpoint swaps and direct/complement convention unresolved; test none/B/BD/ABCDE generation; terminal A; progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_MACRO_PORT_INCIDENCE_G3="+status)

if __name__=="__main__":
    main()
