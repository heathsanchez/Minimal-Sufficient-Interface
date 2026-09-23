from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-history-automaton-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
HIST_PROBES=[(58,46),(58,11),(58,20),(58,22),(55,20),(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]
MAX_HISTORIES=24
MAX_PER_FEATURE=6
MAX_PER_BOARD=4
FULL_SUFFIX_SCAN_LIMIT=8

def env():
    l=logging.getLogger("history-automaton");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game unavailable")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)): x=x[-1]
    if hasattr(x,"tolist"): x=x.tolist()
    return [[int(v) for v in row] for row in x]

def board_hash(f):
    return hashlib.sha256(json.dumps(grid(f),separators=(",",":")).encode()).hexdigest()

def labeled_components(f):
    g=grid(f);h,w=len(g),len(g[0]);lab={};cs=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in lab: continue
            z=g[r][c];idx=len(cs);q=deque([(r,c)]);lab[(r,c)]=idx;cells=[]
            while q:
                rr,cc=q.popleft();cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in lab and g[nr][nc]==z:
                        lab[(nr,nc)]=idx;q.append((nr,nc))
            rs=[r for r,_ in cells]; cols=[c for _,c in cells]
            cs.append({
                "color":z,"size":len(cells),"h":max(rs)-min(rs)+1,"w":max(cols)-min(cols)+1,
                "bbox":(min(rs),min(cols),max(rs),max(cols)),"cells":cells
            })
    return g,lab,cs

def feat(f):
    g,_,cs=labeled_components(f);h,w=len(g),len(g[0])
    sizes=Counter();shape=Counter();color_size=Counter();colors=Counter(v for row in g for v in row)
    for x in cs:
        sizes[x["size"]]+=1
        shape[(x["color"],x["h"],x["w"],x["size"])]+=1
        color_size[(x["color"],x["size"])]+=1
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"sizes":sizes,"shape":shape,"color_size":color_size,"colors":colors,"rt":rt,"ct":ct}

def plain(x):
    if isinstance(x,Counter): return {str(k):int(v) for k,v in sorted(x.items(),key=lambda kv:str(kv[0]))}
    if isinstance(x,dict): return {str(k):plain(v) for k,v in sorted(x.items(),key=lambda kv:str(kv[0]))}
    return x

