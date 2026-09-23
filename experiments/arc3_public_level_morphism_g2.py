from __future__ import annotations
import json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-level-morphism-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]

def env():
    l=logging.getLogger("morphism");l.setLevel(logging.WARNING)
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
        rs=[x for x,_ in cells];cs=[y for _,y in cells]
        out.append({"color":z,"size":len(cells),"h":max(rs)-min(rs)+1,"w":max(cs)-min(cs)+1,
                    "bbox":[min(rs),min(cs),max(rs),max(cs)]})
    return out
def signature(f):
    cs=components(f)
    return {
      "shape_counts":{str(k):v for k,v in sorted(Counter((x["color"],x["h"],x["w"],x["size"]) for x in cs).items(),key=lambda kv:str(kv[0]))},
      "color_size_counts":{str(k):v for k,v in sorted(Counter((x["color"],x["size"]) for x in cs).items(),key=lambda kv:str(kv[0]))},
      "small_components":sorted([x for x in cs if x["size"]<=100],key=lambda x:(x["color"],x["size"],x["bbox"])),
    }
def main():
    e=env()
    l1_initial=signature(e.observation_space)
    for rc in G1[:-1]:click(e,rc)
    l1_preterminal=signature(e.observation_space)
    z=click(e,G1[-1])
    if int(z.levels_completed)!=1:raise RuntimeError("G1 no longer progresses")
    l2_initial=signature(z)
    out={"l1_initial":l1_initial,"l1_preterminal":l1_preterminal,"l2_initial":l2_initial,
         "model_calls":0,"source_inspection":False}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_LEVEL_MORPHISM_G2=PASS")
if __name__=="__main__":main()
