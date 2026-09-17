from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.transport import MotionMemory, extract_transports


def point(x: int, y: int, *, width: int = 6, height: int = 4):
    rows = [[0 for _ in range(width)] for _ in range(height)]
    rows[y][x] = 7
    return tuple(tuple(row) for row in rows)


def block(x: int, y: int, *, width: int = 6, height: int = 4):
    rows = [[0 for _ in range(width)] for _ in range(height)]
    rows[y][x] = 7
    rows[y][x + 1] = 7
    return tuple(tuple(row) for row in rows)


class TransportContracts(unittest.TestCase):
    def test_extracts_exact_component_translation(self):
        rows = extract_transports(point(1, 1), point(2, 1))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.dx, 1)
        self.assertEqual(row.dy, 0)
        self.assertEqual(row.origin_before, (1, 1))
        self.assertEqual(row.origin_after, (2, 1))
        self.assertEqual(row.area, 1)

    def test_shape_change_is_not_transport(self):
        self.assertEqual(extract_transports(point(1, 1), block(1, 1)), ())

    def test_learns_action_conditioned_motion_and_prefers_unvisited_frontier(self):
        memory = MotionMemory(min_support=2, min_dominance=1.0)
        a_right = (3, None, None)
        a_left = (4, None, None)

        memory.record(a_right, point(1, 1), point(2, 1))
        memory.record(a_right, point(2, 1), point(3, 1))
        memory.record(a_left, point(3, 1), point(2, 1))
        memory.record(a_left, point(2, 1), point(1, 1))

        self.assertEqual(memory.reliable_control_count, 2)
        chosen = memory.recommend(point(3, 1), (a_right, a_left))
        self.assertEqual(chosen, a_right)

    def test_ambiguous_identical_components_do_not_fabricate_motion(self):
        before = (
            (0, 0, 0, 0, 0),
            (0, 7, 0, 7, 0),
            (0, 0, 0, 0, 0),
        )
        after = (
            (0, 0, 0, 0, 0),
            (7, 0, 7, 0, 0),
            (0, 0, 0, 0, 0),
        )
        # Two identical components can admit multiple pairings. Unless the
        # entire origin set is related by one exact translation, stay UNKNOWN.
        self.assertEqual(extract_transports(before, after), ())

    def test_blocked_local_move_forces_route_to_nearest_frontier(self):
        memory = MotionMemory(min_support=2, min_dominance=1.0)
        a_right = (3, None, None)
        a_left = (4, None, None)

        memory.record(a_right, point(1, 1), point(2, 1))
        memory.record(a_right, point(2, 1), point(3, 1))
        memory.record(a_left, point(3, 1), point(2, 1))
        memory.record(a_left, point(2, 1), point(1, 1))

        self.assertEqual(memory.recommend(point(3, 1), (a_right, a_left)), a_right)

        # The globally valid RIGHT control is blocked at this local position.
        memory.record(a_right, point(3, 1), point(3, 1))
        self.assertEqual(memory.blocked_local_count, 1)

        # RIGHT must not be retried here. LEFT is the first edge on the known
        # path back to x=1, where LEFT remains an untried modeled control.
        self.assertEqual(memory.recommend(point(3, 1), (a_right, a_left)), a_left)


if __name__ == "__main__":
    unittest.main(verbosity=2)
