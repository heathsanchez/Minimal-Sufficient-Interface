from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any

from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME_ID = "tn36-ef4dde99"
ENVROOT = Path(os.environ["ENVROOT"]).resolve()
OUTDIR = Path(os.environ.get("OUTDIR", "evidence/arc3-public-generational-frontier-g2")).resolve()
OUTDIR.mkdir(parents=True, exist_ok=True)

G1 = [
    {"action":"MOUSE","row":55,"col":36},
    {"action":"MOUSE","row":14,"col":31},
    {"action":"MOUSE","row":42,"col":26},
    {"action":"MOUSE","row":42,"col":36},
    {"action":"MOUSE","row":42,"col":41},
    {"action":"MOUSE","row":45,"col":26},
    {"action":"MOUSE","row":45,"col":36},
    {"action":"MOUSE","row":45,"col":41},
    {"action":"MOUSE","row":55,"col":36},
]

MAX_DEPTH = 14
MAX_STATES = 350
MAX_TRANSITIONS = 24000
PER_STATE_CANDIDATES = 128


def visible_grid(frame: Any) -> list[list[int]]:
    raw = frame.frame
    if isinstance(raw, (list, tuple)):
        if not raw:
            return []
        raw = raw[-1]
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    return [[int(x) for x in row] for row in raw]


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def board_hash(frame: Any) -> str:
    import hashlib
    return hashlib.sha256(canon(visible_grid(frame)).encode()).hexdigest()


def histogram(frame: Any) -> tuple[tuple[int, int], ...]:
    g = visible_grid(frame)
    return tuple(sorted(Counter(x for row in g for x in row).items()))


def make_env():
    logger = logging.getLogger("tn36-g2-search")
    logger.setLevel(logging.WARNING)
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(ENVROOT), logger=logger)
    card = arcade.create_scorecard()
    env = arcade.make(GAME_ID, scorecard_id=card)
    if env is None:
        raise RuntimeError("public game unavailable offline")
    return arcade, env, card


def do_action(env: Any, action: dict[str, Any]):
    if action["action"] == "MOUSE":
        return env.step(
            GameAction.ACTION6,
            data={"x": int(action["col"]), "y": int(action["row"])},
        )
    return env.step(GameAction[action["action"]])


def full_reset(env: Any):
    f = env.reset()
    if f is None:
        raise RuntimeError("reset returned None")
    if int(f.levels_completed) != 0:
        raise RuntimeError(f"reset did not return to level 0: {f.levels_completed}")
    return f


def replay(env: Any, path: list[dict[str, Any]]) -> Any:
    full_reset(env)
    for action in G1:
        f = do_action(env, action)
        if f is None:
            raise RuntimeError("G1 replay returned None")
    if int(env.observation_space.levels_completed) != 1:
        raise RuntimeError("G1 no longer earns protected level-1 progress")
    for action in path:
        f = do_action(env, action)
        if f is None:
            raise RuntimeError("G2 path replay returned None")
        if int(f.levels_completed) > 1 or f.state in (GameState.WIN, GameState.GAME_OVER):
            break
    return env.observation_space


def components(grid: list[list[int]]) -> list[list[tuple[int, int]]]:
    if not grid:
        return []
    h, w = len(grid), len(grid[0])
    bg = Counter(x for row in grid for x in row).most_common(1)[0][0]
    seen: set[tuple[int, int]] = set()
    out: list[list[tuple[int, int]]] = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or grid[r][c] == bg:
                continue
            color = grid[r][c]
            q = deque([(r, c)])
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            while q:
                rr, cc = q.popleft()
                cells.append((rr, cc))
                for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr,nc) not in seen and grid[nr][nc] == color:
                        seen.add((nr,nc))
                        q.append((nr,nc))
            out.append(cells)
    return out


