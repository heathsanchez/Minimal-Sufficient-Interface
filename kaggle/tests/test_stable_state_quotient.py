from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.stable_state import StableStateQuotient


def grid(volatile: int, marker_x: int = 2):
    rows = [
        [volatile, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]
    rows[2][marker_x] = 7
    return tuple(tuple(row) for row in rows)


class StableStateQuotientContracts(unittest.TestCase):
    def test_is_dormant_before_residual_threshold(self):
        q = StableStateQuotient(
            activation_transitions=4,
            min_change_rate=0.75,
            min_action_classes=2,
        )
        q.observe(0, grid(0), grid(1), (1, None, None))
        q.observe(0, grid(1), grid(2), (2, None, None))
        self.assertFalse(q.active(0, 3, 3))
        self.assertNotEqual(q.digest(0, grid(1)), q.digest(0, grid(2)))

    def test_masks_ubiquitous_multi_intervention_volatility_only(self):
        q = StableStateQuotient(
            activation_transitions=4,
            min_change_rate=0.75,
            min_action_classes=2,
        )
        transitions = [
            (grid(0, 2), grid(1, 2), (1, None, None)),
            (grid(1, 2), grid(2, 1), (2, None, None)),
            (grid(2, 1), grid(3, 1), (3, None, None)),
            (grid(3, 1), grid(4, 2), (4, None, None)),
        ]
        for before, after, action in transitions:
            q.observe(0, before, after, action)

        self.assertTrue(q.active(0, 3, 3))
        self.assertEqual(q.masked_positions(0, 3, 3), ((0, 0),))
        self.assertEqual(q.digest(0, grid(10, 2)), q.digest(0, grid(99, 2)))
        self.assertNotEqual(q.digest(0, grid(10, 2)), q.digest(0, grid(10, 1)))

    def test_single_intervention_family_cannot_erase_state(self):
        q = StableStateQuotient(
            activation_transitions=4,
            min_change_rate=0.75,
            min_action_classes=2,
        )
        current = grid(0)
        for value in range(1, 5):
            nxt = grid(value)
            q.observe(0, current, nxt, (3, None, None))
            current = nxt
        self.assertTrue(q.active(0, 3, 3))
        self.assertEqual(q.masked_positions(0, 3, 3), ())
        self.assertNotEqual(q.digest(0, grid(4)), q.digest(0, grid(5)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
