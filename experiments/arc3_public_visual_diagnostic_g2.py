from __future__ import annotations
import logging, os
from pathlib import Path
from PIL import Image
from arc_agi import Arcade, OperationMode
from arcengine import GameAction

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-visual-diagnostic-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
A=(58,46);B=(58,11);C=(58,20);D=(58,22);E=(55,20);REC=(2,20)
SCHEMA=[(32,37),(32,42),(32,47),(35,37),(35,42),(35,47)]

PALETTE={
  0:(0,0,0),1:(0,116,217),2:(255,65,54),3:(46,204,64),4:(255,220,0),
  5:(170,170,170),6:(240,18,190),7:(255,133,27),8:(127,219,255),9:(135,12,37),
  10:(255,255,255),11:(128,0,128),12:(0,128,128),13:(128,128,0),14:(192,192,192),15:(255,255,255),
}

def env():
    l=logging.getLogger("visual");l.setLevel(logging.WARNING)
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

def save(f,name):
    g=grid(f);h=len(g);w=len(g[0])
    scale=8
    im=Image.new("RGB",(w*scale,h*scale))
    px=im.load()
    for r,row in enumerate(g):
      for c,v in enumerate(row):
        color=PALETTE.get(int(v),(255,255,255))
        for y in range(r*scale,(r+1)*scale):
          for x in range(c*scale,(c+1)*scale):
            px[x,y]=color
    im.save(OUT/f"{name}.png")

def main():
    e=env();save(e.observation_space,"00_level1_start")
    for i,rc in enumerate(G1,1):
      f=click(e,rc);save(f,f"g1_{i:02d}")
    save(e.observation_space,"10_level2_start")
    for name,rc in [("11_after_A",A),("12_after_B",B),("13_after_C_bundle",C),("14_after_D",D),("15_after_E",E)]:
      f=click(e,rc);save(f,name)

    # independent schema branch
    e2=env()
    for rc in G1:click(e2,rc)
    click(e2,A);click(e2,B)
    save(e2.observation_space,"20_schema_start")
    for i,rc in enumerate(SCHEMA,1):
      f=click(e2,rc);save(f,f"schema_{i:02d}")

    # near-budget recurrence branch
    e3=env()
    for rc in G1:click(e3,rc)
    for rc in [A,B,C,D,E]:click(e3,rc)
    for i in range(54):
      f=click(e3,REC)
      if i in (0,4,9,19,29,39,49,53):
        save(f,f"rec_{i+1:02d}")
    save(e3.observation_space,"90_action59_state")
    print("ARC3_PUBLIC_VISUAL_DIAGNOSTIC_G2=PASS")

if __name__=="__main__":main()
