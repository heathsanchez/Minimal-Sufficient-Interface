from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import ActionToken, normalize_frame


def frame(grid, *, actions=(3, 4)):
    return {
        "frame": [grid],
        "levels_completed": 0,
        "state": "NOT_FINISHED",
        "available_actions": list(actions),
    }


def point(x: int, y: int):
    rows = [[0 for _ in range(6)] for _ in range(4)]
    rows[y][x] = 7
    return rows


class MotionControllerContracts(unittest.TestCase):
    def test_reliable_motion_model_outranks_generic_affordance_repetition(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        a_right = (3, None, None)
        a_left = (4, None, None)
        c.motions.record(a_right, tuple(map(tuple, point(1, 1))), tuple(map(tuple, point(2, 1))))
        c.motions.record(a_right, tuple(map(tuple, point(2, 1))), tuple(map(tuple, point(3, 1))))
        c.motions.record(a_left, tuple(map(tuple, point(3, 1))), tuple(map(tuple, point(2, 1))))
        c.motions.record(a_left, tuple(map(tuple, point(2, 1))), tuple(map(tuple, point(1, 1))))

        obs = normalize_frame(frame(point(3, 1)))
        c._grid = tuple(tuple(row) for row in point(3, 1))
        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 1
        chosen = c._select_probe(obs, catalog)
        self.assertEqual(chosen.action_id, 3)
        self.assertEqual(chosen.source, "motion_frontier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
