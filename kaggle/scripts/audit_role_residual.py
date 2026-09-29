"""Trace the causal role sequence of a no-trace ACTION6 public run.

Diagnostic only. It records the already-qualified role-grounding proposal
sequence and the observed consequence of each click; no role ranking is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"kaggle/src"))
sys.path.insert(0,str(ROOT/"kaggle/vendor/ARC-AGI-3-Agents"))

from arc_agi import Arcade, OperationMode
from arcengine import GameAction
from metalogic_arc3.residual_exploration import ResidualController
from metalogic_arc3.runtime import OnlineController, normalize_frame


def plain(value):
    if hasattr(value,"tolist"):
        return value.tolist()
    if isinstance(value,list):
        return [plain(v) for v in value]
    return value


def board_of(frame):
    raw=plain(getattr(frame,"frame",frame.get("frame",[]) if isinstance(frame,dict) else []))
    return raw[0] if raw else []


def component_role(board,x,y):
    if not board or not (0<=y<len(board) and 0<=x<len(board[0])):
        return None
    color=board[y][x]
    q=[(x,y)]; seen={(x,y)}; pts=[]
    while q:
        px,py=q.pop();pts.append((px,py))
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            qx,qy=px+dx,py+dy
            if not (0<=qy<len(board) and 0<=qx<len(board[0])): continue
            if (qx,qy) in seen or board[qy][qx]!=color: continue
            seen.add((qx,qy));q.append((qx,qy))
    xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys)
    patch=OnlineController._canonical_local_patch(board,x,y,radius=1)
    payload=(maxy-miny+1,maxx-minx+1,len(pts),patch)
    role_id=hashlib.sha256(
        json.dumps(payload,separators=(",",":"),sort_keys=True).encode()
    ).hexdigest()[:16]
    return {
        "role_id":role_id,
        "height":maxy-miny+1,
        "width":maxx-minx+1,
        "size":len(pts),
        "color":color,
        "patch":patch,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--environments",type=Path,required=True)
    ap.add_argument("--game",default="lp85-305b61c3")
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--budget",type=int,default=100)
    args=ap.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)

    ids=tuple(int(a.value) for a in GameAction if a is not GameAction.RESET)
    ctl=ResidualController(
        ids,role_grounding=True,archived_capabilities=(),trace_capabilities=())
    arc=Arcade(operation_mode=OperationMode.OFFLINE,
               environments_dir=str(args.environments.resolve()))
    env=arc.make(args.game)
    if env is None: raise SystemExit("missing environment")
    current=env.observation_space
    start_level=int(current.levels_completed)
    rows=[]
    resets=1

    for step in range(args.budget):
        before=normalize_frame(current)
        if before.state=="WIN" or before.levels_completed>start_level:
            break
        if before.state in ("GAME_OVER","NOT_PLAYED"):
            ctl.observe_terminal(current)
            if before.state=="GAME_OVER":
                ctl.record_terminal_failure("GAME_OVER")
            ctl.reset_episode()
            current=env.step(GameAction.RESET)
            resets+=1
            continue

        board=board_of(current)
        token=ctl.observe_and_choose(current)
        if token is None: break
        role_coords=tuple(getattr(ctl,"_role_grounding_coordinates",()))
        rank=(role_coords.index((token.x,token.y))+1
              if token.action_id==6 and (token.x,token.y) in role_coords else None)
        role=(component_role(board,token.x,token.y)
              if token.action_id==6 and token.x is not None and token.y is not None else None)

        action=GameAction.from_id(token.action_id)
        data={"x":token.x,"y":token.y} if token.action_id==6 else {}
        nxt=env.step(action,data=data)
        if nxt is None: raise RuntimeError("no observation")
        after=normalize_frame(nxt)
        row={
            "step":step+1,
            "source":token.source,
            "action_id":token.action_id,
            "x":token.x,"y":token.y,
            "role_rank":rank,
            "role_count":len(role_coords),
            "role":role,
            "board_changed":after.board_digest!=before.board_digest,
            "frame_changed":after.frame_digest!=before.frame_digest,
            "progress":after.levels_completed>before.levels_completed or after.state=="WIN",
            "before_level":before.levels_completed,
            "after_level":after.levels_completed,
            "after_state":after.state,
        }
        rows.append(row)
        print(json.dumps(row,sort_keys=True),flush=True)
        current=nxt

    result={
        "schema":"arc3.role-residual-audit@1",
        "game":args.game,
        "start_level":start_level,
        "final_level":int(current.levels_completed),
        "resets":resets,
        "actions":len(rows),
        "progress":int(current.levels_completed)>start_level,
        "rows":rows,
        "changed_clicks":sum(bool(r["board_changed"]) for r in rows),
        "role_clicks":sum(r["role_rank"] is not None for r in rows),
    }
    if result["progress"]:
        winner=next(r for r in rows if r["progress"])
        result["progress_role"]=winner["role"]
        result["progress_role_rank"]=winner["role_rank"]
        result["progress_step"]=winner["step"]
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},sort_keys=True))
    arc.close_scorecard()


if __name__=="__main__":
    main()
