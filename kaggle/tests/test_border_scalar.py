from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.border_scalar import BorderScalarFactor


def bar_frame(remaining: int, *, width: int = 32, height: int = 16):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[-1][x] = 12 if x < remaining else 11
    # recurrent world marker independent of budget
    grid[5][5] = 8
    return tuple(tuple(r) for r in grid)


def interior_walk(step: int, *, width: int = 32, height: int = 16):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    grid[height // 2][step % width] = 8
    return tuple(tuple(r) for r in grid)


class BorderScalarContracts(unittest.TestCase):
    def test_admits_monotone_multi_action_border_scalar_with_recurrence_gain(self):
        f = BorderScalarFactor(
            activation_transitions=16,
            min_changes=6,
            min_action_classes=2,
            min_sign_consistency=0.9,
            min_projection_compression=2.0,
        )
        frames = [bar_frame(max(0, 32 - (i % 17))) for i in range(18)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(
                0, before, after,
                (3 if i % 2 == 0 else 4, None, None),
                descriptor=f"primitive:{3 if i % 2 == 0 else 4}",
                history=str(i),
                terminal=False,
            )
        self.assertTrue(f.active(0, 16, 32))
        candidate = f.candidate(0, 16, 32)
        self.assertEqual(candidate["side"], "bottom")
        self.assertEqual(candidate["depth"], 1)
        self.assertGreaterEqual(candidate["compression"], 2.0)
        self.assertGreaterEqual(candidate["sign_consistency"], 0.9)
        self.assertEqual(candidate["direction"], -1)

    def test_projected_world_identity_forgets_only_admitted_band(self):
        f = BorderScalarFactor(
            activation_transitions=16,
            min_changes=6,
            min_action_classes=2,
            min_sign_consistency=0.9,
            min_projection_compression=2.0,
        )
        frames = [bar_frame(max(0, 32 - (i % 17))) for i in range(18)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(0, before, after, (3 + i % 2, None, None),
                      descriptor="p", history=str(i), terminal=False)
        a, b = bar_frame(20), bar_frame(8)
        self.assertEqual(f.world_digest(0, a), f.world_digest(0, b))
        self.assertNotEqual(f.scalar_signature(0, a), f.scalar_signature(0, b))

    def test_interior_motion_does_not_earn_border_substitution(self):
        f = BorderScalarFactor(
            activation_transitions=16,
            min_changes=6,
            min_action_classes=2,
            min_sign_consistency=0.9,
            min_projection_compression=2.0,
        )
        frames = [interior_walk(i) for i in range(18)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(0, before, after, (3 + i % 2, None, None),
                      descriptor="p", history=str(i), terminal=False)
        self.assertTrue(f.frozen(0, 16, 32))
        self.assertFalse(f.active(0, 16, 32))

    def test_buffer_is_retained_for_replay_after_admission(self):
        f = BorderScalarFactor(
            activation_transitions=16,
            min_changes=6,
            min_action_classes=2,
            min_sign_consistency=0.9,
            min_projection_compression=2.0,
        )
        frames = [bar_frame(max(0, 32 - (i % 17))) for i in range(18)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(0, before, after, (3 + i % 2, None, None),
                      descriptor="p", history=f"h{i}", terminal=False)
        rows = f.buffered_transitions(0, 16, 32)
        self.assertGreaterEqual(len(rows), 16)
        self.assertEqual(rows[0]["history"], "h0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
