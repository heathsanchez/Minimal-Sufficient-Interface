from __future__ import annotations

import json
import os

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import _matrix, _source_bits


PROBES = ((5, 56, "D"), (15, 58, "U"), (25, 58, "L"), (33, 58, "R"))


def render_left(grid):
    chars = {0: "0", 1: "1", 2: "2", 3: "3", 4: ".", 5: "+", 6: "#", 9: "S", 11: "X"}
    return ["".join(chars.get(grid[row][col], "?") for col in range(32)) for row in range(32)]


def main() -> None:
    results = []
    for x, y, direction in PROBES:
        env, _ = g3.enter_level3()
        before = _matrix(env.observation_space)
        after_frame = ab.click(env, (y, x))
        after = _matrix(after_frame)
        results.append({
            "direction": direction,
            "source_before": list(_source_bits(before)),
            "source_after": list(_source_bits(after)),
            "left_before": render_left(before),
            "left_after": render_left(after),
        })
    print(json.dumps(results, indent=2), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
