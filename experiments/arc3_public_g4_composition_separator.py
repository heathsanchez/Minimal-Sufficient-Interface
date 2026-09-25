from __future__ import annotations

import json
import os

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import SemanticPathSession, _bbox, _components, _matrix, _source_bits


POINTS = {"large": (15, 58), "middle": (25, 58), "origin": (35, 58)}
SEQUENCES = (
    ("middle", "origin"),
    ("origin", "middle"),
    ("middle", "large"),
    ("origin", "large"),
)


def enter_g4():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    session = SemanticPathSession.start(frame)
    while session.phase != "done":
        x, y = session.next_action(frame)
        frame = ab.click(env, (y, x))
    return env


def left_foreground(grid):
    components = []
    for component in _components(grid, (4,)):
        top, left, bottom, right = _bbox(component)
        if top < 32 and right < 32:
            components.append({"size": len(component), "bbox": [top, left, bottom, right]})
    return sorted(components, key=lambda item: (item["bbox"], item["size"]))


def main() -> None:
    results = []
    for sequence in SEQUENCES:
        env = enter_g4()
        trace = []
        for label in sequence:
            x, y = POINTS[label]
            frame = ab.click(env, (y, x))
            grid = _matrix(frame)
            trace.append({
                "label": label,
                "source": list(_source_bits(grid)),
                "left_foreground": left_foreground(grid),
            })
        results.append({"sequence": sequence, "trace": trace})
    print(json.dumps(results, indent=2), flush=True)
    print("ARC3_PUBLIC_G4_COMPOSITION_SEPARATOR=PASS", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
