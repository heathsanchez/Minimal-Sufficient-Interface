from __future__ import annotations
import json, os
from collections import defaultdict
from pathlib import Path
from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-observed-column-feature-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
A=g3.A; KNOWN=g3.KNOWN

def truth(mask,a,b): return (mask >> ((a<<1)|b)) & 1
def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)

def data(f):
    left,right=g3.panel_groups(f);L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(L)
    if rows!=sorted(R) or len(rows)!=6:return None
    src=[];tgt=[];cols=None
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1]);q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:return None
        v=[bit(x) for x in l]
        if len(set(v))!=1:return None
        src.append(v[0]);tgt.append(q)
        cc=[x["rc"][1] for x in q]
        cols=cc if cols is None else cols
        if cc!=cols:return None
    return rows,src,cols,tgt

def column_features(f,cols):
    grid=g3.ab.grid(f)
    feats={"checker_phase":[],"upper_purple":[],"lower_purple":[],"any_purple":[]}
    for j,c in enumerate(cols):
        # target columns are 5 apart; use the observed 4-wide upper-field cell containing c
        a=c-1 if c%5==4 else c-2
        # robustly center a 4-wide block around the target column without crossing the central gap
        if j<3: a=33+4*j
        else: a=49+4*(j-3)
        b=a+3
        y=sum(1 for r in range(4,32) for cc in range(a,b+1) if grid[r][cc]==4)
        gr=sum(1 for r in range(4,32) for cc in range(a,b+1) if grid[r][cc]==5)
        up=sum(1 for r in range(4,18) for cc in range(a,b+1) if grid[r][cc]==11)
        dn=sum(1 for r in range(18,32) for cc in range(a,b+1) if grid[r][cc]==11)
        feats["checker_phase"].append(1 if y>gr else 0)
        feats["upper_purple"].append(1 if up>0 else 0)
        feats["lower_purple"].append(1 if dn>0 else 0)
        feats["any_purple"].append(1 if up+dn>0 else 0)
    return feats

def apply(feature,mask,k):
    e=g3.make_g3();start=int(e.observation_space.levels_completed);trace=[]
    for name,rc in KNOWN[:k]:
        z=g3.ab.click(e,rc)
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"feature":feature,"mask":mask,"prefix_len":k,"progressed":int(z.levels_completed)>start or z.state==GameState.WIN}
    d=data(e.observation_space)
    if d is None:return {"feature":feature,"mask":mask,"prefix_len":k,"progressed":False,"reason":"surface"}
    rows,src,cols,tgt=d; feats=column_features(e.observation_space,cols); cb=feats[feature]
    writes=[]
    for i,row in enumerate(tgt):
        for j,t in enumerate(row):
            want=truth(mask,src[i],cb[j])
            if bit(t)!=want:
                z=g3.ab.click(e,tuple(t["rc"]));writes.append(list(t["rc"]))
                if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):break
        if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):break
    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
    return {"feature":feature,"feature_bits":cb,"all_features":feats,"mask":mask,
            "truth":[truth(mask,a,b) for a,b in ((0,0),(0,1),(1,0),(1,1))],
            "prefix_len":k,"source":src,"writes":writes,
            "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
            "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

def verify(feature,mask,k): return [apply(feature,mask,k),apply(feature,mask,k)]

def main():
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
      for feature in ("checker_phase","upper_purple","lower_purple","any_purple"):
       for mask in range(16):
        r=apply(feature,mask,k);tested.append(r)
        if r.get("progressed"):
            vv=verify(feature,mask,k)
            if all(x.get("progressed") for x in vv):
                selected={"prefix_len":k,"feature":feature,"feature_bits":r.get("feature_bits"),
                          "mask":mask,"truth":r.get("truth"),"source":r.get("source")}
                verification=vv;break
       if selected:break
      if selected:break
    out={"status":"PROMOTED" if selected else "RESIDUAL",
         "hypothesis":"G3 target is a relation between generated row bits and one directly observed binary column predicate from the upper-right field",
         "features":["checker_phase","upper_purple","lower_purple","any_purple"],
         "tested":tested,"selected":selected,"verification":verification,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"exact public tn36 G3 after qualified G1/G2; four column predicates are derived only from observed upper-right yellow/gray phase and purple occupancy; all 16 binary functions; A/B/C/D/E prefixes; terminal A; verify twice"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_OBSERVED_COLUMN_FEATURE_G3="+out["status"])
if __name__=="__main__":main()
