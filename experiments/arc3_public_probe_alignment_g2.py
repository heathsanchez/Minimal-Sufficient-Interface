from __future__ import annotations
import json,logging,os
from collections import Counter,deque
from pathlib import Path
from arc_agi import Arcade,OperationMode
from arcengine import GameAction

GAME="tn36-ef4dde99"; ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-probe-alignment-g2")).resolve();OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
PROBES=[(58,46),(58,11),(58,20),(58,22),(55,20)]

def env():
 l=logging.getLogger("align");l.setLevel(logging.WARNING)
 a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l); card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
 if e is None:raise RuntimeError("game")
 return e

def click(e,rc):
 r,c=rc;return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
 x=f.frame
 if isinstance(x,(list,tuple)):x=x[-1]
 if hasattr(x,"tolist"):x=x.tolist()
 return [[int(v) for v in row] for row in x]

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

def summ(f):
 g=grid(f);h=len(g);w=len(g[0]);total=h*w
 ar=Counter(len(c) for c in comps(g) if len(c)<=max(16,total//4));hist=Counter(v for row in g for v in row)
 rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
 ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
 return {"cc":sum(ar.values()),"ar":dict(ar),"hi":dict(hist),"rt":rt,"ct":ct}

def dm(a,b):return {str(k):b.get(k,0)-a.get(k,0) for k in set(a)|set(b) if b.get(k,0)!=a.get(k,0)}
def sig(a,b):
 hd=dm(a["hi"],b["hi"]);return {"dcc":b["cc"]-a["cc"],"da":dm(a["ar"],b["ar"]),"hu":sorted(hd.values()),"dr":b["rt"]-a["rt"],"dc":b["ct"]-a["ct"]}
def dist(a,b):
 d=20*abs(a["dcc"]-b["dcc"])+25*sum(abs(a["da"].get(k,0)-b["da"].get(k,0)) for k in set(a["da"])|set(b["da"]))
 x=list(a["hu"]);y=list(b["hu"]);n=max(len(x),len(y));x += [0]*(n-len(x));y += [0]*(n-len(y))
 return d+2*sum(abs(p-q) for p,q in zip(sorted(x),sorted(y)))+abs(a["dr"]-b["dr"])+abs(a["dc"]-b["dc"])

def main():
 e=env();s=[];a=summ(e.observation_space)
 for i,rc in enumerate(G1):
  f=click(e,rc);b=summ(f);s.append({"i":i,"rc":list(rc),"sig":sig(a,b)});a=b
 if int(e.observation_space.levels_completed)!=1:raise RuntimeError("G1")
 t=[];a=summ(e.observation_space)
 for j,rc in enumerate(PROBES):
  f=click(e,rc);b=summ(f);sg=sig(a,b)
  ranking=sorted((dist(x["sig"],sg),x["i"]) for x in s)
  t.append({"j":j,"rc":list(rc),"sig":sg,"best_source":ranking[:5]});a=b
 out={"source":s,"target_probes":t,"model_calls":0,"source_inspection":False}
 (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_PROBE_ALIGNMENT_G2=PASS")
if __name__=="__main__":main()
