from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import ActionToken, normalize_frame


def frame():
    return {
        "frame": [[[0, 0], [0, 0]]],
        "levels_completed": 0,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


class QuotientFrontierContracts(unittest.TestCase):
    def _controller(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c._grid = ((0, 0), (0, 0))
        c._primary = (ActionToken(3), ActionToken(4))
        c._decision_tick = 1
        return c

    def test_local_untried_world_action_outranks_affordance(self):
        c = self._controller()
        c._consequence_context = lambda obs, grid: "w:s0"
        c.effects.note_attempt = None if False else getattr(c.effects, "note_attempt", None)

        # Action 3 already has repeated controllability evidence and one world-state
        # attempt. Action 4 is still untried in this factored world state.
        c.effects.record("w:s0", (3, None, None), "w:s1", "primitive:3", 1, "h", False)
        for i in range(4):
            c.affordances.record(
                f"a{i}", (3, None, None), "primitive:3",
                (1, 1, 1, 0, 0, 1), directness=1.0,
            )

        token = c._select_probe(normalize_frame(frame()), c._primary)
        self.assertEqual(token.action_id, 4)
        self.assertEqual(token.source, "quotient_frontier")

    def test_known_path_to_remote_untried_world_action_outranks_affordance(self):
        c = self._controller()
        c._consequence_context = lambda obs, grid: "w:s0"
        a3, a4 = (3, None, None), (4, None, None)

        # Current world state is locally exhausted.
        c.effects.record("w:s0", a3, "w:s1", "primitive:3", 1, "h0", False)
        c.effects.record("w:s0", a4, "w:s0", "primitive:4", 0, "h1", False)
        c.effects.note_catalog("w:s0", (a3, a4))
        c.effects.note_catalog("w:s1", (a3, a4))
        # Mark both current actions attempted, but none at s1.
        self.assertGreater(c.effects.attempts("w:s0", a3), 0)
        self.assertGreater(c.effects.attempts("w:s0", a4), 0)
        for i in range(4):
            c.affordances.record(
                f"b{i}", a4, "primitive:4",
                (1, 1, 1, 0, 0, 1), directness=1.0,
            )

        token = c._select_probe(normalize_frame(frame()), c._primary)
        self.assertEqual((token.action_id, token.x, token.y), a3)
        self.assertEqual(token.source, "quotient_frontier")

    def test_raw_context_keeps_existing_affordance_priority(self):
        c = self._controller()
        c._consequence_context = lambda obs, grid: "raw:s0"
        for i in range(4):
            c.affordances.record(
                f"a{i}", (3, None, None), "primitive:3",
                (1, 1, 1, 0, 0, 1), directness=1.0,
            )
        token = c._select_probe(normalize_frame(frame()), c._primary)
        self.assertEqual(token.action_id, 3)
        self.assertEqual(token.source, "affordance")


if __name__ == "__main__":
    unittest.main(verbosity=2)
