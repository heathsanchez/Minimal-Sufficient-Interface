from __future__ import annotations
import itertools, json, logging, os
from collections import deque
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-two-recolor-terminal-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC_STEPS=3

def env():
    l=logging.getLogger("two-recolor-terminal");l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard();e=a.make(GAME,scorecard_id=card)
    if e is None:raise RuntimeError("game")
    return e

def click(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def grid(f):
    x=f.frame
    if isinstance(x,(list,tuple)):x=x[-1]
    if hasattr(x,"tolist"):x=x.tolist()
    return [[int(v) for v in row] for row in x]

def label_components(f):
    g=grid(f);h,w=len(g),len(g[0]);lab={};cs=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in lab:continue
            z=g[r][c];idx=len(cs);q=deque([(r,c)]);lab[(r,c)]=idx;cells=[]
            while q:
                rr,cc=q.popleft();cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in lab and g[nr][nc]==z:
                        lab[(nr,nc)]=idx;q.append((nr,nc))
            cs.append({"color":z,"cells":cells,"size":len(cells)})
    return g,lab,cs

def enter_matched(e):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            f=click(e,rc)
            if f is None:raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    for rc in ANCHOR:
        f=click(e,rc)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("anchor drift")
    for _ in range(REC_STEPS):
        f=click(e,REC)
        if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("rec drift")
    return e.observation_space

def source_recolor_cells(f):
    g,lab,cs=label_components(f);h,w=len(g),len(g[0]);out=[]
    for i,comp in enumerate(cs):
        if comp["size"]!=3 or comp["color"]!=1:continue
        for r,c in comp["cells"]:
            unlike=[]
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w and lab[(nr,nc)]!=i:
                    j=lab[(nr,nc)]
                    unlike.append((dr,dc,cs[j]["size"],cs[j]["color"]))
            dirs=sorted((dr,dc) for dr,dc,_,_ in unlike)
            if len(unlike)==2 and all(color==0 for _,_,_,color in unlike):
                orientation=None
                if dirs==[(-1,0),(1,0)]:orientation="vertical-neighbors"
                elif dirs==[(0,-1),(0,1)]:orientation="horizontal-neighbors"
                if orientation:
                    out.append({"rc":(r,c),"component":i,"orientation":orientation,"neighbors":unlike})
    return out

def terminal_guard_cells(f):
    g,lab,cs=label_components(f);h,w=len(g),len(g[0]);out=[]
    for i,comp in enumerate(cs):
        if comp["size"]!=69 or comp["color"]!=9:continue
        for r,c in comp["cells"]:
            unlike=[]
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<h and 0<=nc<w and lab[(nr,nc)]!=i:
                    unlike.append((nr,nc))
            if not unlike:out.append((r,c))
    return out

def clicked_meta(f,rc):
    g,lab,cs=label_components(f);i=lab[tuple(rc)]
    return {"color":cs[i]["color"],"size":cs[i]["size"]}

def verify(program):
    outs=[]
    for _ in range(2):
        e=env();enter_matched(e)
        trace=[]
        for rc in program:
            z=click(e,tuple(rc))
            trace.append({"rc":list(rc),"level":int(z.levels_completed),"state":str(z.state),"meta":clicked_meta(z,tuple(rc))})
            if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
        outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                     "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace})
    return outs

def main():
    e=env();base=enter_matched(e)
    candidates=source_recolor_cells(base)
    single=[]
    good=[]
    for row in candidates:
        enter_matched(e);before=clicked_meta(e.observation_space,row["rc"]);z=click(e,row["rc"]);after=clicked_meta(z,row["rc"])
        rec={"rc":list(row["rc"]),"orientation":row["orientation"],"before":before,"after":after,
             "progressed":int(z.levels_completed)>1 or z.state==GameState.WIN,"state":str(z.state)}
        single.append(rec)
        if before=={"color":1,"size":3} and after=={"color":5,"size":3} and z.state!=GameState.GAME_OVER:
            good.append(tuple(row["rc"]))

    attempts=[]
    selected=None
    selected_ver=None
    # The residual is exactly six pixels, so require two distinct 3-cell recolors.
    for a,b in itertools.permutations(good,2):
        e2=env();enter_matched(e2)
        z1=click(e2,a)
        if z1.state==GameState.GAME_OVER:continue
        z2=click(e2,b)
        if z2.state==GameState.GAME_OVER:continue
        terminals=terminal_guard_cells(e2.observation_space)
        att={"recolors":[list(a),list(b)],"terminal_guard_cells":len(terminals),"first_terminal_cells":[list(x) for x in terminals[:10]]}
        attempts.append(att)
        for t in terminals:
            e3=env();enter_matched(e3);click(e3,a);click(e3,b);z=click(e3,t)
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
                program=[list(a),list(b),list(t)]
                ver=verify(program)
                if all(x["progressed"] for x in ver):
                    selected=program;selected_ver=ver;break
        if selected:break

    out={
        "matched_state":{"anchor_actions":len(ANCHOR),"recurrence_steps":REC_STEPS},
        "source_recolor_candidates":single,
        "successful_recolor_cells":[list(x) for x in good],
        "pair_attempts":attempts,
        "selected_program":selected,
        "verification":selected_ver or [],
        "status":"PROMOTED" if selected else "RESIDUAL",
        "model_calls":0,"source_inspection":False,
        "claim_boundary":"exact two-missing-3-cell recolor residual plus transported G1 terminal guard on public tn36 G2"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_TWO_RECOLOR_TERMINAL_G2="+out["status"])

if __name__=="__main__":main()
