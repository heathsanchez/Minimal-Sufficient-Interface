from __future__ import annotations
import json, logging, os
from collections import Counter, deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-residual-alignment-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
TARGET_ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC3=3
MAX_GEN=4

def env():
    l=logging.getLogger("residual-alignment");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)): x=x[-1]
    if hasattr(x,"tolist"): x=x.tolist()
    return [[int(v) for v in row] for row in x]

def features(f):
    g=grid(f);h=len(g);w=len(g[0])
    seen=set(); sizes=Counter(); colors=Counter(v for row in g for v in row)
    for r in range(h):
        for c in range(w):
            if (r,c) in seen: continue
            z=g[r][c];q=deque([(r,c)]);seen.add((r,c));n=0
            while q:
                rr,cc=q.popleft();n+=1
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==z:
                        seen.add((nr,nc));q.append((nr,nc))
            sizes[n]+=1
    rt=sum(1 for row in g for a,b in zip(row,row[1:]) if a!=b)
    ct=sum(1 for r in range(h-1) for c in range(w) if g[r][c]!=g[r+1][c])
    return {"sizes":dict(sizes),"colors":dict(colors),"rt":rt,"ct":ct}

def diff(a,b):
    def dm(x,y):
        return {str(k):int(y.get(k,0)-x.get(k,0)) for k in set(x)|set(y) if y.get(k,0)!=x.get(k,0)}
    return {"sizes":dm(a["sizes"],b["sizes"]),"colors":dm(a["colors"],b["colors"]),
            "rt":b["rt"]-a["rt"],"ct":b["ct"]-a["ct"]}

def sub(a,b):
    def sm(x,y):
        keys=set(x)|set(y);return {str(k):int(x.get(k,0)-y.get(k,0)) for k in keys if x.get(k,0)-y.get(k,0)!=0}
    return {"sizes":sm(a["sizes"],b["sizes"]),"colors":sm(a["colors"],b["colors"]),
            "rt":a["rt"]-b["rt"],"ct":a["ct"]-b["ct"]}

def dist(x):
    return 25*sum(abs(v) for v in x["sizes"].values()) + 2*sum(abs(v) for v in x["colors"].values()) + abs(x["rt"])+abs(x["ct"])

def key(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"))

def source_net():
    e=env();a=features(e.observation_space)
    for rc in G1[:-1]:
        f=click(e,rc)
        if int(f.levels_completed)>0: raise RuntimeError("source progressed before terminal")
    b=features(e.observation_space)
    return diff(a,b)

def enter_target(e,chosen=()):
    f=e.reset()
    if f is None: raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1: click(e,rc)
    if int(e.observation_space.levels_completed)!=1: raise RuntimeError("g1")
    start=features(e.observation_space)
    for rc in TARGET_ANCHOR: click(e,rc)
    for _ in range(REC3): click(e,REC)
    for rc in chosen:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return start,e.observation_space

def target_net(e,chosen=()):
    a,f=enter_target(e,chosen)
    return diff(a,features(f)),f

def enumerate_effects(e,chosen,residual):
    classes={}
    best_progress=None
    for r in range(64):
        for c in range(64):
            _,f=enter_target(e,chosen)
            if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
                continue
            before=features(f);z=click(e,(r,c))
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                best_progress=(r,c); return classes,best_progress
            if z.state==GameState.GAME_OVER: continue
            ed=diff(before,features(z));k=key(ed)
            if k in classes: continue
            rem=sub(residual,ed)
            classes[k]={"rc":[r,c],"effect":ed,"remaining":rem,"distance":dist(rem)}
    return classes,best_progress

def verify(program):
    out=[]
    for _ in range(2):
        e=env();_,f=enter_target(e,program)
        out.append({"level":int(f.levels_completed),"state":str(f.state),
                    "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN})
    return out

def main():
    src=source_net(); e=env(); tgt,_=target_net(e,())
    residual=sub(src,tgt); initial_distance=dist(residual)
    chosen=[];trace=[];progress=None
    for generation in range(MAX_GEN):
        classes,p=enumerate_effects(e,tuple(chosen),residual)
        if p is not None:
            chosen.append(list(p));progress=p
            trace.append({"generation":generation,"direct_progress":list(p),"classes_examined":len(classes)})
            break
        if not classes:
            trace.append({"generation":generation,"reason":"no-live-effect-classes"});break
        ranked=sorted(classes.values(),key=lambda z:(z["distance"],z["rc"]))
        best=ranked[0]
        trace.append({"generation":generation,"classes":len(classes),"before_distance":dist(residual),
                      "selected":best["rc"],"after_distance":best["distance"],"effect":best["effect"]})
        if best["distance"]>=dist(residual):
            trace[-1]["reason"]="no-residual-improvement"
            break
        chosen.append(best["rc"]);residual=best["remaining"]
    ver=verify(chosen) if chosen else []
    ok=bool(ver and all(x["progressed"] for x in ver))
    out={"source_net":src,"target_net_before_repair":tgt,"initial_residual":sub(src,tgt),
         "initial_distance":initial_distance,"repair_program":chosen,"trace":trace,
         "verification":ver,"status":"PROMOTED" if ok else "RESIDUAL",
         "model_calls":0,"source_inspection":False,
         "claim_boundary":"source-vs-target cumulative consequence alignment at G2 (8,53) state"}
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_RESIDUAL_ALIGNMENT_G2="+out["status"])
if __name__=="__main__":main()
