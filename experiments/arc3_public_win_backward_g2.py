from __future__ import annotations
import hashlib, json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-win-backward-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
MAX_LEVEL_ACTIONS=60
MAX_SLACK=3

def env():
    l=logging.getLogger("win-backward");l.setLevel(logging.WARNING)
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

def bh(f):
    return hashlib.sha256(json.dumps(grid(f),separators=(",",":")).encode()).hexdigest()

def enter_prefix(e,slack,path=()):
    f=e.reset()
    if f is None:raise RuntimeError("reset")
    if int(f.levels_completed)==0:
      for rc in G1:click(e,rc)
    if int(e.observation_space.levels_completed)!=1:raise RuntimeError("g1 drift")
    for rc in ANCHOR:
      f=click(e,rc)
      if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):raise RuntimeError("anchor drift")
    rec_steps=(MAX_LEVEL_ACTIONS-slack)-len(ANCHOR)
    if rec_steps<0:raise RuntimeError("bad slack")
    for i in range(rec_steps):
      f=click(e,REC)
      if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
        raise RuntimeError(f"rec drift at {i+1}")
    for rc in path:
      f=click(e,rc)
      if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):break
    return e.observation_space

def out(f):
    return {"level":int(f.levels_completed),"state":str(f.state),"hash":bh(f),
            "progressed":int(f.levels_completed)>1 or f.state==GameState.WIN,
            "game_over":f.state==GameState.GAME_OVER}

def verify(slack,path):
    outs=[]
    for _ in range(2):
      e=env();enter_prefix(e,slack)
      trace=[]
      for rc in path:
        z=click(e,tuple(rc));trace.append({"rc":list(rc),**out(z)})
        if int(z.levels_completed)>1 or z.state in (GameState.WIN,GameState.GAME_OVER):break
      outs.append({"progressed":int(e.observation_space.levels_completed)>1 or e.observation_space.state==GameState.WIN,
                   "level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state),"trace":trace})
    return outs

def search_slack(slack):
    e=env()
    if slack==1:
      tested=0
      for r in range(64):
        for c in range(64):
          enter_prefix(e,slack);z=click(e,(r,c));tested+=1
          if int(z.levels_completed)>1 or z.state==GameState.WIN:
            p=[(r,c)];v=verify(slack,p)
            if all(x["progressed"] for x in v):
              return p,{"tested":tested,"states":1,"depth":1},v
      return None,{"tested":tested,"states":1,"depth":1},[]

    frontier=[()]
    seen={(bh(enter_prefix(e,slack)),0)}
    tested=0
    expanded=0
    per_depth={}
    for depth in range(slack):
      nxt={}
      for path in frontier:
        expanded+=1
        for r in range(64):
          for c in range(64):
            f=enter_prefix(e,slack,path)
            if int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):continue
            z=click(e,(r,c));tested+=1
            np=path+((r,c),)
            if int(z.levels_completed)>1 or z.state==GameState.WIN:
              v=verify(slack,np)
              if all(x["progressed"] for x in v):
                return list(np),{"tested":tested,"states":len(seen),"expanded":expanded,"depth":depth+1,"per_depth":per_depth},v
            if z.state==GameState.GAME_OVER:continue
            key=(bh(z),depth+1)
            if key not in seen:
              seen.add(key);nxt[key]=np
      per_depth[str(depth+1)]={"frontier":len(frontier),"new_states":len(nxt)}
      frontier=list(nxt.values())
      if not frontier:break
    return None,{"tested":tested,"states":len(seen),"expanded":expanded,"depth":slack,"per_depth":per_depth},[]

def main():
    attempts=[]
    selected=None;selected_slack=None;verification=[]
    for slack in range(1,MAX_SLACK+1):
      p,stats,v=search_slack(slack)
      attempts.append({"slack":slack,"prefix_actions":MAX_LEVEL_ACTIONS-slack,"stats":stats,"program":[list(x) for x in p] if p else None})
      if p:
        selected=[list(x) for x in p];selected_slack=slack;verification=v;break
    out={
      "goal":"protected level progress before the 60-action boundary",
      "method":"backward slack expansion from WIN boundary with exact visible-successor quotient",
      "max_level_actions":MAX_LEVEL_ACTIONS,
      "max_slack":MAX_SLACK,
      "attempts":attempts,
      "selected_slack":selected_slack,
      "selected_suffix":selected,
      "verification":verification,
      "status":"PROMOTED" if selected else "RESIDUAL",
      "model_calls":0,"source_inspection":False,
      "claim_boundary":"exact public tn36 G2 mouse-action suffixes within last 3 actions before budget"
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_WIN_BACKWARD_G2="+out["status"])

if __name__=="__main__":main()
