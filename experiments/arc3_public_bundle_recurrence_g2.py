from __future__ import annotations
import json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-bundle-recurrence-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
SETUP=[(58,46),(58,11)]
MAX_BUNDLES=55

def env():
    l=logging.getLogger("bundle-recurrence");l.setLevel(logging.WARNING)
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

def comps(f):
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
        rs=[x[0] for x in cells];cs=[x[1] for x in cells]
        out.append({"color":z,"size":len(cells),"h":max(rs)-min(rs)+1,"w":max(cs)-min(cs)+1,"cells":cells})
    return g,lab,out

def feat(f):
    _,_,cs=comps(f)
    color_size=Counter((x["color"],x["size"]) for x in cs)
    shape=Counter((x["color"],x["h"],x["w"],x["size"]) for x in cs)
    colors=Counter()
    for x in cs: colors[x["color"]]+=x["size"]
    return {"color_size":color_size,"shape":shape,"colors":colors}

def diff(a,b):
    out={}
    for name in ("color_size","shape","colors"):
      keys=set(a[name])|set(b[name])
      d={str(k):int(b[name].get(k,0)-a[name].get(k,0)) for k in keys if b[name].get(k,0)!=a[name].get(k,0)}
      if d:out[name]=d
    return out

def count_size3(f,color):
    _,_,cs=comps(f)
    return sum(1 for x in cs if x["color"]==color and x["size"]==3)

def enter2(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    return e.observation_space

def replay(e,path):
    enter2(e)
    for rc in SETUP+path:
      z=click(e,rc)
      if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space

def bundle_score(before,after):
    c1a=count_size3(before,1);c1b=count_size3(after,1)
    c5a=count_size3(before,5);c5b=count_size3(after,5)
    removed=c1a-c1b;added=c5b-c5a
    if removed<=0 or added!=removed:return None
    return removed

def terminal_cells(f):
    g,lab,cs=comps(f);h,w=len(g),len(g[0]);out=[]
    for i,x in enumerate(cs):
      if x["color"]!=9 or x["size"]!=69:continue
      for r,c in x["cells"]:
        # Prefer interior cells in the transported terminal component.
        if all(not(0<=r+dr<h and 0<=c+dc<w) or lab[(r+dr,c+dc)]==i for dr,dc in ((1,0),(-1,0),(0,1),(0,-1))):
          out.append((r,c))
    return out

def verify(program):
    outs=[]
    for _ in range(2):
      e=env();enter2(e)
      for rc in program:
        z=click(e,tuple(rc))
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
      outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                   "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)})
    return outs

def main():
    e=env();path=[];trace=[];tested=0
    for step in range(MAX_BUNDLES):
      f=replay(e,path)
      if int(f.levels_completed)>1 or f.state==GameState.WIN:break
      c1=count_size3(f,1)
      if c1==0:break
      classes={}
      best=None
      for r in range(64):
        for c in range(64):
          before=replay(e,path); fb=feat(before); c1_before=count_size3(before,1)
          z=click(e,(r,c)); tested+=1
          if z is None or z.state==GameState.GAME_OVER:continue
          if int(z.levels_completed)>1 or z.state==GameState.WIN:
            program=[list(x) for x in SETUP+path+[(r,c)]]
            ver=verify(program)
            out={"status":"PROMOTED" if all(x["progressed"] for x in ver) else "RESIDUAL",
                 "program":program,"verification":ver,"trace":trace,"tested":tested,
                 "model_calls":0,"source_inspection":False}
            (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_BUNDLE_RECURRENCE_G2="+out["status"]);return
          score=bundle_score(before,z)
          if score is None:continue
          fd=diff(fb,feat(z));key=json.dumps(fd,sort_keys=True,separators=(",",":"))
          classes.setdefault(key,{"rc":[r,c],"score":score,"effect":fd,"count":0});classes[key]["count"]+=1
          rec=classes[key]
          cand=(-score, r, c)
          if best is None or cand < best[0]: best=(cand,(r,c),score,fd,c1_before,count_size3(z,1))
      if best is None:
        trace.append({"step":step,"status":"NO_BUNDLE","remaining_color1_size3":c1,"classes":len(classes)})
        break
      _,rc,score,fd,before_count,after_count=best
      path.append(rc)
      trace.append({"step":step,"chosen":list(rc),"bundle_size":score,"before_color1_size3":before_count,
                    "after_color1_size3":after_count,"effect":fd,"classes":len(classes)})

    # Terminal test as soon as bundle recurrence stops or clears the guard.
    f=replay(e,path)
    terms=terminal_cells(f)
    attempts=[]
    for tc in terms:
      program=[list(x) for x in SETUP+path+[tc]]
      ver=verify(program); attempts.append({"terminal":list(tc),"verification":ver})
      if all(x["progressed"] for x in ver):
        out={"status":"PROMOTED","program":program,"verification":ver,"trace":trace,
             "remaining_color1_size3":count_size3(f,1),"terminal_candidates":len(terms),
             "terminal_attempts":attempts,"tested":tested,"model_calls":0,"source_inspection":False,
             "claim_boundary":"exact public tn36 G2 maximal residual-reducing bundle recurrence to closure + transported terminal guard"}
        (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_BUNDLE_RECURRENCE_G2=PROMOTED");return

    out={"status":"RESIDUAL","program":[list(x) for x in SETUP+path],"verification":[],"trace":trace,
         "remaining_color1_size3":count_size3(f,1),"terminal_candidates":len(terms),
         "terminal_attempts":attempts,"tested":tested,"model_calls":0,"source_inspection":False,
         "claim_boundary":"exact public tn36 G2 maximal bundle recurrence + transported terminal guard"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_BUNDLE_RECURRENCE_G2=RESIDUAL")

if __name__=="__main__":
    main()
