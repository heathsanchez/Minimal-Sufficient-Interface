from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-terminal-guard-transport-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
MAX_K=55

def env():
    l=logging.getLogger("terminal-guard");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def labels(f):
    g=grid(f);h,w=len(g),len(g[0]); lab={}; comps=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in lab:continue
            z=g[r][c];idx=len(comps);q=deque([(r,c)]);lab[(r,c)]=idx;cells=[]
            while q:
                rr,cc=q.popleft();cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in lab and g[nr][nc]==z:
                        lab[(nr,nc)]=idx;q.append((nr,nc))
            comps.append({"color":z,"cells":cells,"size":len(cells)})
    return g,lab,comps

def source_guard_cells(f):
    g,lab,cs=labels(f);h,w=len(g),len(g[0]);out=[]
    for i,comp in enumerate(cs):
        if comp["size"]!=69 or comp["color"]!=9:continue
        for r,c in comp["cells"]:
            unlike=[]
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w and lab[(nr,nc)]!=i:
                    unlike.append((nr,nc,g[nr][nc]))
            if not unlike:
                out.append((r,c))
    return out

def enter_k(e,k):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            f=click(e,rc)
            if f is None:raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("anchor drift")
    for i in range(k):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return f
    return e.observation_space

def verify(k,rc):
    out=[]
    for _ in range(2):
        e=env();enter_k(e,k);z=click(e,rc)
        out.append({
            "level":int(z.levels_completed),"state":str(z.state),
            "progressed":int(z.levels_completed)>1 or z.state==GameState.WIN
        })
    return out

def main():
    e=env();scan=[];selected=None;tested=0
    for k in range(MAX_K+1):
        f=enter_k(e,k)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            scan.append({"k":k,"preterminal":True,"state":str(f.state),"level":int(f.levels_completed)})
            break
        cells=source_guard_cells(f)
        row={"k":k,"n":5+k,"guard_cells":len(cells),"first_cells":[list(x) for x in cells[:12]],"tested":0,"outcomes":{"continue":0,"game_over":0,"progress":0}}
        for rc in cells:
            f=enter_k(e,k);z=click(e,rc);tested+=1;row["tested"]+=1
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                row["outcomes"]["progress"]+=1
                selected={"k":k,"rc":list(rc)}
                break
            elif z.state==GameState.GAME_OVER:row["outcomes"]["game_over"]+=1
            else:row["outcomes"]["continue"]+=1
        scan.append(row)
        if selected:break
    ver=verify(selected["k"],tuple(selected["rc"])) if selected else []
    ok=bool(selected and all(x["progressed"] for x in ver))
    out={
        "source_terminal_guard":{"component_size":69,"color":9,"clicked_cell_unlike_4_neighbors":0},
        "scan":scan,"tested_guard_cells":tested,"selected":selected,"verification":ver,
        "status":"PROMOTED" if ok else "RESIDUAL","model_calls":0,"source_inspection":False,
        "claim_boundary":"exact source terminal click guard transported across public tn36 G2 recurrence"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_TERMINAL_GUARD_TRANSPORT_G2="+out["status"])
if __name__=="__main__":main()
