from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.resource_factor import ResourceFactor
from metalogic_arc3.runtime import normalize_frame


def frame(grid, *, level=0, actions=(3, 4), state="NOT_FINISHED"):
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": state,
        "available_actions": list(actions),
    }


def bar(active: int, width=16, height=12):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[-1][x] = 12 if x < active else 11
    return tuple(tuple(row) for row in grid)


class ResourceFactorControllerContracts(unittest.TestCase):
    def test_memory_context_remains_exact_after_factor_activation(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.resource_factor = ResourceFactor(activation_transitions=2, min_positions=1)
        c.resource_factor.observe(0, bar(16), bar(15))
        c.resource_factor.observe(0, bar(15), bar(14))
        obs = normalize_frame(frame(bar(13)))
        self.assertTrue(c.resource_factor.active(0, 12, 16))
        self.assertEqual(c._memory_context(obs)[-1], obs.frame_digest)
        self.assertTrue(c._consequence_context(obs, bar(13)).startswith("w:"))

    def test_factorized_world_context_ignores_resource_but_ledger_does_not(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.resource_factor = ResourceFactor(activation_transitions=2, min_positions=1)
        c.resource_factor.observe(0, bar(16), bar(15))
        c.resource_factor.observe(0, bar(15), bar(14))
        left = normalize_frame(frame(bar(13)))
        right = normalize_frame(frame(bar(10)))
        self.assertEqual(
            c._consequence_context(left, bar(13)),
            c._consequence_context(right, bar(10)),
        )
        self.assertNotEqual(
            c._resource_signature(left, bar(13)),
            c._resource_signature(right, bar(10)),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
