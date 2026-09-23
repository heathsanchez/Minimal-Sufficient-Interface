from __future__ import annotations
import json, os
from collections import defaultdict
from pathlib import Path
from arcengine import GameState
import arc3_public_correspondence_compound_g3 as g3

OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-row-column-category-g3")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
A=g3.A; KNOWN=g3.KNOWN

def bit(x):
    if x["color"]==1:return 0
    if x["color"]==5:return 1
    raise ValueError(x)

def surface(f):
    left,right=g3.panel_groups(f); L=defaultdict(list);R=defaultdict(list)
    for x in left:L[x["rc"][0]].append(x)
    for x in right:R[x["rc"][0]].append(x)
    rows=sorted(L)
    if rows!=sorted(R) or len(rows)!=6:return None
    src=[]; tgt=[]; cols=None
    for r in rows:
        l=sorted(L[r],key=lambda x:x["rc"][1]); q=sorted(R[r],key=lambda x:x["rc"][1])
        if len(l)!=4 or len(q)!=6:return None
        vals=[bit(x) for x in l]
        if len(set(vals))!=1:return None
        src.append(vals[0]);tgt.append(q)
        cc=[x["rc"][1] for x in q]
        if cols is None:cols=cc
        elif cc!=cols:return None
    return rows,src,cols,tgt

def col_types(f,cols):
    grid=g3.ab.grid(f); tuples=[]; evidence=[]
    for j,c in enumerate(cols):
        a=33+4*j if j<3 else 49+4*(j-3); b=a+3
        y=sum(grid[r][cc]==4 for r in range(4,32) for cc in range(a,b+1))
        gr=sum(grid[r][cc]==5 for r in range(4,32) for cc in range(a,b+1))
        up=sum(grid[r][cc]==11 for r in range(4,18) for cc in range(a,b+1))
        dn=sum(grid[r][cc]==11 for r in range(18,32) for cc in range(a,b+1))
        phase=1 if y>gr else 0
        purple=1 if up>0 else (2 if dn>0 else 0)
        t=(phase,purple);tuples.append(t)
        evidence.append({"col":c,"phase":phase,"purple_state":purple,
                         "yellow":int(y),"gray":int(gr),"purple_top":int(up),"purple_bottom":int(dn)})
    cats=sorted(set(tuples))
    idx={t:i for i,t in enumerate(cats)}
    return [idx[t] for t in tuples],cats,evidence

def want(mask,rowbit,cat,kcats):
    return (mask >> (rowbit*kcats+cat)) & 1

def apply(mask,k):
    e=g3.make_g3();start=int(e.observation_space.levels_completed)
    for name,rc in KNOWN[:k]:
        z=g3.ab.click(e,rc)
        if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):
            return {"mask":mask,"prefix_len":k,"progressed":int(z.levels_completed)>start or z.state==GameState.WIN,"early":True}
    d=surface(e.observation_space)
    if d is None:return {"mask":mask,"prefix_len":k,"progressed":False,"reason":"surface"}
    rows,src,cols,tgt=d; cb,cats,ev=col_types(e.observation_space,cols);kc=len(cats)
    if kc>4: return {"mask":mask,"prefix_len":k,"progressed":False,"reason":"too_many_categories","categories":cats}
    writes=[]
    for i,row in enumerate(tgt):
      for j,t in enumerate(row):
        w=want(mask,src[i],cb[j],kc)
        if bit(t)!=w:
            z=g3.ab.click(e,tuple(t["rc"]));writes.append(list(t["rc"]))
            if int(z.levels_completed)>start or z.state in (GameState.WIN,GameState.GAME_OVER):break
      if int(e.observation_space.levels_completed)>start or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):break
    if int(e.observation_space.levels_completed)==start and e.observation_space.state==GameState.NOT_FINISHED:
        z=g3.ab.click(e,A)
    return {"mask":mask,"prefix_len":k,"source":src,"column_categories":cb,
            "category_defs":[list(x) for x in cats],"column_evidence":ev,"writes":writes,
            "progressed":int(e.observation_space.levels_completed)>start or e.observation_space.state==GameState.WIN,
            "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

def verify(mask,k):return [apply(mask,k),apply(mask,k)]

def main():
    probe=apply(0,0)
    kc=len(probe.get("category_defs",[]))
    assert kc==4, probe
    tested=[];selected=None;verification=[]
    for k in range(len(KNOWN)+1):
      for mask in range(1<<(2*kc)):
        r=apply(mask,k);tested.append(r)
        if r.get("progressed"):
            vv=verify(mask,k)
            if all(x.get("progressed") for x in vv):
                selected={"prefix_len":k,"prefix":[{"name":n,"rc":list(rc)} for n,rc in KNOWN[:k]],
                          "mask":mask,"source":r.get("source"),"column_categories":r.get("column_categories"),
                          "category_defs":r.get("category_defs"),"column_evidence":r.get("column_evidence")}
                verification=vv;break
      if selected:break
    out={"status":"PROMOTED" if selected else "RESIDUAL",
         "hypothesis":"G3 target cell depends only on generated row bit and the observed upper-right column type (checker phase x purple top/bottom/absent)",
         "category_count":kc,"candidate_family":f"all {1<<(2*kc)} binary tables on rowBit x columnType across A/B/C/D/E prefixes",
         "tested":tested,"selected":selected,"verification":verification,
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"exact public tn36 G3 after qualified G1/G2; four column types are derived from upper-right checker phase and purple occupancy; arbitrary binary output per (rowBit,columnType); terminal A; verify twice"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_ROW_COLUMN_CATEGORY_G3="+out["status"])
if __name__=="__main__":main()
