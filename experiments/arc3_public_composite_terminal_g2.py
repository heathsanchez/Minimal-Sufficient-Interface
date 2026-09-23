from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-composite-terminal-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20); REC_STEPS=55
PRIMS=["ACTION1","ACTION2","ACTION3","ACTION4","ACTION5","ACTION7"]
KEY_SIZES={1,6,32,41,60,69}

def env():
    l=logging.getLogger("composite-terminal");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def mouse(e,rc):
    r,c=rc; return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter_boundary(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1: mouse(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in ANCHOR: mouse(e,rc)
    for i in range(REC_STEPS):
        f=mouse(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"boundary drift {i+1}")
    return e.observation_space

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def comps(f):
    g=grid(f);h,w=len(g),len(g[0]);seen=set();out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen:continue
            z=g[r][c];q=deque([(r,c)]);seen.add((r,c));cells=[]
            while q:
                rr,cc=q.popleft();cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==z:
                        seen.add((nr,nc));q.append((nr,nc))
            out.append({"size":len(cells),"color":z,"cells":cells})
    return out

def role_actions(f):
    rows=[]
    seen=set()
    def add_mouse(rc,label):
        key=("M",rc)
        if key not in seen:
            seen.add(key);rows.append({"kind":"mouse","rc":list(rc),"label":label})
    add_mouse(REC,"recurrence")
    for i,c in enumerate(comps(f)):
        if c["size"] not in KEY_SIZES:continue
        cells=c["cells"]
        for rc,tag in ((cells[0],"first"),(cells[len(cells)//2],"mid"),(cells[-1],"last")):
            add_mouse(rc,f"comp{i}:size{c['size']}:color{c['color']}:{tag}")
    for p in PRIMS:
        rows.append({"kind":"primitive","action":p,"label":p})
    return rows

def apply(e,a):
    if a["kind"]=="mouse":return mouse(e,tuple(a["rc"]))
    return e.step(GameAction[a["action"]])

def run_seq(e,seq):
    enter_boundary(e)
    trace=[]
    for i,a in enumerate(seq):
        f=apply(e,a)
        if f is None:return {"valid":False,"trace":trace}
        trace.append({"i":i,"label":a["label"],"level":int(f.levels_completed),"state":str(f.state)})
        if int(f.levels_completed)>1 or f.state==GameState.WIN:
            return {"valid":True,"progressed":True,"trace":trace,"level":int(f.levels_completed),"state":str(f.state)}
        if f.state==GameState.GAME_OVER:
            return {"valid":True,"progressed":False,"game_over":True,"trace":trace,"level":int(f.levels_completed),"state":str(f.state)}
    return {"valid":True,"progressed":False,"game_over":False,"trace":trace,"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

def verify(seq):
    out=[]
    for _ in range(2):
        e=env();z=run_seq(e,seq)
        out.append({"progressed":bool(z.get("progressed")),"level":z.get("level"),"state":z.get("state"),"trace":z.get("trace")})
    return out

def main():
    e=env();b=enter_boundary(e);alphabet=role_actions(b)
    tested=0;selected=None;selected_result=None
    counts={"progress":0,"game_over":0,"continue":0,"invalid":0}
    for a in alphabet:
        for b in alphabet:
            z=run_seq(e,[a,b]);tested+=1
            if not z.get("valid"):counts["invalid"]+=1;continue
            if z.get("progressed"):
                counts["progress"]+=1;selected=[a,b];selected_result=z;break
            if z.get("game_over"):counts["game_over"]+=1
            else:counts["continue"]+=1
        if selected:break
    ver=verify(selected) if selected else []
    ok=bool(selected and all(x["progressed"] for x in ver))
    out={"alphabet_size":len(alphabet),"alphabet":alphabet,"tested_pairs":tested,"outcomes":counts,
         "selected":selected,"selected_result":selected_result,"verification":ver,
         "status":"PROMOTED" if ok else "RESIDUAL","model_calls":0,"source_inspection":False,
         "claim_boundary":"exact public tn36 G2 depth-2 relational composite synthesis"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_COMPOSITE_TERMINAL_G2="+out["status"])
if __name__=="__main__":main()
