from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.contextual_quotient import ContextualQuotient
from metalogic_arc3.runtime import normalize_frame


def grid(world: int, resource: int, width=8, height=8):
    rows = [[0 for _ in range(width)] for _ in range(height)]
    rows[2][1 if world == 0 else 5] = 7
    for x in range(width):
        rows[-1][x] = 12 if x < resource else 11
    return tuple(tuple(row) for row in rows)


def frame(g):
    return {
        "frame": [g],
        "levels_completed": 0,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


class ContextualQuotientControllerContracts(unittest.TestCase):
    def _certified(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.contextual_quotient = ContextualQuotient(
            activation_transitions=8,
            min_compression=2.0,
            min_repeated_events=6,
            depths=(1,),
        )
        world = 0
        resource = 8
        for _ in range(8):
            before = grid(world, resource)
            action = (3 if world == 0 else 4, None, None)
            world = 1 - world
            resource -= 1
            after = grid(world, resource)
            c.contextual_quotient.observe(
                0, before, after, action, "CONTINUE"
            )
        return c

    def test_exact_memory_context_is_never_quotiented(self):
        c = self._certified()
        obs = normalize_frame(frame(grid(0, 3)))
        self.assertEqual(c._memory_context(obs)[-1], obs.frame_digest)

    def test_only_learned_consequence_context_uses_certified_projection(self):
        c = self._certified()
        left = normalize_frame(frame(grid(0, 8)))
        right = normalize_frame(frame(grid(0, 3)))
        self.assertEqual(
            c._consequence_context(left, grid(0, 8)),
            c._consequence_context(right, grid(0, 3)),
        )
        self.assertTrue(c._consequence_context(left, grid(0, 8)).startswith("cq:"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
