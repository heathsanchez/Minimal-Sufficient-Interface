from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.recurrence_factor import RecurrenceFactor
from metalogic_arc3.runtime import ActionToken, normalize_frame


def raster(resource: int, world: int, width=64, height=12):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    grid[2][world % 16] = 9
    for x in range(width):
        grid[-1][x] = 12 if x < resource else 11
    return tuple(tuple(row) for row in grid)


def frame(grid, level=0):
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


class RecurrenceFactorControllerContracts(unittest.TestCase):
    def _activated(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.recurrence_factor = RecurrenceFactor(
            activation_frames=8,
            min_compression=4.0,
            min_scalar_changes=4,
            min_sign_consistency=0.75,
            min_action_classes=2,
            candidate_depths=(1,),
        )
        frames = [raster(16-i, i % 2) for i in range(9)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            c.recurrence_factor.observe(
                0, before, after, (3 if i % 2 == 0 else 4, None, None)
            )
        self.assertTrue(c.recurrence_factor.active(0, 12, 64))
        return c

    def test_exact_memory_context_is_never_replaced(self):
        c = self._activated()
        g = raster(8, 1)
        obs = normalize_frame(frame(g))
        self.assertEqual(c._memory_context(obs)[-1], obs.frame_digest)

    def test_consequence_context_uses_world_factor_after_admission(self):
        c = self._activated()
        left = raster(8, 1)
        right = raster(4, 1)
        left_obs = normalize_frame(frame(left))
        right_obs = normalize_frame(frame(right))
        self.assertEqual(
            c._consequence_context(left_obs, left),
            c._consequence_context(right_obs, right),
        )
        self.assertTrue(c._consequence_context(left_obs, left).startswith("w:"))

    def test_recurrent_world_frontier_outranks_generic_affordance(self):
        c = self._activated()
        g = raster(8, 1)
        obs = normalize_frame(frame(g))
        c._grid = g
        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 1

        context = c._consequence_context(obs, g)
        target = "w:target"
        c.effects.note_catalog(context, ((3, None, None), (4, None, None)))
        c.effects.record(
            context, (3, None, None), target, "primitive:3", 1, "h", False
        )
        c.effects.note_catalog(target, ((4, None, None),))

        for i in range(3):
            c.affordances.record(
                f"a{i}",
                (4, None, None),
                "primitive:4",
                (1, 1, 1, 0, 0, 1),
                directness=1.0,
            )

        selected = c._select_probe(obs, catalog)
        self.assertEqual(selected.action_id, 3)
        self.assertEqual(selected.source, "consequence_frontier")

    def test_removed_factor_is_retained_separately(self):
        c = self._activated()
        left = raster(8, 1)
        right = raster(4, 1)
        left_obs = normalize_frame(frame(left))
        right_obs = normalize_frame(frame(right))
        self.assertNotEqual(
            c._factor_signature(left_obs, left),
            c._factor_signature(right_obs, right),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
