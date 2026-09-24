from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-singleton-family-five-lens-g3")).resolve()
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
        z=ab.click(e,rc)
        if protected(z)!="CONTINUE":
            break
    return e

def singleton_family(f):
    out=[]
    for comp in ab.comps(f):
        if int(comp["color"])!=0 or int(comp["size"])!=1:
            continue
        cells=[tuple(x) for x in comp["cells"]]
        if len(cells)!=1:
            continue
        r,c=cells[0]
        # Keep the left/control half only; right side is writable target.
        if c < 31:
            out.append((r,c))
    return sorted(out)

def source_sig(f):
    rows,src,targets=sem.semantic_surface(f)
    panel=[[sem.bit(x["color"]) for x in row] for row in targets]
    return list(src),panel

def frame_hash(f):
    import hashlib
    x=f.frame
    if isinstance(x,(list,tuple)):
        x=x[-1]
    if hasattr(x,"tolist"):
        x=x.tolist()
    return hashlib.sha256(json.dumps(x,separators=(",",":")).encode()).hexdigest()

def family_trace_g3():
    rows=[]
    for k in range(6):
        e=enter_g3(G3_ACTIONS[:k])
        rows.append({
            "prefix_len":k,
            "prefix":[n for n,_ in G3_ACTIONS[:k]],
            "objects":[list(x) for x in singleton_family(e.observation_space)],
        })
    return rows

def family_trace_g2():
    e=enter_g2()
    rows=[{"stage":"initial","objects":[list(x) for x in singleton_family(e.observation_space)]}]
    # G2 qualified generator is A,B,C.
    for name,rc in [("A",A),("B",B),("C",C)]:
        ab.click(e,rc)
        rows.append({"stage":name,"objects":[list(x) for x in singleton_family(e.observation_space)]})
    return rows

def intervention(prefix,obj):
    e=enter_g3(prefix)
    before_src,before_panel=source_sig(e.observation_space)
    before_hash=frame_hash(e.observation_space)
    z=ab.click(e,obj)
    after_src,after_panel=source_sig(e.observation_space)
    after_hash=frame_hash(e.observation_space)
    return {
        "object":list(obj),
        "before_source":before_src,
        "after_source":after_src,
        "delta":[int(a!=b) for a,b in zip(before_src,after_src)],
        "source_changed":before_src!=after_src,
        "panel_changed":before_panel!=after_panel,
        "frame_changed":before_hash!=after_hash,
        "outcome":protected(z),
    }

def intervention_bank(prefix,objects):
    return [intervention(prefix,obj) for obj in objects]

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
        "write_count":len(actions),
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def main():
    g2_trace=family_trace_g2()
    g3_trace=family_trace_g3()
    g2_counts=[len(x["objects"]) for x in g2_trace]
    g3_counts=[len(x["objects"]) for x in g3_trace]

    g3_initial=[tuple(x) for x in g3_trace[0]["objects"]]
    g3_final=[tuple(x) for x in g3_trace[-1]["objects"]]

    transport={
        "g2_trace":g2_trace,
        "g3_trace":g3_trace,
        "g2_counts":g2_counts,
        "g3_counts":g3_counts,
        "g2_all_four":all(x==4 for x in g2_counts),
        "g3_all_six":all(x==6 for x in g3_counts),
        "g3_objects_stable":all(x["objects"]==g3_trace[0]["objects"] for x in g3_trace),
    }

    # Covariance: do family identities themselves move under A-E?
    covariance=[]
    for i,name in enumerate(["A","B","C","D","E"]):
        before=g3_trace[i]["objects"]; after=g3_trace[i+1]["objects"]
        covariance.append({
            "action":name,
            "objects_changed":before!=after,
            "before":before,
            "after":after,
        })

    intervention_initial=intervention_bank([],g3_initial) if len(g3_initial)==6 else []
    intervention_final=intervention_bank(G3_ACTIONS,g3_final) if len(g3_final)==6 else []

    families=[]
    if len(intervention_initial)==6:
        families.extend([
            ("initial_after",[],[x["after_source"] for x in intervention_initial]),
            ("initial_delta",[],[x["delta"] for x in intervention_initial]),
        ])
    if len(intervention_final)==6:
        families.extend([
            ("final_after",G3_ACTIONS,[x["after_source"] for x in intervention_final]),
            ("final_delta",G3_ACTIONS,[x["delta"] for x in intervention_final]),
        ])

    tested=[]; selected=None; verification=[]; seen=set()
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

    if not transport["g3_all_six"]:
        status="NO_SIX_OBJECT_FAMILY"
    elif selected:
        status="PROMOTED"
    else:
        status="RESIDUAL"

    out={
        "status":status,
        "candidate_family":"left-side connected components with color=0,size=1",
        "transport":transport,
        "covariance":covariance,
        "intervention":{
            "initial":intervention_initial,
            "final":intervention_final,
            "initial_unique_after":len({tuple(x["after_source"]) for x in intervention_initial}) if intervention_initial else 0,
            "initial_unique_delta":len({tuple(x["delta"]) for x in intervention_initial}) if intervention_initial else 0,
            "final_unique_after":len({tuple(x["after_source"]) for x in intervention_final}) if intervention_final else 0,
            "final_unique_delta":len({tuple(x["delta"]) for x in intervention_final}) if intervention_final else 0,
        },
        "terminal_tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":48,
        "claim_boundary":"exact public tn36 G2/G3; candidate family is exactly the left-half color-0 singleton connected components surfaced by the component census; test G2/G3 count transport and stage stability, independent G3 interventions from initial/final state, compile after-source/delta causal response columns, forward/reverse and direct/complement, terminal A, replay any progress twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SINGLETON_FAMILY_FIVE_LENS_G3="+status)

if __name__=="__main__":
    main()
