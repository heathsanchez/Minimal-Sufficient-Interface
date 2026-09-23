from __future__ import annotations

import json
import os
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any

MSI_ROOT = Path(os.environ["MSI_ROOT"]).resolve()
ENVROOT = Path(os.environ["ENVROOT"]).resolve()
METATRON_ROOT = Path(os.environ["METATRON_ROOT"]).resolve()
OUTDIR = Path(os.environ.get("OUTDIR", MSI_ROOT / "evidence" / "arc3-residual-generated-capability-v2"))
OUTDIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MSI_ROOT / "experiments"))
sys.path.insert(0, str(METATRON_ROOT))

from arc3_certified_capability_slice_v1 import (  # noqa: E402
    WITNESS as BASE_WITNESS,
    canon,
    features,
    grid_of,
    grid_hash,
    make_env,
)
from arcengine import GameAction, GameState  # noqa: E402
from runtime.metatron.nucleus import Node, append, dumps, live_ids  # noqa: E402

MAX_REPEAT = 32
GRID_W = 64
GRID_H = 64


def hist_key(frame: Any) -> str:
    return canon(features(frame)["color_histogram"])


def execute_click(env: Any, coord: tuple[int, int], max_steps: int) -> dict[str, Any]:
    start = int(env.observation_space.levels_completed)
    used = 0
    changed = 0
    before_hash = grid_hash(env.observation_space)
    prev_hash = before_hash
    trace: list[dict[str, Any]] = []
    progressed = False
    won = False
    for _ in range(max_steps):
        f = env.step(GameAction.ACTION6, data={"x": coord[0], "y": coord[1]})
        used += 1
        if f is None:
            break
        h = grid_hash(f)
        changed += int(h != prev_hash)
        prev_hash = h
        now = int(f.levels_completed)
        trace.append({"action": used, "levels_completed": now, "state": str(f.state), "grid_hash": h})
        if now > start or f.state == GameState.WIN:
            progressed = True
            won = f.state == GameState.WIN
            break
        if f.state == GameState.GAME_OVER:
            break
    return {
        "coord": list(coord),
        "start_level": start,
        "actions": used,
        "progressed": progressed,
        "won": won,
        "board_changed_steps": changed,
        "start_hash": before_hash,
        "end_hash": grid_hash(env.observation_space),
        "end_state": str(env.observation_space.state),
        "end_level": int(env.observation_space.levels_completed),
        "trace": trace,
    }


def replay_atlas(atlas: dict[str, dict[str, Any]]) -> tuple[Any, Any, Any, list[dict[str, Any]]]:
    arcade, env, card = make_env(ENVROOT)
    replay_trace: list[dict[str, Any]] = []
    seen = 0
    while env.observation_space.state not in (GameState.WIN, GameState.GAME_OVER):
        key = hist_key(env.observation_space)
        cap = atlas.get(key)
        if cap is None:
            break
        res = execute_click(env, tuple(cap["coord"]), int(cap["max_steps"]))
        replay_trace.append({"guard": key, "capability": cap, "result": res})
        if not res["progressed"]:
            raise AssertionError(f"warranted capability failed during replay at level {res['start_level']}")
        seen += 1
        if seen > 16:
            raise AssertionError("atlas replay failed to terminate")
    return arcade, env, card, replay_trace


