from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-component-terminal-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC_STEPS=55

def env():
    l=logging.getLogger("component-terminal");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter_boundary(e):
    if int(e.observation_space.levels_completed)==0:
        for rc in G1: click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in ANCHOR: click(e,rc)
    for _ in range(REC_STEPS):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"boundary drift {f.levels_completed} {f.state}")
    return e.observation_space

def reset_boundary(e):
    f=e.reset()
    if int(f.levels_completed)==0:
        return enter_boundary(e)
    if int(f.levels_completed)!=1:
        raise RuntimeError(f"reset drift {f.levels_completed}")
    for rc in ANCHOR: click(e,rc)
    for _ in range(REC_STEPS):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"boundary drift {f.levels_completed} {f.state}")
    return e.observation_space

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def components(f):
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
            rs=[r for r,_ in cells];cs=[c for _,c in cells]
            out.append({
                "color":z,"size":len(cells),"cells":cells,
                "bbox":[min(rs),min(cs),max(rs),max(cs)],
                "rep":cells[len(cells)//2],
            })
    return out

def test(e,rc):
    reset_boundary(e)
    f=click(e,rc)
    return {"rc":list(rc),"level":int(f.levels_completed),"state":str(f.state),
            "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,
            "game_over":f.state==GameState.GAME_OVER}

def verify(rc):
    rows=[]
    for _ in range(2):
        e=env();enter_boundary(e);f=click(e,rc)
        rows.append({"level":int(f.levels_completed),"state":str(f.state),
                     "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN})
    return rows

def main():
    e=env();b=enter_boundary(e);cs=components(b)
    summary=[{"i":i,"color":x["color"],"size":x["size"],"bbox":x["bbox"],"rep":list(x["rep"])} for i,x in enumerate(cs)]
    order=sorted(range(len(cs)),key=lambda i:(0 if cs[i]["size"] in (69,60,1) else 1,cs[i]["size"],cs[i]["color"],i))
    tested=[];success=None
    for i in order:
        comp=cs[i]
        reps=[comp["rep"],comp["cells"][0],comp["cells"][-1]]
        seen=set()
        for rc in reps:
            if rc in seen:continue
            seen.add(rc)
            z=test(e,rc);z["component"]=i;tested.append(z)
            if z["progressed"]:
                success=rc;break
        if success is not None:break
    v=verify(success) if success else []
    out={"components":summary,"tested":tested,"selected":list(success) if success else None,
         "verification":v,"status":"PROMOTED" if v and all(x["progressed"] for x in v) else "RESIDUAL",
         "model_calls":0,"source_inspection":False}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_COMPONENT_TERMINAL_G2="+out["status"])

if __name__=="__main__":main()
