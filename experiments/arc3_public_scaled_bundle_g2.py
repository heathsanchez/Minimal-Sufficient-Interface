from __future__ import annotations
import json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-scaled-bundle-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
PREFIX=[(58,46),(58,11),(58,20)]  # setup0, setup1, observed 4-vertical bundle

def env():
    l=logging.getLogger("scaled-bundle");l.setLevel(logging.WARNING)
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
def comps(f):
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
        rs=[x[0] for x in cells];cs=[x[1] for x in cells]
        out.append({"color":z,"size":len(cells),"h":max(rs)-min(rs)+1,"w":max(cs)-min(cs)+1,"cells":cells})
    return g,lab,out
def feat(f):
    g,_,cs=comps(f);h,w=len(g),len(g[0]);shape=Counter();colors=Counter(v for row in g for v in row)
    for x in cs:shape[(x["color"],x["h"],x["w"],x["size"])]+=1
    return {"shape":shape,"colors":colors}
def delta(a,b):
    out={}
    for name in ("shape","colors"):
      keys=set(a[name])|set(b[name])
      out[name]={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
    return out
def reset_level2(e):
    f=e.reset()
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    return e.observation_space
def replay_prefix(e,extra=()):
    reset_level2(e)
    for rc in PREFIX:
      z=click(e,rc)
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):raise RuntimeError("prefix drift")
    for rc in extra:
      z=click(e,rc)
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space
def horizontal4(ed):
    s=ed.get("shape",{});c=ed.get("colors",{})
    return (
      s.get("(1, 1, 3, 3)",0)==-4 and
      s.get("(5, 1, 3, 3)",0)==4 and
      c.get("1",0)==-12 and c.get("5",0)==12 and
      c.get("3",0)==1 and c.get("9",0)==-1
    )
def terminal_cells(f):
    g,lab,cs=comps(f);h,w=len(g),len(g[0]);out=[]
    for i,x in enumerate(cs):
      if x["color"]!=9 or x["size"]!=69:continue
      for r,c in x["cells"]:
        if all(not(0<=r+dr<h and 0<=c+dc<w) or lab[(r+dr,c+dc)]==i for dr,dc in ((1,0),(-1,0),(0,1),(0,-1))):
          out.append((r,c))
    return out
def verify(program):
    outs=[]
    for _ in range(2):
      e=env();reset_level2(e)
      for rc in program:
        z=click(e,tuple(rc))
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
      outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                   "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)})
    return outs
def main():
    e=env();candidates=[];classes={}
    for r in range(64):
      for c in range(64):
        f=replay_prefix(e);before=feat(f);z=click(e,(r,c))
        if z is None or z.state==GameState.GAME_OVER:continue
        if int(z.levels_completed)>1 or z.state==GameState.WIN:
          candidates.append({"rc":[r,c],"direct_progress":True,"effect":delta(before,feat(z))});break
        ed=delta(before,feat(z));k=json.dumps(ed,sort_keys=True,separators=(",",":"))
        classes.setdefault(k,{"rc":[r,c],"effect":ed,"count":0});classes[k]["count"]+=1
        if horizontal4(ed):candidates.append({"rc":[r,c],"direct_progress":False,"effect":ed})
      if candidates and candidates[-1]["direct_progress"]:break

    selected=None;ver=[];attempts=[]
    for cand in candidates:
      if cand["direct_progress"]:
        full=[list(x) for x in PREFIX]+[cand["rc"]];vv=verify(full)
        attempts.append({"horizontal":cand["rc"],"terminal":None,"verification":vv})
        if all(x["progressed"] for x in vv):selected=full;ver=vv;break
        continue
      e2=env();replay_prefix(e2);z=click(e2,tuple(cand["rc"]))
      terms=terminal_cells(z)
      att={"horizontal":cand["rc"],"terminal_cells":[list(x) for x in terms]}
      attempts.append(att)
      # First test exact transported terminal-guard cells.
      for tc in terms:
        full=[list(x) for x in PREFIX]+[cand["rc"],list(tc)]
        vv=verify(full)
        if all(x["progressed"] for x in vv):selected=full;ver=vv;att["selected_terminal"]=list(tc);break
      if selected:break
      # If guard representation differs, exhaustively test the one terminal click only.
      for r in range(64):
        for c in range(64):
          e3=env();replay_prefix(e3,[tuple(cand["rc"])]);zz=click(e3,(r,c))
          if int(zz.levels_completed)>1 or zz.state==GameState.WIN:
            full=[list(x) for x in PREFIX]+[cand["rc"],[r,c]];vv=verify(full)
            if all(x["progressed"] for x in vv):selected=full;ver=vv;att["selected_terminal"]=[r,c];break
        if selected:break
      if selected:break

    out={
      "hypothesis":"G2 scales G1 toggle bundle width from 3 to 4",
      "prefix":[list(x) for x in PREFIX],
      "effect_classes":len(classes),
      "horizontal4_candidates":candidates,
      "attempts":attempts,
      "selected_program":selected,"verification":ver,
      "status":"PROMOTED" if selected else "RESIDUAL",
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"exact public tn36 G2 scaled bundle law"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2));print("ARC3_PUBLIC_SCALED_BUNDLE_G2="+out["status"])
if __name__=="__main__":main()