def candidate_actions(frame: Any, *, exhaustive: bool = False) -> list[dict[str, Any]]:
    g = visible_grid(frame)
    h = len(g); w = len(g[0]) if h else 0
    coords: list[tuple[int,int]] = []
    seen: set[tuple[int,int]] = set()

    def add(row: int, col: int) -> None:
        if 0 <= row < h and 0 <= col < w and (row,col) not in seen:
            seen.add((row,col))
            coords.append((row,col))

    # Keep previously useful coordinates and symmetries first.
    for a in G1:
        r,c=int(a["row"]),int(a["col"])
        for rr,cc in ((r,c),(r,w-1-c),(h-1-r,c),(h-1-r,w-1-c)):
            add(rr,cc)

    comps = components(g)
    comps.sort(key=lambda cells: (len(cells), min(r for r,_ in cells), min(c for _,c in cells)))
    for cells in comps:
        rs=[r for r,_ in cells]; cs=[c for _,c in cells]
        r0,r1,c0,c1=min(rs),max(rs),min(cs),max(cs)
        for r,c in (((r0+r1)//2,(c0+c1)//2),(r0,c0),(r0,c1),(r1,c0),(r1,c1)):
            add(r,c)
    foreground = [p for cells in comps for p in cells]
    if len(foreground) <= 768:
        for r,c in sorted(foreground):
            add(r,c)

    # Coarse lattice ensures background-sensitive controls are represented.
    for r in range(0,h,max(1,h//8)):
        for c in range(0,w,max(1,w//8)):
            add(r,c)

    if exhaustive:
        for r in range(h):
            for c in range(w):
                add(r,c)

    return [{"action":"MOUSE","row":r,"col":c} for r,c in coords]


def transition(env: Any, path: list[dict[str, Any]], action: dict[str, Any]) -> dict[str, Any]:
    before = replay(env, path)
    start_hash = board_hash(before)
    start_hist = histogram(before)
    f = do_action(env, action)
    if f is None:
        return {"valid":False}
    out = {
        "valid": True,
        "action": action,
        "state": str(f.state),
        "levels_completed": int(f.levels_completed),
        "progressed": int(f.levels_completed) > 1 or f.state == GameState.WIN,
        "game_over": f.state == GameState.GAME_OVER,
        "board_hash": board_hash(f),
        "histogram": histogram(f),
        "changed": board_hash(f) != start_hash,
        "hist_changed": histogram(f) != start_hist,
    }
    return out


def verify_path(path: list[dict[str, Any]], trials: int = 2) -> list[dict[str, Any]]:
    verified=[]
    for _ in range(trials):
        _, env, _ = make_env()
        f = replay(env, path)
        verified.append({
            "levels_completed": int(f.levels_completed),
            "state": str(f.state),
            "progressed": int(f.levels_completed) > 1 or f.state == GameState.WIN,
            "final_hash": board_hash(f),
        })
    return verified


def main() -> None:
    _, env, _ = make_env()
    root = replay(env, [])
    root_hash = board_hash(root)
    root_hist = histogram(root)

    # First generation at this residual: exhaustive one-step quotient.
    root_candidates = candidate_actions(root, exhaustive=True)
    one_step: dict[str, dict[str, Any]] = {}
    transitions = 0
    found_path: list[dict[str, Any]] | None = None
    for action in root_candidates:
        tr = transition(env, [], action)
        transitions += 1
        if not tr["valid"] or tr["game_over"]:
            continue
        if tr["progressed"]:
            found_path=[action]
            break
        if not tr["changed"]:
            continue
        one_step.setdefault(tr["board_hash"], {"path":[action],"transition":tr})

    quotient_stats = {
        "raw_root_actions": len(root_candidates),
        "distinct_changed_successors": len(one_step),
        "root_hash": root_hash,
        "root_histogram": root_hist,
    }

    seen={root_hash}
    q=deque()
    for h,rec in one_step.items():
        if h not in seen:
            seen.add(h); q.append(rec["path"])
            if len(seen)>=MAX_STATES:
                break

    explored_nodes=0
    depth_frontier=Counter()
    while found_path is None and q and len(seen) < MAX_STATES and transitions < MAX_TRANSITIONS:
        path=q.popleft()
        explored_nodes += 1
        depth=len(path)
        depth_frontier[depth]+=1
        if depth >= MAX_DEPTH:
            continue

        frame=replay(env,path)
        if int(frame.levels_completed)>1 or frame.state==GameState.WIN:
            found_path=path
            break
        if frame.state==GameState.GAME_OVER:
            continue

        actions=candidate_actions(frame, exhaustive=False)[:PER_STATE_CANDIDATES]
        for action in actions:
            if transitions >= MAX_TRANSITIONS or len(seen)>=MAX_STATES:
                break
            tr=transition(env,path,action)
            transitions += 1
            if not tr["valid"] or tr["game_over"]:
                continue
            newpath=path+[action]
            if tr["progressed"]:
                found_path=newpath
                break
            if not tr["changed"]:
                continue
            h=tr["board_hash"]
            if h in seen:
                continue
            seen.add(h)
            q.append(newpath)
        if found_path is not None:
            break

    verification = verify_path(found_path,2) if found_path is not None else []
    promoted = bool(found_path and all(v["progressed"] for v in verification))

    result = {
        "game": GAME_ID,
        "source_generation": {
            "branch":"arc3-public-generational-frontier-v1",
            "head":"15eeb1e66ce6bec83160c39df1a216ad970ebae8",
            "run":35854403385,
            "g1_program":G1,
        },
        "observer":"final visible 64x64 frame only",
        "source_inspection":False,
        "model_calls":0,
        "search":{
            "max_depth":MAX_DEPTH,
            "max_states":MAX_STATES,
            "max_transitions":MAX_TRANSITIONS,
            "per_state_candidates":PER_STATE_CANDIDATES,
            "transitions_tested":transitions,
            "states_seen":len(seen),
            "nodes_expanded":explored_nodes,
            "depth_frontier":dict(sorted(depth_frontier.items())),
            "root_quotient":quotient_stats,
        },
        "status":"PROMOTED" if promoted else "RESIDUAL",
        "g2_program":found_path,
        "g2_actions":len(found_path) if found_path else None,
        "verification":verification,
        "claim_boundary":"black-box local public-game residual search; no source inspection; generation-2 capability only",
    }
    (OUTDIR/"result.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    print("ARC3_PUBLIC_G2_SEARCH="+result["status"])


if __name__=="__main__":
    main()
