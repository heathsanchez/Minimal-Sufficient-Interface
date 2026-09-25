from __future__ import annotations

import json
import os

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import (
    SemanticPathSession,
    _bbox,
    _components,
    _matrix,
    _source_bits,
)


PROBES = ((15, 58), (25, 58), (35, 58))


def enter_g4():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    session = SemanticPathSession.start(frame)
    while session.phase != "done":
        x, y = session.next_action(frame)
        frame = ab.click(env, (y, x))
    if int(frame.levels_completed) != 3:
        raise AssertionError(f"expected G4, got level={frame.levels_completed} state={frame.state}")
    return env, frame


def purple_board_components(grid):
    return [
        {"size": len(component), "bbox": list(_bbox(component))}
        for component in sorted(_components(grid, (11,)), key=_bbox)
        if _bbox(component)[0] < 32 and _bbox(component)[1] >= 32
    ]


def changed_cells(before, after):
    return [
        [row, col, before[row][col], after[row][col]]
        for row in range(len(before))
        for col in range(len(before[0]))
        if before[row][col] != after[row][col]
    ]


def render_left(grid):
    chars = {0: "0", 1: "1", 2: "2", 3: "3", 4: ".", 5: "+", 6: "#", 9: "S", 11: "X"}
    return ["".join(chars.get(grid[row][col], "?") for col in range(32)) for row in range(32)]


def main() -> None:
    results = []
    for x, y in PROBES:
        env, frame = enter_g4()
        before = _matrix(frame)
        after_frame = ab.click(env, (y, x))
        after = _matrix(after_frame)
        changes = changed_cells(before, after)
        results.append({
            "probe_xy": [x, y],
            "level": int(after_frame.levels_completed),
            "state": str(after_frame.state),
            "change_count": len(changes),
            "source_before": list(_source_bits(before)),
            "source_after": list(_source_bits(after)),
            "left_before": render_left(before),
            "left_after": render_left(after),
            "board_before": purple_board_components(before),
            "board_after": purple_board_components(after),
        })
    print(json.dumps(results, indent=2), flush=True)
    print("ARC3_PUBLIC_G4_CONTROL_SEPARATOR=PASS", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
