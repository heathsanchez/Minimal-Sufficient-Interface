from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.memory_controller import MemoryGraphController


def frame(value: int = 0, *, level: int = 0, actions=(3, 4)):
    grid = [[value for _ in range(4)] for _ in range(4)]
    return {
        "frame": [grid],
        "levels_completed": level,
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

        second_episode = [c.observe_and_choose(start).action_id for _ in range(4)]
        self.assertEqual(second_episode, [3, 4, 3, 3])

    def test_progress_program_becomes_prospective_option_and_repeats_without_becoming_a_rule(self):
        c = MemoryGraphController((3, 4), archived_capabilities=(), max_transfer_depth=8)
        start = frame(level=0)

        # Generic exploration witnesses [3,4] as a level-incrementing suffix.
        first = c.observe_and_choose(start)
        second = c.observe_and_choose(start)
        self.assertEqual([first.action_id, second.action_id], [3, 4])

        # The next public observation proves progress.  The successful source
        # suffix is promoted, then proposed at the new level as a hypothesis.
        transfer1 = c.observe_and_choose(frame(level=1))
        self.assertEqual(c.memory.capability_count, 1)
        self.assertEqual((transfer1.action_id, transfer1.source), (3, "transfer"))

        transfer2 = c.observe_and_choose(frame(level=1))
        self.assertEqual((transfer2.action_id, transfer2.source), (4, "transfer"))

        # No progress or terminal consequence has occurred, so generic program
        # composition repeats the witnessed option rather than exploding into
        # primitive depth-first enumeration immediately.
        transfer3 = c.observe_and_choose(frame(level=1))
        transfer4 = c.observe_and_choose(frame(level=1))
        self.assertEqual(
            [(transfer3.action_id, transfer3.source), (transfer4.action_id, transfer4.source)],
            [(3, "transfer"), (4, "transfer")],
        )

    def test_refuted_transfer_leaf_diverges_only_at_closed_child(self):
        c = MemoryGraphController((3, 4), archived_capabilities=(), max_transfer_depth=8)
        start = frame(level=0)

        # Witness [3,4] once.
        c.observe_and_choose(start)
        c.observe_and_choose(start)
        c.observe_and_choose(frame(level=1))
        c.observe_and_choose(frame(level=1))
        c.observe_and_choose(frame(level=1))
        c.observe_and_choose(frame(level=1))
        # The level-1 hypothesis was [3,4,3,4] and failed.
        c.record_terminal_failure("GAME_OVER")
        c.reset_episode()

        # Reacquire level 1 through the exact retained source capability.
        replay1 = c.observe_and_choose(start)
        replay2 = c.observe_and_choose(start)
        self.assertEqual([replay1.source, replay2.source], ["retained", "retained"])

        # Once progress is observed, transfer replays the failed hypothesis up
        # to its exact leaf and the trie forces the sibling only there.
        attempt = [c.observe_and_choose(frame(level=1)) for _ in range(4)]
        self.assertEqual([t.action_id for t in attempt], [3, 4, 3, 3])
        self.assertEqual([t.source for t in attempt[:3]], ["transfer"] * 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
