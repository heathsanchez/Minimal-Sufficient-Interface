from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path

OUT = Path(
    os.environ.get("OUTDIR", "evidence/arc3-public-path-program-g3")
).resolve()
OUT.mkdir(parents=True, exist_ok=True)

GameState = None
ab = None
g3 = None
glyphs = None
sem = None


def require_runtime():
    global GameState, ab, g3, glyphs, sem
    if ab is not None:
        return
    from arcengine import GameState as game_state
    import arc3_public_all_blue_to_gray_g2 as ab_module
    import arc3_public_panel_correspondence_g3 as g3_module
    import arc3_public_selector_glyph_decoder as glyphs_module
    import arc3_public_semantic_relation_g3 as sem_module

    GameState = game_state
    ab = ab_module
    g3 = g3_module
    glyphs = glyphs_module
    sem = sem_module

DIRECTION_ORDER = (
    ("U", (-1, 0)),
    ("D", (1, 0)),
    ("L", (0, -1)),
    ("R", (0, 1)),
)


def shortest_paths(start, goal, blocked, height, width):
    blocked = set(blocked)
    queue = deque([(tuple(start), "")])
    distance = {tuple(start): 0}
    selected = []
    optimum = None

    while queue:
        point, path = queue.popleft()
        if optimum is not None and len(path) > optimum:
            continue
        if point == tuple(goal):
            optimum = len(path)
            selected.append(path)
            continue
        for name, (dr, dc) in DIRECTION_ORDER:
            nxt = (point[0] + dr, point[1] + dc)
            if not (0 <= nxt[0] < height and 0 <= nxt[1] < width):
                continue
            if nxt in blocked:
                continue
            new_distance = len(path) + 1
            if new_distance <= distance.get(nxt, 10**9):
                distance[nxt] = new_distance
                queue.append((nxt, path + name))
    return selected


def compile_columns(path, direction_codes):
    return [list(direction_codes[step]) for step in path]


def bbox(comp):
    cells = [tuple(cell) for cell in comp["cells"]]
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    return [min(rows), min(cols), max(rows), max(cols)]


def discover_submit(components):
    candidates = []
    for comp in components:
        box = bbox(comp)
        if int(comp["color"]) == 9 and box[0] >= 50 and box[1] >= 40:
            candidates.append((int(comp["size"]), box))
    if not candidates:
        raise AssertionError("large bottom-right submit control not found")
    _, box = max(candidates)
    return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)


def selector_direction(box):
    patch = box["patch"]
    cells = [
        (r, c)
        for r, row in enumerate(patch)
        for c, value in enumerate(row)
        if int(value) == 11
    ]
    if not cells:
        raise AssertionError("selector has no color-11 block")
    mean_r = sum(r for r, _ in cells) / len(cells)
    mean_c = sum(c for _, c in cells) / len(cells)
    centre_r = (len(patch) - 1) / 2
    centre_c = (len(patch[0]) - 1) / 2
    dr = mean_r - centre_r
    dc = mean_c - centre_c
    if abs(dr) > abs(dc):
        return "D" if dr > 0 else "U"
    return "R" if dc > 0 else "L"


def all_selector_boxes(frame):
    require_runtime()
    grid = glyphs.frame_grid(frame)
    singles = []
    for comp in ab.comps(frame):
        if int(comp["color"]) == 0 and int(comp["size"]) == 1:
            singles.extend(tuple(cell) for cell in comp["cells"])

    boxes = []
    for comp in ab.comps(frame):
        if int(comp["color"]) != 5 or int(comp["size"]) != 41:
            continue
        cells = [tuple(cell) for cell in comp["cells"]]
        rows = [r for r, _ in cells]
        cols = [c for _, c in cells]
        r0, c0, r1, c1 = min(rows), min(cols), max(rows), max(cols)
        if r0 < 50 or r1 - r0 != 6 or c1 - c0 != 6:
            continue
        holes = sorted(
            point
            for point in singles
            if r0 <= point[0] <= r1 and c0 <= point[1] <= c1
        )
        patch = [
            [grid[r][c] for c in range(c0, c1 + 1)]
            for r in range(r0, r1 + 1)
        ]
        boxes.append(
            {
                "bbox": [r0, c0, r1, c1],
                "holes": [list(point) for point in holes],
                "patch": patch,
            }
        )
    return sorted(boxes, key=lambda item: item["bbox"][1])


def direction_codebook():
    require_runtime()
    base, _ = g3.enter_level3()
    boxes = all_selector_boxes(base.observation_space)
    if len(boxes) != 4:
        raise AssertionError(f"expected four directional selectors, got {len(boxes)}")

    codes = {}
    records = []
    for box in boxes:
        direction = selector_direction(box)
        env, _ = g3.enter_level3()
        hole = tuple(box["holes"][0])
        ab.click(env, hole)
        code = glyphs.source_bits(env.observation_space)[1]
        codes[direction] = code
        records.append(
            {
                "direction": direction,
                "bbox": box["bbox"],
                "probe": list(hole),
                "code": code,
            }
        )
    if set(codes) != {"U", "D", "L", "R"}:
        raise AssertionError(f"incomplete direction codebook: {codes}")
    return codes, records


