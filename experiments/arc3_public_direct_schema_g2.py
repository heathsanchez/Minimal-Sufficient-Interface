from __future__ import annotations
import itertools, json, logging, os
from collections import Counter, deque, defaultdict
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-direct-schema-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
SETUP=[(58,46),(58,11)]

def env():
    l=logging.getLogger("direct-schema");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc;return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def label_components(f):
    g=grid(f);h,w=len(g),len(g[0]);seen=set();lab={};out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen:continue
            z=g[r][c];idx=len(out);q=deque([(r,c)]);seen.add((r,c));cells=[]
            while q:
                rr,cc=q.popleft();cells.append((rr,cc));lab[(rr,cc)]=idx
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==z:
                        seen.add((nr,nc));q.append((nr,nc))
            rs=[r for r,_ in cells];cs=[c for _,c in cells]
            out.append({"color":z,"size":len(cells),"h":max(rs)-min(rs)+1,"w":max(cs)-min(cs)+1,
                        "cells":sorted(cells),"center":sorted(cells)[len(cells)//2]})
    return g,lab,out

def feat(f):
    g,_,cs=label_components(f);h,w=len(g),len(g[0])
    size=Counter(x["size"] for x in cs);color_size=Counter((x["color"],x["size"]) for x in cs)
    shape=Counter((x["color"],x["h"],x["w"],x["size"]) for x in cs);colors=Counter(v for row in g for v in row)
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"size":size,"color_size":color_size,"shape":shape,"colors":colors,"rt":rt,"ct":ct}

def delta(a,b):
    out={}
    for name in ("size","color_size","shape","colors"):
        keys=set(a[name])|set(b[name])
        out[name]={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
    out["rt"]=b["rt"]-a["rt"];out["ct"]=b["ct"]-a["ct"]
    return {k:v for k,v in out.items() if v not in ({},0)}

def residual(src,tgt):
    out={}
    for name in ("size","color_size","shape","colors"):
        keys=set(src[name])|set(tgt[name])
        d={str(k):int(src[name].get(k,0)-tgt[name].get(k,0)) for k in keys if src[name].get(k,0)!=tgt[name].get(k,0)}
        if d:out[name]=d
    for name in ("rt","ct"):
        v=src[name]-tgt[name]
        if v:out[name]=v
    return out

def source_net():
    e=env();a=feat(e.observation_space)
    for rc in G1[:-1]:click(e,rc)
    return delta(a,feat(e.observation_space))

def enter_level2(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    return feat(e.observation_space),e.observation_space

def relation_toggle_centers(f):
    g,lab,cs=label_components(f);h,w=len(g),len(g[0]);H=[];V=[]
    for i,x in enumerate(cs):
        if x["color"]!=1 or x["size"]!=3:continue
        r,c=x["center"]
        if x["h"]==1 and x["w"]==3:
            neigh=[]
            for dr,dc in ((-1,0),(1,0)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w:
                    j=lab[(nr,nc)];neigh.append(j)
            if len(neigh)==2 and neigh[0]==neigh[1] and cs[neigh[0]]["color"]==0:
                H.append((r,c))
        if x["h"]==3 and x["w"]==1:
            neigh=[]
            for dr,dc in ((0,-1),(0,1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w:
                    j=lab[(nr,nc)];neigh.append(j)
            if len(neigh)==2 and neigh[0]==neigh[1] and cs[neigh[0]]["color"]==0:
                V.append((r,c))
    return sorted(H),sorted(V)

def terminal_cells(f):
    g,lab,cs=label_components(f);h,w=len(g),len(g[0]);out=[]
    for i,x in enumerate(cs):
        if x["color"]!=9 or x["size"]!=69:continue
        for r,c in x["cells"]:
            unlike=False
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w and lab[(nr,nc)]!=i:unlike=True;break
            if not unlike:out.append((r,c))
    return out

def meta(f,rc):
    _,lab,cs=label_components(f);x=cs[lab[tuple(rc)]]
    return (x["color"],x["h"],x["w"],x["size"])

def verify(program):
    out=[]
    for _ in range(2):
        e=env();enter_level2(e)
        trace=[]
        for rc in program:
            z=click(e,tuple(rc));trace.append({"rc":list(rc),"meta":meta(z,tuple(rc)),"level":int(z.levels_completed),"state":str(z.state)})
            if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
        out.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                    "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace})
    return out

def main():
    src=source_net()
    e=env();start,_=enter_level2(e)
    for rc in SETUP:click(e,rc)
    H,V=relation_toggle_centers(e.observation_space)

    hrows=defaultdict(list);vrows=defaultdict(list)
    for r,c in H:hrows[r].append(c)
    for r,c in V:vrows[r].append(c)
    patterns=[]
    for hr,hcs in hrows.items():
        if len(hcs)<3:continue
        for hs in itertools.combinations(sorted(hcs),3):
            for vr,vcs in vrows.items():
                common=sorted(set(hs)&set(vcs))
                if len(common)>=3:
                    for cols in itertools.combinations(common,3):
                        patterns.append({"hrow":hr,"vrow":vr,"cols":list(cols)})
    # Fallback: all 3H x 3V combinations, but exact relational grid patterns are tried first.
    candidates=[]
    seen=set()
    for p in patterns:
        prog=[(p["hrow"],c) for c in p["cols"]]+[(p["vrow"],c) for c in p["cols"]]
        k=tuple(prog)
        if k not in seen:seen.add(k);candidates.append({"kind":"aligned-grid","program":prog})
    if not candidates and len(H)>=3 and len(V)>=3:
        for hs in itertools.combinations(H,3):
            for vs in itertools.combinations(V,3):
                k=tuple(hs+vs)
                if k not in seen:seen.add(k);candidates.append({"kind":"fallback","program":list(hs+vs)})

    attempts=[];selected=None;selected_ver=None
    for cand in candidates:
        e2=env();t0,_=enter_level2(e2)
        for rc in SETUP:click(e2,rc)
        toggles=[];valid=True
        for rc in cand["program"]:
            before=meta(e2.observation_space,rc);z=click(e2,rc);after=meta(z,rc)
            toggles.append({"rc":list(rc),"before":before,"after":after})
            if z.state==GameState.GAME_OVER or before[0]!=1 or after[0]!=5:valid=False;break
        if not valid:continue
        tgt=delta(t0,feat(e2.observation_space));rem=residual(src,tgt)
        att={"kind":cand["kind"],"toggles":toggles,"residual":rem}
        attempts.append(att)
        if rem:continue
        terms=terminal_cells(e2.observation_space);att["terminal_cells"]=len(terms)
        for tc in terms:
            full=[list(x) for x in SETUP+cand["program"]+[tc]]
            ver=verify(full)
            if all(x["progressed"] for x in ver):
                selected=full;selected_ver=ver;break
        if selected:break

    out={
        "source_schema":"2 setup operators + 3 horizontal toggles + 3 vertical toggles + terminal",
        "setup":[list(x) for x in SETUP],
        "toggle_candidates":{"horizontal":[list(x) for x in H],"vertical":[list(x) for x in V],"aligned_patterns":patterns},
        "candidate_programs":len(candidates),"attempts_tested":len(attempts),
        "zero_residual_attempts":[x for x in attempts if not x["residual"]],
        "selected_program":selected,"verification":selected_ver or [],
        "status":"PROMOTED" if selected else "RESIDUAL","model_calls":0,"source_inspection":False,
        "claim_boundary":"direct transport of G1 relational operator schema to exact public tn36 G2"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_DIRECT_SCHEMA_G2="+out["status"])
if __name__=="__main__":main()
