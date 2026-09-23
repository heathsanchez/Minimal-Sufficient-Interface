from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-submit-timing-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
MAX_K=55

def env():
    l=logging.getLogger("submit-timing");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def comp_records(f):
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
            neigh=set()
            own=set(cells)
            for rr,cc in cells:
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    p=(rr+dr,cc+dc)
                    if 0<=p[0]<h and 0<=p[1]<w and p not in own:
                        neigh.add(g[p[0]][p[1]])
            out.append({"color":z,"size":len(cells),"cells":cells,"neighbor_colors":sorted(neigh)})
    return out

def enter_k(e,k):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            f=click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("anchor drift")
    for i in range(k):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return f
    return e.observation_space

def candidate_object(f):
    exact=[c for c in comp_records(f) if c["size"]==69 and c["color"]==9]
    if not exact:return None
    # Source terminal object has no distinct neighboring component relation.
    exact.sort(key=lambda c:(len(c["neighbor_colors"]),min(c["cells"])))
    cells=exact[0]["cells"]
    return cells[len(cells)//2], {"size":69,"color":9,"neighbor_colors":exact[0]["neighbor_colors"],"count":len(exact)}

def main():
    e=env();rows=[];selected=None
    for k in range(MAX_K+1):
        f=enter_k(e,k)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            rows.append({"k":k,"preterminal":True,"level":int(f.levels_completed),"state":str(f.state)})
            break
        got=candidate_object(f)
        if got is None:
            rows.append({"k":k,"candidate":None})
            continue
        rc,meta=got
        z=click(e,rc)
        row={"k":k,"candidate":list(rc),"meta":meta,"level":int(z.levels_completed),"state":str(z.state),
             "progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,"game_over":z.state==GameState.GAME_OVER}
        rows.append(row)
        if row["progressed"]:
            selected={"k":k,"rc":list(rc)}
            break
    verify=[]
    if selected:
        for _ in range(2):
            z=env();f=enter_k(z,selected["k"]);f=click(z,tuple(selected["rc"]))
            verify.append({"level":int(f.levels_completed),"state":str(f.state),"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN})
    ok=bool(selected and all(x["progressed"] for x in verify))
    out={"source_terminal_relation":{"size":69,"color":9,"isolated":True},"scan":rows,"selected":selected,
         "verification":verify,"status":"PROMOTED" if ok else "RESIDUAL","model_calls":0,"source_inspection":False}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_SUBMIT_TIMING_G2="+out["status"])
if __name__=="__main__":main()
