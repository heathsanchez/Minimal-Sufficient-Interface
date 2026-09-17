from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.memory_controller import MemoryGraphController


def frame(value: int = 0, *, actions=(3, 4)):
    grid = [[value for _ in range(4)] for _ in range(4)]
    return {
        "frame": [grid],
        "levels_completed": 0,
        "state": "NOT_FINISHED",
        "available_actions": list(actions),
    }


class MemoryGraphControllerContracts(unittest.TestCase):
    def test_failed_leaf_backtracks_at_leaf_not_at_root(self):
        c = MemoryGraphController((3, 4), archived_capabilities=())
        start = frame()

        first_episode = [c.observe_and_choose(start).action_id for _ in range(4)]
        self.assertEqual(first_episode, [3, 4, 3, 4])
        c.record_terminal_failure("GAME_OVER")
        c.reset_episode()

        # 3434 is refuted, but neither 3 nor 34 nor 343 is yet closed: each
        # still has an untested sibling.  Therefore replay is permitted until
        # the exact failed leaf, where the controller must take the sibling.
        second_episode = [c.observe_and_choose(start).action_id for _ in range(4)]
        self.assertEqual(second_episode, [3, 4, 3, 3])


if __name__ == "__main__":
    unittest.main(verbosity=2)