def right_board(frame):
    require_runtime()
    components = ab.comps(frame)
    tile_boxes = []
    for comp in components:
        box = bbox(comp)
        h = box[2] - box[0] + 1
        w = box[3] - box[1] + 1
        if box[0] < 32 and box[1] >= 31 and h % 4 == 0 and w % 4 == 0:
            tile_boxes.append(box)
    if not tile_boxes:
        raise AssertionError("right tile board not found")

    top = min(box[0] for box in tile_boxes)
    left = min(box[1] for box in tile_boxes)
    bottom = max(box[2] for box in tile_boxes)
    right = max(box[3] for box in tile_boxes)
    cell = 4
    height = (bottom - top + 1) // cell
    width = (right - left + 1) // cell

    blocked = set()
    start = None
    goal = None
    for comp in components:
        box = bbox(comp)
        if box[0] < top or box[1] < left or box[2] > bottom or box[3] > right:
            continue
        color = int(comp["color"])
        if color == 6:
            for row in range((box[0] - top) // cell, (box[2] - top) // cell + 1):
                for col in range((box[1] - left) // cell, (box[3] - left) // cell + 1):
                    blocked.add((row, col))
        if int(comp["size"]) == 14 and color == 11:
            start = ((box[0] - top) // cell, (box[1] - left) // cell)
        if int(comp["size"]) == 14 and color == 4:
            goal = ((box[0] - top) // cell, (box[1] - left) // cell)

    if start is None or goal is None:
        raise AssertionError(f"start/goal not found: start={start} goal={goal}")
    return {
        "origin": [top, left],
        "cell": cell,
        "height": height,
        "width": width,
        "start": list(start),
        "goal": list(goal),
        "blocked": [list(point) for point in sorted(blocked)],
    }


def write_columns(env, columns):
    require_runtime()
    _, _, targets = sem.semantic_surface(env.observation_space)
    writes = []
    for row in range(6):
        for col in range(6):
            want = columns[col][row]
            if sem.bit(targets[row][col]["color"]) == want:
                continue
            point = tuple(targets[row][col]["rc"])
            ab.click(env, point)
            writes.append(list(point))
    return writes


def run_candidate(path, direction_codes):
    require_runtime()
    env, _ = g3.enter_level3()
    start_level = int(env.observation_space.levels_completed)
    columns = compile_columns(path, direction_codes)
    writes = write_columns(env, columns)
    submit = discover_submit(ab.comps(env.observation_space))
    frame = ab.click(env, submit)
    progressed = int(frame.levels_completed) > start_level or frame.state == GameState.WIN
    return {
        "path": path,
        "columns": columns,
        "writes": writes,
        "write_count": len(writes),
        "submit": list(submit),
        "progressed": progressed,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
    }


def main():
    require_runtime()
    base, _ = g3.enter_level3()
    board = right_board(base.observation_space)
    paths = shortest_paths(
        board["start"],
        board["goal"],
        {tuple(point) for point in board["blocked"]},
        board["height"],
        board["width"],
    )
    codes, selectors = direction_codebook()

    tested = []
    selected = None
    verification = []
    for path in paths:
        result = run_candidate(path, codes)
        tested.append(result)
        if not result["progressed"]:
            continue
        verification = [run_candidate(path, codes), run_candidate(path, codes)]
        if all(replay["progressed"] for replay in verification):
            selected = result
            break

    status = "PROMOTED" if selected else "RESIDUAL"
    result = {
        "status": status,
        "hypothesis": (
            "the six target columns are a shortest legal path program on the "
            "observed right-hand 7x7 tile board; each selector orientation supplies "
            "the corresponding six-bit instruction code through the source panel"
        ),
        "board": board,
        "direction_codes": codes,
        "selectors": selectors,
        "shortest_paths": paths,
        "tested": tested,
        "selected": selected,
        "verification": verification,
        "terminal_correction": {
            "old_non_submit": [58, 46],
            "discovered_submit": selected["submit"] if selected else None,
            "implication": (
                "earlier G3 zero-progress terminal sweeps that used (58,46) did not "
                "invoke the observed G3 submit control and require reclassification"
            ),
        },
        "model_calls": 0,
        "source_inspection": False,
        "max_g3_actions": 37,
        "claim_boundary": (
            "exact public tn36 G3 entered from hard restart through the qualified G1 "
            "and G2 solver; board, obstacles, start, goal, selector directions, "
            "direction codewords and submit control derived only from legal visible "
            "observations; enumerate only shortest legal paths in the observed 7x7 "
            "board; compile path steps to target columns; selected progress replayed "
            "twice from independent hard restarts"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"ARC3_PUBLIC_PATH_PROGRAM_G3={status}")


if __name__ == "__main__":
    main()
