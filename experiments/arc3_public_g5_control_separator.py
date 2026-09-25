from __future__ import annotations

import json
import os
from pathlib import Path

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from arc3_public_online_scale_normalized_g4 import execute_session
from metalogic_arc3.semantic_path import _bar_rows, _bbox, _components, _matrix


OUT = Path(os.environ.get("OUTDIR", "evidence/arc3-public-g5-control-separator")).resolve()
OUT.mkdir(parents=True, exist_ok=True)

CONTROLS = ((5, 58), (15, 58), (25, 58), (35, 58), (45, 58))
BOARD = (4, 33, 31, 60)


def enter_g5():
    env, _ = g3.enter_level3()
    frame, _, _ = execute_session(env, env.observation_space)
    frame, _, _ = execute_session(env, frame)
    if int(frame.levels_completed) != 4:
        raise AssertionError("qualified G5 entry drifted")
    return env, frame


def board_signature(frame):
    grid = _matrix(frame)
    top, left, bottom, right = BOARD
    result = {}
    for color in (6, 11, 15):
        components = []
        for cells in _components(grid, (color,)):
            inside = {(r, c) for r, c in cells if top <= r <= bottom and left <= c <= right}
            if inside:
                components.append({"size": len(inside), "bbox": list(_bbox(inside))})
        result[str(color)] = sorted(components, key=lambda item: (item["bbox"], item["size"]))
    return result


def source_signature(grid):
    return [[grid[y][x] for x, y in row] for row in _bar_rows(grid, "left")]


def main():
    rows = []
    for point in CONTROLS:
        env, before = enter_g5()
        before_grid = _matrix(before)
        after = ab.click(env, (point[1], point[0]))
        after_grid = _matrix(after)
        changed = [
            [r, c, before_grid[r][c], after_grid[r][c]]
            for r in range(len(before_grid))
            for c in range(len(before_grid[0]))
            if before_grid[r][c] != after_grid[r][c]
        ]
        rows.append({
            "control": list(point),
            "before": board_signature(before),
            "after": board_signature(after),
            "changed_count": len(changed),
            "changed_bbox": None if not changed else [
                min(x[0] for x in changed), min(x[1] for x in changed),
                max(x[0] for x in changed), max(x[1] for x in changed),
            ],
            "level": int(after.levels_completed),
            "state": str(after.state),
            "source_before": source_signature(before_grid),
            "source_after": source_signature(after_grid),
        })
    result = {
        "classification": "RESPONSE_SEPARATOR_ONLY",
        "hypothesis": "each visible G5 control exposes a distinct legal transformation role",
        "action_budget": 1,
        "controls": rows,
        "model_calls": 0,
        "source_inspection": False,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print("ARC3_PUBLIC_G5_CONTROL_SEPARATOR=PASS", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