def feat_hash(f):
    return hashlib.sha256(json.dumps(plain(feat(f)),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def delta(a,b):
    out={}
    for name in ("sizes","shape","color_size","colors"):
        keys=set(a[name])|set(b[name])
        d={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
        if d: out[name]=d
    for name in ("rt","ct"):
        v=b[name]-a[name]
        if v: out[name]=v
    return out

def relation(f,rc):
    g,lab,cs=labeled_components(f);r,c=rc;i=lab[(r,c)];x=cs[i]
    r0,c0,r1,c1=x["bbox"]
    neigh=[]
    for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
        nr,nc=r+dr,c+dc
        if 0<=nr<len(g) and 0<=nc<len(g[0]):
            j=lab[(nr,nc)]
            if j!=i:
                y=cs[j]
                neigh.append((dr,dc,y["color"],y["h"],y["w"],y["size"]))
    return {
        "color":x["color"],"h":x["h"],"w":x["w"],"size":x["size"],
        "rel":(r-r0,c-c0,r1-r,c1-c),
        "neighbors":sorted(neigh),
    }

def relation_key(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"))

def source_effects():
    e=env();prev=feat(e.observation_space);rows=[]
    for i,rc in enumerate(G1[:-1]):
        z=click(e,rc);cur=feat(z)
        rows.append({"i":i,"rc":list(rc),"effect":delta(prev,cur)})
        prev=cur
    return rows

def reset_level2(e):
    f=e.reset()
    if f is None: raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            z=click(e,rc)
            if z is None: raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:
        raise RuntimeError(f"g1 drift {e.observation_space.levels_completed}")
    return e.observation_space

def replay(e,history):
    reset_level2(e)
    for rc in history:
        z=click(e,tuple(rc))
        if z is None: raise RuntimeError("history replay None")
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return e.observation_space

def exact_matches(e,history,target):
    # Return a diverse set of exact-effect realizations. Preserve multiple
    # witnesses when they converge observationally: that is the history-state hypothesis.
    by=(defaultdict(list))
    for r in range(64):
        for c in range(64):
            f=replay(e,history)
            if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
                continue
            before=feat(f)
            rel=relation(f,(r,c))
            z=click(e,(r,c))
            if z is None or z.state==GameState.GAME_OVER: continue
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                # Preterminal source effects should not progress.
                continue
            ed=delta(before,feat(z))
            if ed!=target: continue
            key=(board_hash(z),relation_key(rel))
            by[key].append((r,c))
    out=[]
    for (bh,rk),coords in sorted(by.items(),key=lambda kv:(kv[0][0],kv[0][1])):
        # Preserve two coordinate witnesses per exact observational/relation class.
        picks=[coords[0]]
        if len(coords)>1 and coords[-1]!=coords[0]: picks.append(coords[-1])
        for rc in picks:
            out.append({"rc":rc,"board_hash":bh,"relation":json.loads(rk),"multiplicity":len(coords)})
    return out

def prune(histories):
    # Histories are never collapsed outright. We retain multiple lineages in each
    # observed feature/board fiber, exactly where future separation may live.
    feat_groups=defaultdict(list)
    for h in histories: feat_groups[h["feature_hash"]].append(h)
    stage=[]
    for fh,rows in sorted(feat_groups.items()):
        board_groups=defaultdict(list)
        for x in rows: board_groups[x["board_hash"]].append(x)
        kept=[]
        for bh,br in sorted(board_groups.items()):
            # diversify by final relation/coordinate
            seen=set()
            for x in br:
                k=(json.dumps(x.get("last_relation"),sort_keys=True),tuple(x["history"][-1]))
                if k in seen: continue
                seen.add(k);kept.append(x)
                if sum(1 for y in kept if y["board_hash"]==bh)>=MAX_PER_BOARD: break
        stage.extend(kept[:MAX_PER_FEATURE])
    # Round-robin across feature fibers to avoid one large symmetric family monopolizing beam.
    if len(stage)<=MAX_HISTORIES: return stage
    buckets=defaultdict(deque)
    for x in stage: buckets[x["feature_hash"]].append(x)
    out=[]
    while len(out)<MAX_HISTORIES and any(buckets.values()):
        for k in sorted(buckets):
            if buckets[k] and len(out)<MAX_HISTORIES: out.append(buckets[k].popleft())
    return out

def apply_suffix(history,kind,payload):
    e=env();f=replay(e,history)
    if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
        return {"level":int(f.levels_completed),"state":str(f.state),"board":board_hash(f)}
    if kind=="mouse":
        z=click(e,tuple(payload))
    else:
        z=e.step(getattr(GameAction,payload))
    if z is None: return {"none":True}
    return {"level":int(z.levels_completed),"state":str(z.state),"board":board_hash(z)}

def outcome_key(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"))

def quick_suffixes(history):
    out=[]
    seen=set()
    # Cycle closure first: G1 begins and ends at the same witness.
    coords=[tuple(history[0])] if history else []
    coords += [tuple(x) for x in history]
    coords += HIST_PROBES
    for rc in coords:
        if rc not in seen:
            seen.add(rc);out.append(("mouse",rc))
    for name in ("ACTION1","ACTION2","ACTION3","ACTION4","ACTION5","ACTION7"):
        out.append(("primitive",name))
    return out

def full_mouse_separator(a,b):
    for r in range(64):
        for c in range(64):
            oa=apply_suffix(a,"mouse",(r,c));ob=apply_suffix(b,"mouse",(r,c))
            if outcome_key(oa)!=outcome_key(ob):
                return {"suffix":["mouse",r,c],"left":oa,"right":ob}
    return None

def terminal_scan(history):
    # Fast cycle/known-witness bank first.
    for kind,payload in quick_suffixes(history):
        o=apply_suffix(history,kind,payload)
        if int(o.get("level",0))>1 or o.get("state")=="GameState.WIN":
            return {"kind":kind,"payload":list(payload) if isinstance(payload,tuple) else payload,"outcome":o}
    # Then exact mouse membership oracle.
    for r in range(64):
        for c in range(64):
            o=apply_suffix(history,"mouse",(r,c))
            if int(o.get("level",0))>1 or o.get("state")=="GameState.WIN":
                return {"kind":"mouse","payload":[r,c],"outcome":o}
    return None

def verify(program):
    outs=[]
    for _ in range(2):
        e=env();reset_level2(e)
        for rc in program:
            z=click(e,tuple(rc))
            if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER): break
        outs.append({"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
                     "progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN})
    return outs

def main():
    src=source_effects()
    e=env()
    histories=[{"history":[]}]
    stages=[]
    for row in src:
        nxt=[]
        for h in histories:
            matches=exact_matches(e,h["history"],row["effect"])
            for m in matches:
                hh=h["history"]+[list(m["rc"])]
                f=replay(e,hh)
                nxt.append({
                    "history":hh,
                    "board_hash":board_hash(f),
                    "feature_hash":feat_hash(f),
                    "last_relation":m["relation"],
                    "match_multiplicity":m["multiplicity"],
                })
        before=len(nxt)
        histories=prune(nxt)
        feat_fibers=Counter(x["feature_hash"] for x in histories)
        board_fibers=Counter(x["board_hash"] for x in histories)
        stages.append({
            "source_step":row["i"],"generated":before,"retained":len(histories),
            "feature_fibers":len(feat_fibers),"feature_collision_histories":sum(v for v in feat_fibers.values() if v>1),
            "board_fibers":len(board_fibers),"exact_board_collision_histories":sum(v for v in board_fibers.values() if v>1),
        })
        if not histories: break

    selected=None
    terminal_evidence=[]
    # Test every retained history, but stop on first independently verifiable win.
    for h in histories:
        term=terminal_scan(h["history"])
        terminal_evidence.append({"history":h["history"],"board_hash":h["board_hash"],"feature_hash":h["feature_hash"],"terminal":term})
        if term and term["kind"]=="mouse":
            program=h["history"]+[term["payload"]]
            ver=verify(program)
            if all(x["progressed"] for x in ver):
                selected={"history":h["history"],"terminal":term,"program":program,"verification":ver}
                break

    # Explicit continuation separators: same exact visible board first; then same feature state.
    separators=[]
    scans=0
    for field in ("board_hash","feature_hash"):
        groups=defaultdict(list)
        for h in histories: groups[h[field]].append(h)
        for key,rows in groups.items():
            if len(rows)<2: continue
            base=rows[0]
            for other in rows[1:]:
                # Cheap suffix bank.
                sep=None
                bank=quick_suffixes(base["history"])
                for kind,payload in bank:
                    a=apply_suffix(base["history"],kind,payload)
                    b=apply_suffix(other["history"],kind,payload)
                    if outcome_key(a)!=outcome_key(b):
                        sep={"fiber":field,"fiber_key":key,"suffix":[kind,list(payload) if isinstance(payload,tuple) else payload],
                             "left_history":base["history"],"right_history":other["history"],"left":a,"right":b}
                        break
                if sep is None and scans<FULL_SUFFIX_SCAN_LIMIT:
                    scans+=1
                    raw=full_mouse_separator(base["history"],other["history"])
                    if raw:
                        sep={"fiber":field,"fiber_key":key,"left_history":base["history"],"right_history":other["history"],**raw}
                if sep: separators.append(sep)

    out={
        "source_run":35811403514,
        "strict_transport_run":35868730738,
        "primitive_negative_run":35892193614,
        "source_preterminal_effects":len(src),
        "stages":stages,
        "retained_histories":len(histories),
        "terminal_evidence":terminal_evidence,
        "selected":selected,
        "separators":separators,
        "full_separator_scans":scans,
        "model_calls":0,
        "source_inspection":False,
        "status":"PROMOTED" if selected else ("HISTORY_SEPARATED" if separators else "RESIDUAL"),
        "claim_boundary":"finite black-box consequential-history refinement over exact transported G1 preterminal effects on public tn36 G2",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_HISTORY_AUTOMATON_G2="+out["status"])

if __name__=="__main__":
    main()
