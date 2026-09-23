from __future__ import annotations
import itertools, json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-shape-residual-repair-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20); REC_STEPS=3

def env():
    l=logging.getLogger("shape-repair");l.setLevel(logging.WARNING)
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

def components(f):
    g=grid(f);h,w=len(g),len(g[0]);seen=set();out=[];lab={}
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
    g,_,cs=components(f)
    size=Counter(x["size"] for x in cs)
    color_size=Counter((x["color"],x["size"]) for x in cs)
    shape=Counter((x["color"],x["h"],x["w"],x["size"]) for x in cs)
    colors=Counter(v for row in g for v in row)
    h,w=len(g),len(g[0])
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"size":size,"color_size":color_size,"shape":shape,"colors":colors,"rt":rt,"ct":ct}

def delta(a,b):
    out={}
    for name in ("size","color_size","shape","colors"):
        keys=set(a[name])|set(b[name])
        out[name]={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
    out["rt"]=b["rt"]-a["rt"];out["ct"]=b["ct"]-a["ct"]
    return out

def residual(src,tgt):
    out={}
    for name in ("size","color_size","shape","colors"):
        keys=set(src[name])|set(tgt[name])
        out[name]={str(k):int(src[name].get(k,0)-tgt[name].get(k,0)) for k in keys if src[name].get(k,0)!=tgt[name].get(k,0)}
    out["rt"]=src["rt"]-tgt["rt"];out["ct"]=src["ct"]-tgt["ct"]
    return {k:v for k,v in out.items() if v not in ({},0)}

def source_net():
    e=env();a=feat(e.observation_space)
    for rc in G1[:-1]:click(e,rc)
    return delta(a,feat(e.observation_space))

def enter_matched(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    start=feat(e.observation_space)
    for rc in ANCHOR:click(e,rc)
    for _ in range(REC_STEPS):click(e,REC)
    return start,e.observation_space

def shape_centers(f,color,h,w):
    _,_,cs=components(f)
    return [tuple(x["center"]) for x in cs if x["color"]==color and x["size"]==3 and x["h"]==h and x["w"]==w]

def terminal_cells(f):
    g,lab,cs=components(f);h,w=len(g),len(g[0]);out=[]
    for i,x in enumerate(cs):
        if x["color"]!=9 or x["size"]!=69:continue
        for r,c in x["cells"]:
            unlike=0
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w and lab[(nr,nc)]!=i:unlike+=1
            if unlike==0:out.append((r,c))
    return out

def verify(program):
    out=[]
    for _ in range(2):
        e=env();enter_matched(e)
        for rc in program:
            z=click(e,tuple(rc))
            if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
        out.append({"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
                    "progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN})
    return out

def main():
    src=source_net()
    e=env();t0,f=enter_matched(e)
    h1=shape_centers(f,1,1,3)
    v5=shape_centers(f,5,3,1)
    attempts=[];selected=None;selected_ver=None
    # Exact residual says: 3 horizontal color1 strips -> color5, 1 vertical color5 strip -> color1.
    for hs in itertools.combinations(h1,3):
        for vv in v5:
            if vv in hs:continue
            e2=env();start,state=enter_matched(e2)
            program=[list(x) for x in hs]+[list(vv)]
            valid=True;toggles=[]
            for rc in program:
                before_grid,lab,cs=components(e2.observation_space);bi=lab[tuple(rc)]
                before=(cs[bi]["color"],cs[bi]["h"],cs[bi]["w"],cs[bi]["size"])
                z=click(e2,tuple(rc))
                if z.state==GameState.GAME_OVER:valid=False;break
                after_grid,lab2,cs2=components(e2.observation_space);ai=lab2[tuple(rc)]
                after=(cs2[ai]["color"],cs2[ai]["h"],cs2[ai]["w"],cs2[ai]["size"])
                toggles.append({"rc":rc,"before":before,"after":after})
            if not valid:continue
            tgt=delta(start,feat(e2.observation_space))
            rem=residual(src,tgt)
            att={"repair":program,"residual":rem,"toggles":toggles}
            attempts.append(att)
            if rem:continue
            terms=terminal_cells(e2.observation_space)
            att["terminal_cells"]=len(terms)
            for tc in terms:
                full=program+[list(tc)]
                ver=verify(full)
                if all(x["progressed"] for x in ver):
                    selected=full;selected_ver=ver;break
            if selected:break
        if selected:break
    out={
        "source_net":src,
        "matched_candidates":{"horizontal_color1": [list(x) for x in h1],"vertical_color5":[list(x) for x in v5]},
        "attempts_tested":len(attempts),
        "zero_residual_repairs":[x for x in attempts if not x["residual"]],
        "selected_program":selected,"verification":selected_ver or [],
        "status":"PROMOTED" if selected else "RESIDUAL","model_calls":0,"source_inspection":False,
        "claim_boundary":"exact shape/color residual repair then transported G1 terminal operator on public tn36 G2"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SHAPE_RESIDUAL_REPAIR_G2="+out["status"])
if __name__=="__main__":main()
