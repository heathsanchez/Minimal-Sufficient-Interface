from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.contextual_quotient import ContextualQuotient
from metalogic_arc3.runtime import normalize_frame


def grid(world: int, nuisance: int):
    rows = [[0 for _ in range(6)] for _ in range(6)]
    rows[2][2] = world
    rows[0][4] = nuisance
    rows[0][5] = nuisance + 20
    return tuple(tuple(row) for row in rows)


def frame(g, level=0):
    return {
        "frame": [g],
        "levels_completed": level,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


class ContextualQuotientControllerContracts(unittest.TestCase):
    def _controller(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.contextual_quotient = ContextualQuotient(
            activation_transitions=4,
            evaluation_interval=2,
            min_compression=1.5,
            min_repeated_events=2,
            candidate_depths=(1, 2),
        )
        return c

    def test_exact_memory_context_is_never_replaced(self):
        c = self._controller()
        current = grid(1, 0)
        for i in range(4):
            obs_before = normalize_frame(frame(current))
            target = grid(2 if i % 2 == 0 else 1, i + 1)
            obs_after = normalize_frame(frame(target))
            c.contextual_quotient.observe(
                current,
                (3 if i % 2 == 0 else 4, None, None),
                target,
                (0, "NOT_FINISHED", (3, 4)),
                (0, "NOT_FINISHED", (3, 4)),
            )
            current = target
        obs = normalize_frame(frame(current))
        self.assertTrue(c.contextual_quotient.active(6, 6))
        self.assertEqual(c._memory_context(obs)[-1], obs.frame_digest)
        self.assertTrue(c._consequence_context(obs, current).startswith("cq:"))

    def test_disabled_quotient_is_exact_mg_arc5_behavior(self):
        c = self._controller()
        c.contextual_quotient_enabled = False
        obs = normalize_frame(frame(grid(1, 99)))
        self.assertEqual(c._consequence_context(obs, grid(1, 99)), obs.evidence_sha256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
