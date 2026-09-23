from __future__ import annotations
import json,logging,os,hashlib
from collections import Counter,deque
from pathlib import Path
from arc_agi import Arcade,OperationMode
from arcengine import GameAction,GameState

GAME="tn36-ef4dde99";ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-recurrence-boundary-g2")).resolve();OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
MAX_STEPS=50;MAX_TRANSITIONS=12000

def env():
 l=logging.getLogger("rec-boundary");l.setLevel(logging.WARNING)
 a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l);card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
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
   out.append(cells)
 return out
def area_counter(f):
 g=grid(f);total=len(g)*len(g[0]);return Counter(len(c) for c in components(f) if len(c)<=max(16,total//4))
def delta(a,b):return {int(k):b.get(k,0)-a.get(k,0) for k in set(a)|set(b) if b.get(k,0)!=a.get(k,0)}
def expected(n):
 R=61-n;return {n:-1,n+1:1,R-1:1,R:-1}
def enter2(e):
 if int(e.observation_space.levels_completed)==0:
  for rc in G1:click(e,rc)
 if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1")
 return e.observation_space
def reset2(e):
 f=e.reset()
 if int(f.levels_completed)==0:return enter2(e)
 if int(f.levels_completed)!=1:raise RuntimeError(f"reset {f.levels_completed}")
 return f
def replay(e,path):
 reset2(e)
 for rc in ANCHOR+path:
  f=click(e,rc)
  if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):break
 return e.observation_space

def semantic_candidates(f,n):
 g=grid(f);h,w=len(g),len(g[0]);R=61-n
 cs=components(f);selected=[]
 for cells in cs:
  if len(cells) in (n,R):
   selected.extend(cells)
   for r,c in cells:
    for dr in (-1,0,1):
     for dc in (-1,0,1):
      nr,nc=r+dr,c+dc
      if 0<=nr<h and 0<=nc<w:selected.append((nr,nc))
 seen=set();out=[]
 for p in selected:
  if p not in seen:seen.add(p);out.append(p)
 return out

def main():
 e=env();enter2(e);path=[];trace=[];transitions=0;n=5
 while n<5+MAX_STEPS and transitions<MAX_TRANSITIONS:
  f=replay(e,path)
  if int(f.levels_completed)>1:break
  before=area_counter(f);want=expected(n)
  local=semantic_candidates(f,n)
  pools=[("semantic",local),("fallback",[(r,c) for r in range(64) for c in range(64)])]
  chosen=None;progress=None;tested=0
  for mode,pool in pools:
   matches=[]
   for rc in pool:
    replay(e,path);a=area_counter(e.observation_space);z=click(e,rc);transitions+=1;tested+=1
    if z is None or z.state==GameState.GAME_OVER:continue
    if int(z.levels_completed)>1 or z.state==GameState.WIN:
     progress=rc;break
    if delta(a,area_counter(z))==want:matches.append(rc)
    if transitions>=MAX_TRANSITIONS:break
   if progress is not None:break
   if matches:
    prev=(ANCHOR+path)[-1]
    matches.sort(key=lambda p:(abs(p[0]-prev[0])+abs(p[1]-prev[1]),p[0],p[1]))
    chosen=matches[0];break
   if transitions>=MAX_TRANSITIONS:break
  trace.append({"n":n,"expected":want,"semantic_candidates":len(local),"tested":tested,
                "chosen":list(chosen) if chosen else None,"progress":list(progress) if progress else None})
  if progress is not None:
   path.append(progress);break
  if chosen is None:break
  path.append(chosen);n+=1

 v=[]
 if path:
  for _ in range(2):
   z=env();enter2(z)
   for rc in ANCHOR+path:
    f=click(z,rc)
    if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):break
   v.append({"level":int(z.observation_space.levels_completed),"state":str(z.observation_space.state),
             "progressed":int(z.observation_space.levels_completed)>1})
 ok=bool(v and all(x["progressed"] for x in v))
 out={"law":"grow n->n+1, reservoir 61-n -> 60-n","anchor":[list(x) for x in ANCHOR],
      "tail":[list(x) for x in path],"program":[list(x) for x in ANCHOR+path],
      "transitions":transitions,"trace":trace,"verification":v,"model_calls":0,"source_inspection":False,
      "status":"PROMOTED" if ok else "RESIDUAL"}
 (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_RECURRENCE_BOUNDARY_G2="+out["status"])
if __name__=="__main__":main()
