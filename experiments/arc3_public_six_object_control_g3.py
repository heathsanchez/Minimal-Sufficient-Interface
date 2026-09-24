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

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-six-object-control-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
G3_ACTIONS=[("A",A),("B",B),("C",C),("D",D),("E",E)]

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

def family_map(f):
    fam=defaultdict(list)
    for comp in ab.comps(f):
        r=comp_record(comp)
        if r["bbox"][1] >= 31:
            continue
        # Ignore giant frame/background components; retain discrete control/object candidates.
        if r["size"] > 100:
            continue
        fam[(r["color"],r["size"])].append(r)
    for k in fam:
        fam[k]=sorted(fam[k],key=lambda x:(x["center"][0],x["center"][1]))
    return fam

def source_bits(f):
    rows,src,targets=sem.semantic_surface(f)
    return rows,list(src),targets

def panel_bits(targets):
    return [[sem.bit(x["color"]) for x in row] for row in targets]

def transported_families():
    g2f=family_map(enter_g2().observation_space)
    g3f=family_map(enter_g3().observation_space)
    out=[]
    for sig in sorted(set(g2f)&set(g3f)):
        if len(g2f[sig])==4 and len(g3f[sig])==6:
            out.append({
                "signature":{"color":sig[0],"size":sig[1]},
                "g2_objects":g2f[sig],
                "g3_objects":g3f[sig],
            })
    return out

def family_at(prefix,sig):
    e=enter_g3(prefix)
    fam=family_map(e.observation_space)
    return fam.get((sig["color"],sig["size"]),[])

def intervention(prefix,obj):
    e=enter_g3(prefix)
    rows,before,targets=source_bits(e.observation_space)
    pbefore=panel_bits(targets)
    z=ab.click(e,tuple(obj["center"]))
    rows2,after,targets2=source_bits(e.observation_space)
    pafter=panel_bits(targets2)
    return {
        "center":obj["center"],
        "before_source":before,
        "after_source":after,
        "source_delta":[int(a!=b) for a,b in zip(before,after)],
        "target_changed":pbefore!=pafter,
        "outcome":protected(z),
    }

def cols_to_matrix(cols,reverse=False):
    cc=list(reversed(cols)) if reverse else list(cols)
    if len(cc)!=6 or any(len(x)!=6 for x in cc):
        raise AssertionError(cc)
    return [[cc[j][i] for j in range(6)] for i in range(6)]

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

def terminal(prefix,cols,reverse,complement):
    e=enter_g3(prefix)
    M=cols_to_matrix(cols,reverse)
    actions=write_matrix(e,M,complement)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "write_count":len(actions),
        "matrix":M,
    }

def main():
    candidates=transported_families()
    if not candidates:
        raise AssertionError("no 4->6 transported component family")

    reports=[]
    selected=None
    verification=[]

    for cand in candidates:
        sig=cand["signature"]
        g3_objs=cand["g3_objects"]

        # STATIC + TRANSPORT
        static={
            "signature":sig,
            "g2_count":len(cand["g2_objects"]),
            "g3_count":len(g3_objs),
            "g2_centers":[x["center"] for x in cand["g2_objects"]],
            "g3_centers":[x["center"] for x in g3_objs],
        }

        # COVARIANCE: object family positions across canonical stages.
        covariance=[]
        for k in range(6):
            objs=family_at(G3_ACTIONS[:k],sig)
            covariance.append({
                "prefix_len":k,
                "centers":[x["center"] for x in objs],
                "count":len(objs),
            })

        # INTERVENTION from initial and fully-generated states.
        init=[intervention([],obj) for obj in g3_objs]
        final_objs=family_at(G3_ACTIONS,sig)
        if len(final_objs)!=6:
            raise AssertionError(("family lost at final",sig,len(final_objs)))
        final=[intervention(G3_ACTIONS,obj) for obj in final_objs]

        families=[
            ("initial_after",[],[x["after_source"] for x in init]),
            ("initial_delta",[],[x["source_delta"] for x in init]),
            ("final_after",G3_ACTIONS,[x["after_source"] for x in final]),
            ("final_delta",G3_ACTIONS,[x["source_delta"] for x in final]),
        ]

        terminal_rows=[]
        seen=set()
        for fname,prefix,cols in families:
            for reverse in (False,True):
                for complement in (False,True):
                    key=json.dumps({
                        "cols":list(reversed(cols)) if reverse else cols,
                        "complement":complement,
                    },sort_keys=True)
                    if key in seen:
                        continue
                    seen.add(key)
                    row=terminal(prefix,cols,reverse,complement)
                    terminal_rows.append({
                        "family":fname,
                        "reverse":reverse,
                        "complement":complement,
                        "write_count":row["write_count"],
                        "progressed":row["progressed"],
                        "outcome":row["outcome"],
                    })
                    if row["progressed"] and selected is None:
                        vv=[terminal(prefix,cols,reverse,complement),terminal(prefix,cols,reverse,complement)]
                        if all(x["progressed"] for x in vv):
                            selected={
                                "signature":sig,
                                "family":fname,
                                "reverse":reverse,
                                "complement":complement,
                                "columns":list(reversed(cols)) if reverse else cols,
                                "objects":[x["center"] for x in (final_objs if fname.startswith("final") else g3_objs)],
                            }
                            verification=vv

        reports.append({
            "static_transport":static,
            "covariance":covariance,
            "intervention_initial":init,
            "intervention_final":final,
            "unique_initial_after":len({tuple(x["after_source"]) for x in init}),
            "unique_initial_delta":len({tuple(x["source_delta"]) for x in init}),
            "unique_final_after":len({tuple(x["after_source"]) for x in final}),
            "unique_final_delta":len({tuple(x["source_delta"]) for x in final}),
            "terminal":terminal_rows,
        })

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "parent_five_lens_head":"daafb74e270adfca3880377ae87306f7c70d5081",
        "parent_five_lens_run":35953088719,
        "hypothesis":"the six target columns correspond to a transported left-side object family whose connected-component signature occurs 4 times in G2 and 6 times in G3; individual object interventions should yield column-specific causal response vectors",
        "candidate_count":len(candidates),
        "reports":reports,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":48,
        "claim_boundary":"exact public tn36 G2/G3; candidate families are discrete left-side connected-component signatures (color,size<=100) with exact 4-count in G2 and 6-count in G3; apply five lenses: static object identity, canonical-stage covariance, one-click intervention from initial/final G3, G2->G3 transport, terminal compilation of causal source after/delta vectors under forward/reverse and direct/complement; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SIX_OBJECT_CONTROL_G3="+status)

if __name__=="__main__":
    main()
