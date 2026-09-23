from __future__ import annotations
import hashlib, json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-terminal-directed-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
A=(58,46)
B=(58,11)
SETUP=[A,B]
HIST=[(58,20),(58,22),(55,20),(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]
MAX_DEPTH=8
MAX_STATES=1200
MAX_TRANSITIONS=30000

def env():
    l=logging.getLogger("terminal-directed");l.setLevel(logging.WARNING)
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

def bh(f):
    return hashlib.sha256(json.dumps(grid(f),separators=(",",":")).encode()).hexdigest()

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
        rs=[x[0] for x in cells];cs=[x[1] for x in cells]
        out.append({"color":z,"size":len(cells),"cells":cells,"bbox":(min(rs),min(cs),max(rs),max(cs))})
    return out

def enter2(e,path=()):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    for rc in SETUP+list(path):
      z=click(e,rc)
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space

def candidates(f):
    out=[];seen=set()
    def add(rc):
      if rc not in seen and 0<=rc[0]<64 and 0<=rc[1]<64:
        seen.add(rc);out.append(rc)
    for rc in HIST:add(rc)
    for x in comps(f):
      cells=sorted(x["cells"])
      add(cells[len(cells)//2])
      r0,c0,r1,c1=x["bbox"]
      for rc in ((r0,c0),(r0,c1),(r1,c0),(r1,c1),((r0+r1)//2,(c0+c1)//2)):
        add(rc)
      if x["size"]<=16:
        for rc in cells:add(rc)
    return out

def verify(path,terminal=A):
    outs=[]
    for _ in range(2):
      e=env();enter2(e)
      trace=[]
      for rc in path:
        z=click(e,tuple(rc));trace.append({"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
      if int(e.observation_space.levels_completed)==1 and e.observation_space.state==GameState.NOT_FINISHED:
        z=click(e,terminal);trace.append({"rc":list(terminal),"level":int(z.levels_completed),"state":str(z.state),"terminal":True})
      outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                   "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace})
    return outs

def main():
    e=env()
    root=enter2(e)
    root_hash=bh(root)
    q=deque([()])
    seen={root_hash}
    transitions=0;expanded=0;per_depth=Counter()
    selected=None;verification=[];direct=False

    while q and len(seen)<MAX_STATES and transitions<MAX_TRANSITIONS:
      path=q.popleft();depth=len(path);per_depth[depth]+=1;expanded+=1
      f=enter2(e,path)
      if int(f.levels_completed)>1 or f.state==GameState.WIN:
        selected=list(path);direct=True;break
      if f.state==GameState.GAME_OVER or depth>=MAX_DEPTH:continue

      # First ask the protected future directly: does transported terminal A work now?
      e2=env();enter2(e2,path);ta=click(e2,A)
      transitions+=1
      if int(ta.levels_completed)>1 or ta.state==GameState.WIN:
        v=verify(list(path),A)
        if all(x["progressed"] for x in v):
          selected=list(path);verification=v;break

      reps={}
      for rc in candidates(f):
        z0=enter2(e,path)
        before=bh(z0)
        z=click(e,rc);transitions+=1
        if z is None or z.state==GameState.GAME_OVER:continue
        np=path+(rc,)
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
          # Candidate itself reached protected progress; verify without extra terminal.
          vv=[]
          for _ in range(2):
            ez=env();enter2(ez)
            tr=[]
            for qrc in np:
              zz=click(ez,qrc);tr.append({"rc":list(qrc),"level":int(zz.levels_completed),"state":str(zz.state)})
              if int(zz.levels_completed)>1 or zz.state in (GameState.WIN,GameState.GAME_OVER):break
            vv.append({"progressed":int(ez.observation_space.levels_completed)>1 or ez.observation_space.state==GameState.WIN,
                       "level":int(ez.observation_space.levels_completed),"state":str(ez.observation_space.state),"trace":tr})
          if all(x["progressed"] for x in vv):
            selected=list(np);verification=vv;direct=True;break
        h=bh(z)
        if h==before:continue
        reps.setdefault(h,np)
        if transitions>=MAX_TRANSITIONS:break
      if selected:break
      for h,np in reps.items():
        if h not in seen:
          seen.add(h);q.append(np)
          if len(seen)>=MAX_STATES:break

    if selected is not None and not verification:
      if direct:
        # Verify direct-progress path only.
        vv=[]
        for _ in range(2):
          ez=env();enter2(ez)
          tr=[]
          for rc in selected:
            zz=click(ez,tuple(rc));tr.append({"rc":list(rc),"level":int(zz.levels_completed),"state":str(zz.state)})
            if int(zz.levels_completed)>1 or zz.state in (GameState.WIN,GameState.GAME_OVER):break
          vv.append({"progressed":int(ez.observation_space.levels_completed)>1 or ez.observation_space.state==GameState.WIN,
                     "level":int(ez.observation_space.levels_completed),"state":str(ez.observation_space.state),"trace":tr})
        verification=vv
      else:
        verification=verify(selected,A)

    ok=bool(selected is not None and verification and all(x["progressed"] for x in verification))
    out={
      "source_schema":"A,B,middle*,A with A fixed as transported terminal witness",
      "setup":[list(x) for x in SETUP],
      "terminal":list(A),
      "max_depth":MAX_DEPTH,"max_states":MAX_STATES,"max_transitions":MAX_TRANSITIONS,
      "states_seen":len(seen),"expanded":expanded,"transitions":transitions,
      "per_depth":dict(sorted(per_depth.items())),
      "selected_middle":[list(x) for x in selected] if selected is not None else None,
      "verification":verification,
      "status":"PROMOTED" if ok else "RESIDUAL",
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"semantic-component action pool and exact visible-state quotient after transported setup A,B on public tn36 G2"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_TERMINAL_DIRECTED_G2="+out["status"])

if __name__=="__main__":main()