def connected_components(grid: list[list[int]]) -> list[list[tuple[int, int]]]:
    if not grid:
        return []
    h, w = len(grid), len(grid[0])
    flat = [x for row in grid for x in row]
    bg = Counter(flat).most_common(1)[0][0]
    seen: set[tuple[int, int]] = set()
    comps: list[list[tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] == bg or (x, y) in seen:
                continue
            color = grid[y][x]
            q = deque([(x, y)])
            seen.add((x, y))
            cells: list[tuple[int, int]] = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and grid[ny][nx] == color:
                        seen.add((nx, ny))
                        q.append((nx, ny))
            comps.append(cells)
    return comps


def candidate_order(frame: Any) -> list[tuple[int, int]]:
    grid = grid_of(frame)
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    def add(p: tuple[int, int]) -> None:
        x, y = p
        if 0 <= x < w and 0 <= y < h and p not in seen:
            seen.add(p)
            out.append(p)

    # Previously warranted witness and its obvious representation symmetries.
    bx, by = BASE_WITNESS
    for p in (
        (bx, by), (w - 1 - bx, by), (bx, h - 1 - by), (w - 1 - bx, h - 1 - by),
        (w // 2, h // 2), (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
    ):
        add(p)

    # Visible residual structure: centers, corners, then all cells of each foreground component.
    comps = connected_components(grid)
    comps.sort(key=lambda c: (len(c), min(y for _, y in c), min(x for x, _ in c)))
    for cells in comps:
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        for p in (
            ((x0 + x1) // 2, (y0 + y1) // 2),
            (x0, y0), (x1, y0), (x0, y1), (x1, y1),
        ):
            add(p)
    for cells in comps:
        for p in sorted(cells, key=lambda q: (q[1], q[0])):
            add(p)

    # Complete declared intervention language fallback: every visible coordinate.
    for y in range(h):
        for x in range(w):
            add((x, y))
    return out


def trial_candidate(atlas: dict[str, dict[str, Any]], coord: tuple[int, int]) -> dict[str, Any]:
    _, env, _, prefix_trace = replay_atlas(atlas)
    if env.observation_space.state in (GameState.WIN, GameState.GAME_OVER):
        return {
            "coord": list(coord),
            "prefix_terminal": str(env.observation_space.state),
            "progressed": False,
            "prefix_trace": prefix_trace,
        }
    res = execute_click(env, coord, MAX_REPEAT)
    res["prefix_trace_len"] = len(prefix_trace)
    return res


def independent_verify(atlas: dict[str, dict[str, Any]], coord: tuple[int, int]) -> tuple[dict[str, Any], dict[str, Any]]:
    a = trial_candidate(atlas, coord)
    b = trial_candidate(atlas, coord)
    if not (a.get("progressed") and b.get("progressed")):
        raise AssertionError("candidate did not independently requalify twice")
    return a, b


def discover(atlas: dict[str, dict[str, Any]], log) -> tuple[dict[str, dict[str, Any]], Any, dict[str, Any]]:
    _, residual_env, _, prefix = replay_atlas(atlas)
    frame = residual_env.observation_space
    if frame.state == GameState.WIN:
        return atlas, log, {"status": "WIN_ALREADY", "prefix": prefix}
    if frame.state == GameState.GAME_OVER:
        return atlas, log, {"status": "GAME_OVER_BEFORE_DISCOVERY", "prefix": prefix}

    key = hist_key(frame)
    level = int(frame.levels_completed)
    residual = Node(
        "residual",
        {
            "domain": "ARC3/bt33",
            "level": level,
            "guard": "color_histogram",
            "signature": key,
            "reason": "no live capability for observed quotient state",
            "intervention_language": "ACTION6(x,y), 0<=x,y<64, repeated <=32",
        },
    )
    log = append(log, residual)

    candidates = candidate_order(frame)
    tested: list[dict[str, Any]] = []
    first_success: dict[str, Any] | None = None
    first_failure: dict[str, Any] | None = None
    for idx, coord in enumerate(candidates):
        res = trial_candidate(atlas, coord)
        row = {
            "index": idx,
            "coord": list(coord),
            "progressed": bool(res.get("progressed")),
            "actions": int(res.get("actions", 0) or 0),
            "end_state": res.get("end_state"),
            "end_level": res.get("end_level"),
            "board_changed_steps": res.get("board_changed_steps"),
        }
        tested.append(row)
        if not row["progressed"] and first_failure is None:
            first_failure = row
        if row["progressed"]:
            first_success = row
            break

    if first_success is None:
        obstruction = Node(
            "obstruction",
            {
                "residual": residual.id,
                "level": level,
                "signature": key,
                "reason": "declared repeated-click language exhausted without protected progress",
                "tested_candidates": len(tested),
                "max_repeat": MAX_REPEAT,
            },
            (residual.id,),
        )
        log = append(log, obstruction)
        return atlas, log, {
            "status": "EXHAUSTED",
            "level": level,
            "signature": key,
            "tested": tested,
            "obstruction_id": obstruction.id,
        }

    coord = tuple(first_success["coord"])
    verify_a, verify_b = independent_verify(atlas, coord)

    candidate = Node(
        "candidate_capability",
        {
            "residual": residual.id,
            "level": level,
            "guard_signature": key,
            "witness": {"action": "ACTION6", "x": coord[0], "y": coord[1]},
            "selection_rule": "first success in frozen residual-derived candidate order",
            "tested_before_success": first_success["index"],
        },
        (residual.id,),
    )
    log = append(log, candidate)

    verification = Node(
        "verification",
        {
            "candidate": candidate.id,
            "independent_trials": 2,
            "trial_actions": [verify_a["actions"], verify_b["actions"]],
            "protected_progress": [verify_a["progressed"], verify_b["progressed"]],
            "matched_prior_failure": first_failure,
            "search_prefix_length": len(tested),
            "max_repeat": MAX_REPEAT,
        },
        (candidate.id,),
    )
    log = append(log, verification)

    max_steps = max(int(verify_a["actions"]), int(verify_b["actions"]))
    capability = Node(
        "capability",
        {
            "parent_residual": residual.id,
            "guard": {"color_histogram": key},
            "witness": {"action": "ACTION6", "x": coord[0], "y": coord[1]},
            "protected_consequence": "levels_completed increases",
            "max_verified_steps": max_steps,
            "authority": "two independent environment replays after bounded residual search",
        },
        (verification.id,),
    )
    log = append(log, capability)

    new_atlas = dict(atlas)
    new_atlas[key] = {
        "coord": list(coord),
        "max_steps": max_steps,
        "capability_id": capability.id,
        "level_discovered": level,
    }

    return new_atlas, log, {
        "status": "PROMOTED",
        "level": level,
        "signature": key,
        "candidate_count": len(candidates),
        "tested": tested,
        "selected": first_success,
        "verify_a": {k: v for k, v in verify_a.items() if k != "trace" and k != "prefix_trace"},
        "verify_b": {k: v for k, v in verify_b.items() if k != "trace" and k != "prefix_trace"},
        "capability_id": capability.id,
    }


def bootstrap(log) -> tuple[dict[str, dict[str, Any]], Any, list[dict[str, Any]]]:
    atlas: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []

    # Re-earn the known V1 witness from a fresh environment, level by level.
    arcade, env, card = make_env(ENVROOT)
    for expected_actions in (4, 8, 16):
        key = hist_key(env.observation_space)
        level = int(env.observation_space.levels_completed)
        res = execute_click(env, BASE_WITNESS, expected_actions)
        if not res["progressed"] or res["actions"] != expected_actions:
            raise AssertionError(f"bootstrap capability drift at level {level}: {res}")
        cap = Node(
            "capability",
            {
                "guard": {"color_histogram": key},
                "witness": {"action": "ACTION6", "x": BASE_WITNESS[0], "y": BASE_WITNESS[1]},
                "protected_consequence": "levels_completed increases",
                "max_verified_steps": expected_actions,
                "source": "certified-capability-slice-v1",
                "level": level,
            },
        )
        log = append(log, cap)
        atlas[key] = {
            "coord": list(BASE_WITNESS),
            "max_steps": expected_actions,
            "capability_id": cap.id,
            "level_discovered": level,
        }
        records.append({"level": level, "guard": key, "actions": expected_actions, "capability_id": cap.id})
    return atlas, log, records


def blind_replay(atlas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    _, env, _, replay_trace = replay_atlas(atlas)
    return {
        "won": env.observation_space.state == GameState.WIN,
        "state": str(env.observation_space.state),
        "levels_completed": int(env.observation_space.levels_completed),
        "model_calls": 0,
        "atlas_size": len(atlas),
        "trace": replay_trace,
        "residual_signature": None if env.observation_space.state == GameState.WIN else hist_key(env.observation_space),
    }


def main() -> None:
    log = ()
    atlas, log, bootstrap_records = bootstrap(log)
    discoveries: list[dict[str, Any]] = []

    for _ in range(8):
        replay = blind_replay(atlas)
        if replay["won"]:
            break
        atlas2, log2, disc = discover(atlas, log)
        discoveries.append(disc)
        atlas, log = atlas2, log2
        if disc["status"] != "PROMOTED":
            break

    final = blind_replay(atlas)
    result = {
        "status": "WIN" if final["won"] else "RESIDUAL",
        "boundary": {
            "game": "bt33 fixture",
            "source_code_inspection": False,
            "model_calls": 0,
            "search_language": "visible-state-derived coordinate order + exhaustive 64x64 ACTION6 fallback; repeat <=32",
            "promotion_rule": "first frozen-order success + two independent fresh-replay confirmations",
        },
        "bootstrap": bootstrap_records,
        "discoveries": discoveries,
        "atlas": atlas,
        "final_replay": final,
        "metatron_live_count": len(live_ids(log)),
    }
    (OUTDIR / "result.json").write_text(json.dumps(result, indent=2))
    (OUTDIR / "metatron-log.jsonl").write_text(dumps(log))
    print(json.dumps(result, indent=2))
    print("ARC3_RESIDUAL_GENERATED_CAPABILITY_V2=" + result["status"])


if __name__ == "__main__":
    main()
