from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.border_scalar import BorderScalarFactor
from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import normalize_frame


def frame(grid, *, level=0):
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


def bar(remaining, width=32, height=16):
    g = [[4 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        g[-1][x] = 12 if x < remaining else 11
    g[5][5] = 8
    return tuple(tuple(r) for r in g)


class BorderScalarControllerContracts(unittest.TestCase):
    def _activated(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.border_factor = BorderScalarFactor(
            activation_transitions=8,
            min_changes=4,
            min_action_classes=2,
            min_sign_consistency=0.75,
            min_projection_compression=1.5,
        )
        frames = [bar(max(0, 32 - (i % 9))) for i in range(10)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            c.border_factor.observe(
                0, before, after, (3 + i % 2, None, None),
                descriptor=f"primitive:{3+i%2}", history=str(i), terminal=False,
            )
        c._ensure_border_replay(0, 16, 32)
        return c

    def test_exact_memory_context_is_never_replaced(self):
        c = self._activated()
        obs = normalize_frame(frame(bar(20)))
        self.assertTrue(c.border_factor.active(0, 16, 32))
        self.assertEqual(c._memory_context(obs)[-1], obs.frame_digest)
        self.assertTrue(c._consequence_context(obs, bar(20)).startswith("w:"))

    def test_replay_populates_factorized_graph(self):
        c = self._activated()
        self.assertGreater(c.world_effects.total_observations, 0)
        self.assertGreater(len(c.world_effects.edges), 0)

    def test_scalar_remains_available_separately(self):
        c = self._activated()
        a = normalize_frame(frame(bar(20)))
        b = normalize_frame(frame(bar(10)))
        self.assertEqual(c._consequence_context(a, bar(20)),
                         c._consequence_context(b, bar(10)))
        self.assertNotEqual(c._resource_signature(a, bar(20)),
                            c._resource_signature(b, bar(10)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
