from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
import arc3_public_semantic_relation_g3 as sem
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-g2-learn-g3-singleton-transfer")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
G2_GEN=[("A",A),("B",B),("C",C)]
G3_KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]

def protected(f):
    if int(f.levels_completed)>2 or f.state==GameState.WIN:
        return "PROGRESS"
    if f.state==GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"

def singleton_family(f):
    out=[]
    for comp in ab.comps(f):
        if int(comp["color"])==0 and int(comp["size"])==1:
            cells=[tuple(x) for x in comp["cells"]]
            if len(cells)==1 and cells[0][1] < 31:
                out.append(cells[0])
    return sorted(out)

def source_sig(f):
    rows,src,targets=sem.semantic_surface(f)
    return list(src),targets

def enter_g2_generated():
    e=ab.env()
    ab.enter2(e)
    for _,rc in G2_GEN:
        z=ab.click(e,rc)
        if protected(z)!="CONTINUE":
            raise AssertionError("G2 generator terminated")
    return e

def enter_g3(prefix):
    e,_=g3.enter_level3()
    for _,rc in prefix:
        z=ab.click(e,rc)
        if protected(z)!="CONTINUE":
            break
    return e

def truth(mask,b,a):
    return (mask >> ((b<<1)|a)) & 1

def intervene_g2(obj):
    e=enter_g2_generated()
    before,_=source_sig(e.observation_space)
    z=ab.click(e,obj)
    after,_=source_sig(e.observation_space)
    return {"object":list(obj),"before":before,"after":after,"outcome":protected(z)}

def learn_g2_masks():
    base=enter_g2_generated()
    before,_=source_sig(base.observation_space)
    objs=singleton_family(base.observation_space)
    if len(objs)!=4:
        raise AssertionError(f"expected 4 G2 singleton objects, got {objs}")
    records=[intervene_g2(x) for x in objs]
    # Qualified G2 winning target is exact row correspondence, i.e. this source predicate in every target column.
    winner=before
    survivors=[]
    for mask in range(16):
        ok=True
        cols=[]
        for rec in records:
            col=[truth(mask,b,a) for b,a in zip(rec["before"],rec["after"])]
            cols.append(col)
            if col!=winner:
                ok=False
        if ok:
            survivors.append({
                "mask":mask,
                "truth_00_01_10_11":[truth(mask,b,a) for b,a in ((0,0),(0,1),(1,0),(1,1))],
                "columns":cols,
            })
    return before,objs,records,survivors

def intervene_g3(prefix,obj):
    e=enter_g3(prefix)
    before,_=source_sig(e.observation_space)
    z=ab.click(e,obj)
    after,_=source_sig(e.observation_space)
    return {"object":list(obj),"before":before,"after":after,"outcome":protected(z)}

def write_matrix(e,cols):
    if len(cols)!=6:
        raise AssertionError(len(cols))
    M=[[cols[j][i] for j in range(6)] for i in range(6)]
    rows,src,targets=sem.semantic_surface(e.observation_space)
    actions=[]
    for i in range(6):
        for j in range(6):
            want=M[i][j]
            cur=sem.bit(targets[i][j]["color"])
            if cur==want:
                continue
            rc=tuple(targets[i][j]["rc"])
            z=ab.click(e,rc)
            actions.append({"i":i,"j":j,"rc":list(rc),"want":want})
            if protected(z)!="CONTINUE":
                return actions,M
    return actions,M

def terminal_variant(prefix,cols):
    e=enter_g3(prefix)
    actions,M=write_matrix(e,cols)
    if protected(e.observation_space)=="CONTINUE":
        ab.click(e,A)
    return {
        "write_count":len(actions),
        "matrix":M,
        "progressed":protected(e.observation_space)=="PROGRESS",
        "outcome":protected(e.observation_space),
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
    }

def unique_permuted_columns(cols):
    seen=set()
    out=[]
    for p in itertools.permutations(range(6)):
        cc=[cols[i] for i in p]
        key=json.dumps(cc,separators=(",",":"))
        if key in seen:
            continue
        seen.add(key)
        out.append((list(p),cc))
    return out

def main():
    g2_before,g2_objs,g2_records,survivors=learn_g2_masks()
    if not survivors:
        raise AssertionError("no rowwise Boolean causal predicate reproduces qualified G2 target")

    tested=[]
    selected=None
    verification=[]
    g3_diagnostics=[]

    for k in range(6):
        prefix=G3_KNOWN[:k]
        base=enter_g3(prefix)
        objs=singleton_family(base.observation_space)
        if len(objs)!=6:
            raise AssertionError(f"expected 6 G3 singleton objects at k={k}, got {objs}")
        recs=[intervene_g3(prefix,x) for x in objs]
        g3_diagnostics.append({
            "prefix_len":k,
            "prefix":[n for n,_ in prefix],
            "objects":[list(x) for x in objs],
            "records":recs,
        })
        for sv in survivors:
            mask=sv["mask"]
            raw_cols=[
                [truth(mask,b,a) for b,a in zip(rec["before"],rec["after"])]
                for rec in recs
            ]
            for perm,cols in unique_permuted_columns(raw_cols):
                row=terminal_variant(prefix,cols)
                tested.append({
                    "prefix_len":k,
                    "mask":mask,
                    "truth_00_01_10_11":sv["truth_00_01_10_11"],
                    "permutation":perm,
                    "columns":cols,
                    "write_count":row["write_count"],
                    "progressed":row["progressed"],
                    "outcome":row["outcome"],
                })
                if row["progressed"]:
                    vv=[terminal_variant(prefix,cols),terminal_variant(prefix,cols)]
                    if all(x["progressed"] for x in vv):
                        selected={
                            "prefix_len":k,
                            "prefix":[n for n,_ in prefix],
                            "mask":mask,
                            "truth_00_01_10_11":sv["truth_00_01_10_11"],
                            "permutation":perm,
                            "columns":cols,
                            "write_count":row["write_count"],
                        }
                        verification=vv
                        break
            if selected: break
        if selected: break

    status="PROMOTED" if selected else "RESIDUAL"
    out={
        "status":status,
        "hypothesis":"learn a rowwise causal semantics from the qualified G2 singleton-control family, then transfer only G2-consistent Boolean predicates to the six G3 singleton controls and let the terminal oracle choose column assignment",
        "g2":{
            "before_source":g2_before,
            "objects":[list(x) for x in g2_objs],
            "interventions":g2_records,
            "surviving_masks":survivors,
        },
        "g3_diagnostics":g3_diagnostics,
        "tested_variants":len(tested),
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36; G2 training state is qualified A/B/C generator before target write; G2 winner is exact row correspondence; candidate semantics restricted to all 16 Boolean functions of per-row (before,after) singleton intervention; only G2-perfect functions transfer; G3 tested at prefixes 0..5 with all distinct column permutations induced by duplicate causal classes; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_G2_LEARN_G3_SINGLETON_TRANSFER="+status)

if __name__=="__main__":
    main()
