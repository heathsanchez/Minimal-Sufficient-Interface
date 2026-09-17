from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.recurrence_factor import RecurrenceFactor


def frame(resource: int, world: int, *, width: int = 64, height: int = 12):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    # Small recurrent world state outside the candidate band.
    grid[2][world % 16] = 9
    # Bottom resource bar: count of color 12 shrinks monotonically.
    for x in range(width):
        grid[-1][x] = 12 if x < resource else 11
    return tuple(tuple(row) for row in grid)


class RecurrenceFactorContracts(unittest.TestCase):
    def test_high_recurrence_monotone_multi_action_band_is_admitted(self):
        f = RecurrenceFactor(
            activation_frames=64,
            min_compression=8.0,
            min_scalar_changes=16,
            min_sign_consistency=0.9,
            min_action_classes=2,
            candidate_depths=(1,),
        )
        frames = [frame(64-i, i % 8) for i in range(65)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(0, before, after, (3 if i % 2 == 0 else 4, None, None))

        self.assertTrue(f.active(0, 12, 64))
        self.assertEqual(f.factor_spec(0, 12, 64)["side"], "bottom")
        self.assertEqual(f.factor_spec(0, 12, 64)["depth"], 1)
        self.assertGreaterEqual(f.factor_spec(0, 12, 64)["compression"], 8.0)

        a = frame(20, 3)
        b = frame(7, 3)
        self.assertEqual(f.world_digest(0, a), f.world_digest(0, b))
        self.assertNotEqual(f.factor_signature(0, a), f.factor_signature(0, b))

    def test_moderate_recurrence_gain_does_not_earn_substitution(self):
        f = RecurrenceFactor(
            activation_frames=64,
            min_compression=8.0,
            min_scalar_changes=16,
            min_sign_consistency=0.9,
            min_action_classes=2,
            candidate_depths=(1,),
        )
        frames = [frame(64-i, i % 12) for i in range(65)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(0, before, after, (3 if i % 2 == 0 else 4, None, None))
        self.assertTrue(f.frozen(0, 12, 64))
        self.assertFalse(f.active(0, 12, 64))

    def test_single_action_monotone_band_does_not_earn_substitution(self):
        f = RecurrenceFactor(
            activation_frames=64,
            min_compression=8.0,
            min_scalar_changes=16,
            min_sign_consistency=0.9,
            min_action_classes=2,
            candidate_depths=(1,),
        )
        frames = [frame(64-i, i % 8) for i in range(65)]
        for before, after in zip(frames, frames[1:]):
            f.observe(0, before, after, (3, None, None))
        self.assertTrue(f.frozen(0, 12, 64))
        self.assertFalse(f.active(0, 12, 64))

    def test_factor_signature_is_reconstructive_for_removed_band(self):
        f = RecurrenceFactor(
            activation_frames=64,
            min_compression=8.0,
            min_scalar_changes=16,
            min_sign_consistency=0.9,
            min_action_classes=2,
            candidate_depths=(1,),
        )
        frames = [frame(64-i, i % 8) for i in range(65)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            f.observe(0, before, after, (3 if i % 2 == 0 else 4, None, None))
        signature = f.factor_signature(0, frame(23, 2))
        restored = f.restore(0, f.world_projection(0, frame(23, 2)), signature)
        self.assertEqual(restored, frame(23, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
