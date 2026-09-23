from __future__ import annotations

import json
import os
from collections import Counter, deque
from pathlib import Path

from PIL import Image
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-g3-visual-diagnostic-v1")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

PALETTE={
  0:(0,0,0),1:(0,116,217),2:(255,65,54),3:(46,204,64),4:(255,220,0),
  5:(170,170,170),6:(240,18,190),7:(255,133,27),8:(127,219,255),
  9:(135,12,37),10:(255,255,255),11:(128,0,128),12:(0,128,128),
  13:(128,128,0),14:(192,192,192),15:(255,255,255)
}

def grid(f):
    return g3.g3_grid(f) if hasattr(g3,"g3_grid") else g3.ab.grid(f)

def save(f,name):
    x=grid(f);h=len(x);w=len(x[0]);scale=8
    im=Image.new("RGB",(w*scale,h*scale))
    px=im.load()
    for r,row in enumerate(x):
        for c,v in enumerate(row):
            col=PALETTE.get(int(v),(255,255,255))
            for yy in range(r*scale,(r+1)*scale):
                for xx in range(c*scale,(c+1)*scale): px[xx,yy]=col
    im.save(OUT/f"{name}.png")

def comp_summary(f):
    xs=g3.ab.comps(f)
    out=[]
    for i,x in enumerate(xs):
        cells=x["cells"]
        rs=[r for r,c in cells];cs=[c for r,c in cells]
        if len(cells)<=200:
            out.append({
              "i":i,"color":x["color"],"size":len(cells),
              "bbox":[min(rs),min(cs),max(rs),max(cs)],
              "center":list(cells[len(cells)//2])
            })
    return out

def bars(f):
    left,right=g3.panel_groups(f)
    return {
      "left":[{"rc":list(x["rc"]),"color":x["color"]} for x in left],
      "right":[{"rc":list(x["rc"]),"color":x["color"]} for x in right]
    }

def snap(f,name,trace):
    save(f,name)
    trace.append({
      "name":name,
      "level":int(f.levels_completed),"state":str(f.state),
      "bars":bars(f),
      "components":comp_summary(f),
      "color_hist":dict(sorted(Counter(v for row in grid(f) for v in row).items()))
    })

def main():
    e=g3.make_g3();trace=[]
    snap(e.observation_space,"00_g3_start",trace)
    for i,(name,rc) in enumerate(g3.KNOWN,1):
        z=g3.ab.click(e,rc)
        snap(z,f"{i:02d}_after_{name}",trace)
    (OUT/"result.json").write_text(json.dumps({
      "status":"PASS","trace":trace,
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"black-box visual/component census on exact public tn36 G3 after qualified G1+G2; known A/B/C/D/E target probes only"
    },indent=2))
    print("ARC3_PUBLIC_G3_VISUAL_DIAGNOSTIC_V1=PASS")

if __name__=="__main__":main()
