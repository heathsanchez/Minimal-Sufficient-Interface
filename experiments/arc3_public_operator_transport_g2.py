from __future__ import annotations

import json
import logging
import os
from collections import Counter, deque
from pathlib import Path
from typing import Any

from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME_ID = "tn36-ef4dde99"
ENVROOT = Path(os.environ["ENVROOT"]).resolve()
OUTDIR = Path(os.environ.get("OUTDIR", "evidence/arc3-public-operator-transport-g2")).resolve()
OUTDIR.mkdir(parents=True, exist_ok=True)

G1 = [
    (55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)
]
TARGET_PROBES = [(58,46),(58,11),(58,20),(58,22),(55,20)]  # row,col from source V3

def grid(frame: Any) -> list[list[int]]:
    raw=frame.frame
    if isinstance(raw,(list,tuple)):
        raw=raw[-1]
    if hasattr(raw,"tolist"): raw=raw.tolist()
    return [[int(x) for x in row] for row in raw]

def comps(g):
    if not g: return []
    h,w=len(g),len(g[0])
    seen=set(); out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen: continue
            color=g[r][c]; q=deque([(r,c)]); seen.add((r,c)); cells=[]
            while q:
                rr,cc=q.popleft(); cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==color:
                        seen.add((nr,nc)); q.append((nr,nc))
            out.append((color,cells))
    return out

