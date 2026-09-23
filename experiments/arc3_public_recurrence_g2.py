from __future__ import annotations
import json,logging,os,hashlib
from collections import Counter,deque
from pathlib import Path
from arc_agi import Arcade,OperationMode
from arcengine import GameAction,GameState

GAME="tn36-ef4dde99";ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-recurrence-g2")).resolve();OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
MAX_GROW=40;MAX_TRANSITIONS=60000

def env():
 l=logging.getLogger("recurrence");l.setLevel(logging.WARNING)
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
def bh(f):return hashlib.sha256(json.dumps(grid(f),separators=(",",":")).encode()).hexdigest()
def comps(g):
 h,w=len(g),len(g[0]);seen=set();out=[]
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
def areas(f):
 g=grid(f);total=len(g)*len(g[0]);return Counter(len(c) for c in comps(g) if len(c)<=max(16,total//4))
def delta(a,b):return {int(k):b.get(k,0)-a.get(k,0) for k in set(a)|set(b) if b.get(k,0)!=a.get(k,0)}

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

def expected(n):
 # Observed source law: growing n -> n+1 while reservoir (61-n) -> (60-n).
 R=61-n
 return {n:-1,n+1:1,R-1:1,R:-1}

def search():
 e=env();enter2(e)
 transitions=0;nodes=0;visited=set();trace=[]
 def dfs(path,n):
  nonlocal transitions,nodes
  if n>MAX_GROW or transitions>=MAX_TRANSITIONS:return None
  f=replay(e,path)
  if int(f.levels_completed)>1:return path
  if f.state==GameState.GAME_OVER:return None
  key=(bh(f),n)
  if key in visited:return None
  visited.add(key);nodes+=1
  base=areas(f);want=expected(n)
  recurrence=[];progress=[]
  for r in range(64):
   for c in range(64):
    if transitions>=MAX_TRANSITIONS:break
    replay(e,path);before=areas(e.observation_space);z=click(e,(r,c));transitions+=1
    if z is None or z.state==GameState.GAME_OVER:continue
    if int(z.levels_completed)>1 or z.state==GameState.WIN:
     progress.append((r,c));continue
    d=delta(before,areas(z))
    if d==want:recurrence.append((r,c))
   if transitions>=MAX_TRANSITIONS:break
  trace.append({"n":n,"path_len":len(path),"expected":want,"recurrence_candidates":len(recurrence),
                "first_candidates":[list(x) for x in recurrence[:20]],"progress_candidates":len(progress)})
  if progress:return path+[progress[0]]
  # Continuation-safe ordering: near the previous target-side anchor first, then deterministic.
  prev=(ANCHOR+path)[-1]
  recurrence.sort(key=lambda p:(abs(p[0]-prev[0])+abs(p[1]-prev[1]),p[0],p[1]))
  for rc in recurrence:
   got=dfs(path+[rc],n+1)
   if got is not None:return got
  return None
 program=dfs([],5)
 return program,{"transitions":transitions,"nodes":nodes,"visited":len(visited),"trace":trace}

def verify(tail):
 out=[]
 if not tail:return out
 for _ in range(2):
  e=env();enter2(e)
  for rc in ANCHOR+tail:
   f=click(e,rc)
   if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):break
  out.append({"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),
              "progressed":int(e.observation_space.levels_completed)>1})
 return out

def main():
 tail,stats=search();v=verify(tail);ok=bool(v and all(x["progressed"] for x in v))
 out={"source_run":35811403514,"g1_run":35854403385,"alignment_run":35861739794,
      "law":"grow n->n+1 while reservoir (61-n)->(60-n) until protected progress",
      "anchor":[list(x) for x in ANCHOR],"tail":[list(x) for x in tail] if tail else None,
      "program":[list(x) for x in ANCHOR]+([list(x) for x in tail] if tail else []),
      "search":stats,"verification":v,"model_calls":0,"source_inspection":False,
      "status":"PROMOTED" if ok else "RESIDUAL"}
 (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_RECURRENCE_G2="+out["status"])
if __name__=="__main__":main()
