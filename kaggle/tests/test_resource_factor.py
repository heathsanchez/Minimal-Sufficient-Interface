from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.resource_factor import ResourceFactor


def with_bar(active: int, *, width: int = 16, height: int = 12):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[height - 1][x] = 12 if x < active else 11
    return tuple(tuple(row) for row in grid)


def with_interior_marker(x: int, *, width: int = 16, height: int = 12):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    grid[height // 2][x] = 7
    return tuple(tuple(row) for row in grid)


class ResourceFactorContracts(unittest.TestCase):
    def test_dormant_before_bounded_evidence_horizon(self):
        f = ResourceFactor(activation_transitions=8, min_positions=6)
        frames = [with_bar(16 - i) for i in range(5)]
        for before, after in zip(frames, frames[1:]):
            f.observe(0, before, after)
        self.assertFalse(f.active(0, 12, 16))
        self.assertEqual(f.masked_positions(0, 12, 16), ())

    def test_factors_monotone_edge_bar_and_retains_scalar(self):
        f = ResourceFactor(activation_transitions=8, min_positions=6)
        frames = [with_bar(16 - i) for i in range(10)]
        for before, after in zip(frames, frames[1:]):
            f.observe(0, before, after)

        self.assertTrue(f.active(0, 12, 16))
        mask = f.masked_positions(0, 12, 16)
        self.assertGreaterEqual(len(mask), 6)
        self.assertTrue(all(y >= 9 for x, y in mask))

        a = with_bar(9)
        b = with_bar(6)
        self.assertEqual(f.world_digest(0, a), f.world_digest(0, b))
        self.assertNotEqual(f.resource_signature(0, a), f.resource_signature(0, b))

    def test_interior_motion_is_never_factored_as_resource_ui(self):
        f = ResourceFactor(activation_transitions=8, min_positions=6)
        frames = [with_interior_marker(x) for x in range(1, 11)]
        for before, after in zip(frames, frames[1:]):
            f.observe(0, before, after)
        self.assertTrue(f.frozen(0, 12, 16))
        self.assertFalse(f.active(0, 12, 16))
        self.assertEqual(f.masked_positions(0, 12, 16), ())

    def test_resource_ledger_retains_cost_evidence_separately(self):
        f = ResourceFactor(activation_transitions=8, min_positions=6)
        frames = [with_bar(16 - i) for i in range(10)]
        for before, after in zip(frames, frames[1:]):
            f.observe(0, before, after)
        before, after = with_bar(8), with_bar(7)
        f.note_transition(
            "world-a", (3, None, None), "world-b",
            f.resource_signature(0, before),
            f.resource_signature(0, after),
        )
        rows = f.resource_transitions()
        self.assertEqual(len(rows), 1)
        self.assertNotEqual(rows[0]["before"], rows[0]["after"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
