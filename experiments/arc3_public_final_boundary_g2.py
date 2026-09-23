from __future__ import annotations
import json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-final-boundary-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC_TO_BOUNDARY=55

def env():
    l=logging.getLogger("final-boundary");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def enter2(e):
    if int(e.observation_space.levels_completed)==0:
        for rc in G1:
            f=click(e,rc)
            if f is None: raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1: raise RuntimeError("g1 drift")
    return e.observation_space

def replay_boundary(e):
    f=e.reset()
    if int(f.levels_completed)==0:
        enter2(e)
    elif int(f.levels_completed)!=1:
        raise RuntimeError(f"reset drift {f.levels_completed}")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return f
    for _ in range(REC_TO_BOUNDARY):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            return f
    return e.observation_space

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)): x=x[-1]
    if hasattr(x,"tolist"): x=x.tolist()
    return [[int(v) for v in row] for row in x]

def components(f):
    g=grid(f);h,w=len(g),len(g[0]);seen=set();out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen: continue
            z=g[r][c];q=deque([(r,c)]);seen.add((r,c));cells=[]
            while q:
                rr,cc=q.popleft();cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==z:
                        seen.add((nr,nc));q.append((nr,nc))
            out.append({"size":len(cells),"color":z,"cells":cells})
    return out

def semantic_candidates(f):
    g=grid(f);h,w=len(g),len(g[0])
    cs=[c for c in components(f) if c["size"] in (1,60)]
    pts=[];seen=set()
    def add(p):
        r,c=p
        if 0<=r<h and 0<=c<w and p not in seen:
            seen.add(p);pts.append(p)
    add(REC)
    for comp in cs:
        for r,c in comp["cells"]:
            add((r,c))
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    add((r+dr,c+dc))
    return pts, [{"size":c["size"],"color":c["color"],"cells":len(c["cells"])} for c in cs]

def test_candidate(e,rc):
    b=replay_boundary(e)
    if int(b.levels_completed)!=1 or b.state in (GameState.WIN,GameState.GAME_OVER):
        return {"rc":list(rc),"boundary_invalid":True,"level":int(b.levels_completed),"state":str(b.state)}
    f=click(e,rc)
    return {
        "rc":list(rc),
        "level":int(f.levels_completed),
        "state":str(f.state),
        "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,
        "game_over":f.state==GameState.GAME_OVER,
    }

def verify(rc):
    out=[]
    for _ in range(2):
        e=env();enter2(e)
        b=replay_boundary(e)
        f=click(e,rc)
        out.append({"level":int(f.levels_completed),"state":str(f.state),"progressed":int(f.levels_completed)>1 or f.state==GameState.WIN})
    return out

def main():
    e=env();enter2(e);b=replay_boundary(e)
    cand, comps=semantic_candidates(b)
    tested=[];success=None
    for rc in cand:
        z=test_candidate(e,rc);tested.append(z)
        if z.get("progressed"):
            success=rc;break
    fallback_used=False
    if success is None:
        fallback_used=True
        seen=set(cand)
        for r in range(64):
            for c in range(64):
                if (r,c) in seen: continue
                z=test_candidate(e,(r,c));tested.append(z)
                if z.get("progressed"):
                    success=(r,c);break
            if success is not None: break
    v=verify(success) if success is not None else []
    ok=bool(v and all(x["progressed"] for x in v))
    out={
        "boundary":"after anchor + 55 recurrence steps (immediately before 56th recurrence GAME_OVER)",
        "components_of_interest":comps,
        "semantic_candidates":len(cand),
        "tested":len(tested),
        "fallback_full_grid":fallback_used,
        "selected":list(success) if success else None,
        "verification":v,
        "program":[list(x) for x in ANCHOR]+[list(REC)]*REC_TO_BOUNDARY+([list(success)] if success else []),
        "level2_actions":len(ANCHOR)+REC_TO_BOUNDARY+(1 if success else 0),
        "model_calls":0,
        "source_inspection":False,
        "status":"PROMOTED" if ok else "RESIDUAL",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_FINAL_BOUNDARY_G2="+out["status"])

if __name__=="__main__":
    main()
