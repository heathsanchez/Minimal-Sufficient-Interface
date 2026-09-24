from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = (
    Path(__file__).parents[1]
    / "experiments"
    / "arc3_public_port_role_decoder_g3.py"
)


def load_module():
    assert MODULE_PATH.exists(), "port-role decoder experiment has not been implemented"
    sys.path.insert(0, str(MODULE_PATH.parent))
    spec = importlib.util.spec_from_file_location("port_role_decoder", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def glyph(block_side: str):
    patch = [[5] * 7 for _ in range(7)]
    if block_side == "left":
        block = [(r, c) for r in range(2, 5) for c in range(0, 2)]
        holes = [(3, 3), (3, 5)]
    elif block_side == "top":
        block = [(r, c) for r in range(0, 2) for c in range(2, 5)]
        holes = [(3, 3), (5, 3)]
    elif block_side == "bottom":
        block = [(r, c) for r in range(5, 7) for c in range(2, 5)]
        holes = [(1, 3), (3, 3)]
    else:
        raise ValueError(block_side)
    for r, c in block:
        patch[r][c] = 11
    for r, c in holes:
        patch[r][c] = 0
    return patch, holes


def test_color11_distance_transports_near_far_role_across_glyph_orientations():
    m = load_module()
    for side in ("left", "top", "bottom"):
        patch, holes = glyph(side)
        roles = m.classify_port_roles(patch, holes)
        assert sorted(roles.values()) == ["far", "near"]
        near = min(
            holes,
            key=lambda p: m.distance_to_color(p, patch, 11),
        )
        assert roles[near] == "near"


def test_g2_supervision_leaves_exactly_two_new_role_specific_decoders():
    m = load_module()
    before = [1, 0, 0, 0, 0, 1]
    interventions = [
        {"role": "near", "before": before, "after": [1, 0, 0, 0, 0, 0]},
        {"role": "far", "before": before, "after": [1, 0, 0, 0, 0, 0]},
        {"role": "near", "before": before, "after": before},
        {"role": "far", "before": before, "after": before},
    ]
    survivors = m.fit_role_masks(interventions, winner=before)
    assert survivors == [(12, 12), (12, 14), (14, 12), (14, 14)]
    assert m.novel_mixed_pairs(survivors) == [(12, 14), (14, 12)]


def test_mixed_decoder_uses_observed_role_to_split_equal_immediate_responses():
    m = load_module()
    before = [1, 1, 0, 0, 0, 0]
    after = [1, 0, 0, 0, 0, 1]
    masks = {"near": 12, "far": 14}
    assert m.decode_column(masks, "near", before, after) == before
    assert m.decode_column(masks, "far", before, after) == [1, 1, 0, 0, 0, 1]
