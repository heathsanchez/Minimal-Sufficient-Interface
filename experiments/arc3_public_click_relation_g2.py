from __future__ import annotations
import json,logging,os
from collections import deque
from pathlib import Path
from arc_agi import Arcade,OperationMode
from arcengine import GameAction

GAME="tn36-ef4dde99";ENVROOT=Path(os.environ["ENVROOT"]).resolve();OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-click-relation-g2")).resolve();OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
P=[(58,46),(58,11),(58,20),(58,22),(55,20)]
def env():
 l=logging.getLogger("rel");l.setLevel(logging.WARNING);a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l);c=a.create_scorecard();e=a.make(GAME,scorecard_id=c)
 if e is None:raise RuntimeError("game")
 return e
def click(e,rc):r,c=rc;return e.step(GameAction.ACTION6,data={"x":c,"y":r})
def grid(f):
 x=f.frame
 if isinstance(x,(list,tuple)):x=x[-1]
 if hasattr(x,"tolist"):x=x.tolist()
 return [[int(v) for v in row] for row in x]
def labels(g):
 h,w=len(g),len(g[0]); lab={}; comps=[]
 for r in range(h):
  for c in range(w):
   if (r,c) in lab:continue
   z=g[r][c];idx=len(comps);q=deque([(r,c)]);lab[(r,c)]=idx;cells=[]
   while q:
    rr,cc=q.popleft();cells.append((rr,cc))
    for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
     nr,nc=rr+dr,cc+dc
     if 0<=nr<h and 0<=nc<w and (nr,nc) not in lab and g[nr][nc]==z:
      lab[(nr,nc)]=idx;q.append((nr,nc))
   comps.append({"color":z,"cells":cells,"size":len(cells)})
 return lab,comps
def relation(f,rc):
 g=grid(f);lab,cs=labels(g);r,c=rc;i=lab[(r,c)];neigh=[]
 for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
  p=(r+dr,c+dc)
  if p in lab and lab[p]!=i:
   j=lab[p];neigh.append({"dr":dr,"dc":dc,"size":cs[j]["size"],"color":cs[j]["color"]})
 return {"rc":list(rc),"clicked_size":cs[i]["size"],"clicked_color":cs[i]["color"],"neighbors":neigh}
def main():
 e=env()
 for x in G1:click(e,x)
 rows=[]
 for j,rc in enumerate(P):
  before=relation(e.observation_space,rc);f=click(e,rc);after=relation(f,rc)
  rows.append({"j":j,"before":before,"after":after})
 out={"rows":rows};(OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print("ARC3_PUBLIC_CLICK_RELATION_G2=PASS")
if __name__=="__main__":main()
