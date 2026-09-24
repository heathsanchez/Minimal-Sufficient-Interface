from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = (
    Path(__file__).parents[1]
    / "experiments"
    / "arc3_public_path_program_g3.py"
)


def load_module():
    assert MODULE_PATH.exists(), "path-program experiment has not been implemented"
    sys.path.insert(0, str(MODULE_PATH.parent))
    spec = importlib.util.spec_from_file_location("path_program", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_shortest_paths_respect_the_observed_wall_gap():
    m = load_module()
    blocked = {(row, 3) for row in (0, 1, 2, 4, 5, 6)}
    paths = m.shortest_paths((4, 1), (2, 5), blocked, 7, 7)
    assert paths == ["URRRUR", "URRRRU", "RURRUR", "RURRRU"]


def test_path_compiles_to_observed_direction_codewords():
    m = load_module()
    codes = {
        "U": [1, 0, 0, 0, 0, 1],
        "R": [0, 1, 0, 0, 0, 0],
    }
    assert m.compile_columns("URRRUR", codes) == [
        [1, 0, 0, 0, 0, 1],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 0, 0, 0, 0],
    ]


def test_submit_is_discovered_from_the_large_bottom_right_control():
    m = load_module()
    components = [
        {"color": 9, "size": 32, "cells": [(r, c) for r in range(54, 63) for c in range(1, 10) if r in (54, 62) or c in (1, 9)]},
        {"color": 9, "size": 69, "cells": [(58, 57), (57, 57), (59, 57), (58, 56), (58, 58)]},
    ]
    assert m.discover_submit(components) == (58, 57)
    assert m.discover_submit(components) != (58, 46)