def summary(frame):
    g=grid(frame); h=len(g); w=len(g[0]) if h else 0
    cs=comps(g); total=h*w
    small=[cells for _,cells in cs if len(cells)<=max(16,total//4)]
    areas=Counter(len(c) for c in small)
    hist=Counter(x for row in g for x in row)
    rowt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    colt=sum(1 for r in range(max(0,h-1)) for c in range(w) if g[r][c]!=g[r+1][c])
    return {
        "component_count":len(small),
        "areas":dict(sorted(areas.items())),
        "hist":dict(sorted(hist.items())),
        "rowt":rowt,"colt":colt,
    }

def cdiff(a,b):
    keys=set(a)|set(b)
    return {str(k):int(b.get(k,0)-a.get(k,0)) for k in sorted(keys) if b.get(k,0)!=a.get(k,0)}

def sig(before,after):
    # Color labels may be representation-specific, so retain both labeled and
    # unlabeled histogram deltas. The structural area multiset is primary.
    hdelta=cdiff(before["hist"],after["hist"])
    return {
        "component_count_delta":after["component_count"]-before["component_count"],
        "area_multiset_delta":cdiff(before["areas"],after["areas"]),
        "hist_delta_labeled":hdelta,
        "hist_delta_unlabeled":sorted(hdelta.values()),
        "rowt_delta":after["rowt"]-before["rowt"],
        "colt_delta":after["colt"]-before["colt"],
    }

def distance(src,tgt):
    # Exact structural operator match dominates; geometry-transition deltas
    # break ties. Labeled colors are deliberately not required.
    d=0
    d += 20*abs(src["component_count_delta"]-tgt["component_count_delta"])
    keys=set(src["area_multiset_delta"])|set(tgt["area_multiset_delta"])
    d += 25*sum(abs(int(src["area_multiset_delta"].get(k,0))-int(tgt["area_multiset_delta"].get(k,0))) for k in keys)
    a=src["hist_delta_unlabeled"]; b=tgt["hist_delta_unlabeled"]
    n=max(len(a),len(b)); a=a+[0]*(n-len(a)); b=b+[0]*(n-len(b))
    d += 2*sum(abs(x-y) for x,y in zip(sorted(a),sorted(b)))
    d += abs(src["rowt_delta"]-tgt["rowt_delta"])
    d += abs(src["colt_delta"]-tgt["colt_delta"])
    return d

def make_env():
    log=logging.getLogger("operator-transport"); log.setLevel(logging.WARNING)
    arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=log)
    card=arcade.create_scorecard(); env=arcade.make(GAME_ID,scorecard_id=card)
    if env is None: raise RuntimeError("public game unavailable")
    return arcade,env

def click(env,rc):
    r,c=rc
    return env.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter_l2(env):
    for rc in G1:
        f=click(env,rc)
        if f is None: raise RuntimeError("G1 failed")
    if int(env.observation_space.levels_completed)!=1:
        raise RuntimeError("G1 drift")
    return env.observation_space

def reset_l2(env):
    f=env.reset()
    if f is None: raise RuntimeError("reset returned None")
    level=int(f.levels_completed)
    if level==1:
        return f
    if level==0:
        return enter_l2(env)
    raise RuntimeError(f"level reset drift: {level}")

def source_ops():
    _,env=make_env()
    ops=[]; prev=summary(env.observation_space)
    for i,rc in enumerate(G1):
        f=click(env,rc); cur=summary(f)
        ops.append({"i":i,"rc":list(rc),"sig":sig(prev,cur),"progressed":int(f.levels_completed)>0})
        prev=cur
    return ops

def enumerate_classes(env):
    base=summary(env.observation_space)
    classes={}
    action_to_class={}
    for r in range(64):
        for c in range(64):
            reset_l2(env)
            before=summary(env.observation_space)
            f=click(env,(r,c))
            if f is None or f.state==GameState.GAME_OVER: continue
            s=sig(before,summary(f))
            key=json.dumps(s,sort_keys=True,separators=(",",":"))
            rec=classes.setdefault(key,{"sig":s,"actions":[],"changed":False,"progressed":False})
            rec["actions"].append([r,c])
            rec["changed"] = rec["changed"] or (summary(f)!=before)
            rec["progressed"] = rec["progressed"] or int(f.levels_completed)>1 or f.state==GameState.WIN
            action_to_class[(r,c)]=key
    return classes,action_to_class

def run_greedy(source, classes, probes):
    _,env=make_env(); enter_l2(env)
    trace=[]; used_probes=set()
    # first use source target-side probe history as free anchors where their
    # operator class matches the next source operator unusually well.
    for step,src in enumerate(source):
        if int(env.observation_space.levels_completed)>1: break
        before=summary(env.observation_space)
        candidates=[]
        # enumerate effect classes from current state exactly; one representative per class.
        seen={}
        preferred=list(probes)+[tuple(rec["actions"][0]) for rec in classes.values() if rec["actions"]]
        # add all class representatives from root, then full coords only if unseen consequence needed
        coords=[]
        for rc in preferred:
            if rc not in coords: coords.append(rc)
        for r in range(64):
            for c in range(64):
                if (r,c) not in coords: coords.append((r,c))
        for rc in coords:
            reset_l2(env)
            # replay already chosen target program
            for old in [tuple(x["rc"]) for x in trace]:
                ff=click(env,old)
                if int(ff.levels_completed)>1: break
            if int(env.observation_space.levels_completed)>1:
                break
            b=summary(env.observation_space)
            f=click(env,rc)
            if f is None or f.state==GameState.GAME_OVER: continue
            t=sig(b,summary(f))
            key=json.dumps(t,sort_keys=True,separators=(",",":"))
            if key in seen: continue
            seen[key]=rc
            candidates.append((distance(src["sig"],t),rc,t,int(f.levels_completed)>1 or f.state==GameState.WIN))
        if not candidates: break
        candidates.sort(key=lambda x:(x[0],x[1][0],x[1][1]))
        best=candidates[0]
        rc=best[1]
        # execute chosen operator on live accumulated state
        reset_l2(env)
        for old in [tuple(x["rc"]) for x in trace]:
            f=click(env,old)
        b=summary(env.observation_space); f=click(env,rc); t=sig(b,summary(f))
        trace.append({"source_step":step,"source_rc":src["rc"],"rc":list(rc),"distance":best[0],"sig":t,"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,"distinct_classes_tested":len(seen)})
        if int(f.levels_completed)>1 or f.state==GameState.WIN: break
    return trace

def verify(program):
    outs=[]
    for _ in range(2):
        _,env=make_env(); enter_l2(env)
        for rc in program:
            f=click(env,tuple(rc))
            if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER): break
        outs.append({"level":int(env.observation_space.levels_completed),"state":str(env.observation_space.state),"progressed":int(env.observation_space.levels_completed)>1 or env.observation_space.state==GameState.WIN})
    return outs

def main():
    src=source_ops()
    _,env=make_env(); enter_l2(env)
    classes,_=enumerate_classes(env)
    trace=run_greedy(src,classes,TARGET_PROBES)
    program=[x["rc"] for x in trace]
    v=verify(program) if program else []
    result={
        "source_run":35811403514,
        "g1_run":35854403385,
        "source_operators":src,
        "root_action_quotient":{"raw":4096,"classes":len(classes)},
        "target_probes":[list(x) for x in TARGET_PROBES],
        "transport_trace":trace,
        "program":program,
        "verification":v,
        "status":"PROMOTED" if v and all(x["progressed"] for x in v) else "RESIDUAL",
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"black-box operator-signature transport on exact public tn36 generation-2 residual",
    }
    (OUTDIR/"result.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    print("ARC3_PUBLIC_OPERATOR_TRANSPORT_G2="+result["status"])

if __name__=="__main__":
    main()
