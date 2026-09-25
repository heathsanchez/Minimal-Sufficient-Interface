from __future__ import annotations

from collections import Counter
import os

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import (
    SemanticPathSession,
    _bbox,
    _components,
    _find_board,
    _matrix,
)


def main() -> None:
    env, _ = g3.enter_level3()
    frame = env.observation_space
    session = SemanticPathSession.start(frame)
    while session.phase != "done":
        x, y = session.next_action(frame)
        frame = ab.click(env, (y, x))

    grid = _matrix(frame)
    print("level", frame.levels_completed, "state", frame.state)
    print("palette", sorted(Counter(value for row in grid for value in row).items()))
    print("board_origin", _find_board(grid))

    chars = {0: "0", 1: "1", 2: "2", 3: "3", 4: ".", 5: "+", 6: "#", 9: "S", 10: "A", 11: "X", 14: "E"}
    print("board_patch")
    for row in range(32):
        print(f"{row:02d}", "".join(chars.get(grid[row][col], "?") for col in range(32, 64)))

    print("lower_surface")
    for row in range(32, 64):
        print(f"{row:02d}", "".join(chars.get(grid[row][col], "?") for col in range(64)))

    print("color11_components")
    for component in sorted(_components(grid, (11,)), key=_bbox):
        box = _bbox(component)
        print("size", len(component), "bbox", box)
        top, left, bottom, right = box
        for row in range(top, bottom + 1):
            print(" ", "".join(
                "X" if (row, col) in component else chars.get(grid[row][col], "?")
                for col in range(left, right + 1)
            ))
    print("ARC3_PUBLIC_G4_GEOMETRY_DIAGNOSTIC=PASS", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
