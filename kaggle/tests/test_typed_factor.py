from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.typed_factor import BorderCompositionFactor


def bar(active: int, *, width: int = 16, height: int = 12, obstacle: bool = False):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[-1][x] = 12 if x < active else 11
    if obstacle:
        grid[-1][7] = 7
    return tuple(tuple(row) for row in grid)


def moving_world(x: int, *, width: int = 16, height: int = 12):
    grid = [[4 for _ in range(width)] for _ in range(height)]
    grid[height // 2][x] = 7
    return tuple(tuple(row) for row in grid)


class BorderCompositionFactorContracts(unittest.TestCase):
    def test_learns_composition_not_geometry(self):
        f = BorderCompositionFactor(
            activation_transitions=8,
            history_limit=32,
            min_changes=4,
            min_action_classes=2,
            min_projection_compression=1.5,
        )
        frames = [bar(16-i) for i in range(10)]
        actions = [(3,None,None),(4,None,None)] * 5
        for i,(before,after) in enumerate(zip(frames,frames[1:])):
            f.observe(0,before,after,actions[i])

        self.assertTrue(f.active(0,12,16))
        self.assertEqual(f.side(0,12,16),"bottom")
        self.assertIn(11,f.palette(0,12,16))
        self.assertIn(12,f.palette(0,12,16))
        self.assertEqual(f.world_digest(0,bar(9)),f.world_digest(0,bar(6)))
        self.assertNotEqual(f.scalar_signature(0,bar(9)),f.scalar_signature(0,bar(6)))

    def test_nonpalette_world_detail_survives_projection(self):
        f = BorderCompositionFactor(
            activation_transitions=8,
            history_limit=32,
            min_changes=4,
            min_action_classes=2,
            min_projection_compression=1.5,
        )
        frames = [bar(16-i) for i in range(10)]
        actions = [(3,None,None),(4,None,None)] * 5
        for i,(before,after) in enumerate(zip(frames,frames[1:])):
            f.observe(0,before,after,actions[i])
        self.assertTrue(f.active(0,12,16))
        self.assertNotEqual(
            f.world_digest(0,bar(8,obstacle=False)),
            f.world_digest(0,bar(8,obstacle=True)),
        )

    def test_interior_motion_never_qualifies_as_border_composition(self):
        f = BorderCompositionFactor(
            activation_transitions=8,
            history_limit=32,
            min_changes=4,
            min_action_classes=2,
            min_projection_compression=1.5,
        )
        frames=[moving_world(x) for x in range(1,11)]
        actions=[(3,None,None),(4,None,None)]*5
        for i,(before,after) in enumerate(zip(frames,frames[1:])):
            f.observe(0,before,after,actions[i])
        self.assertFalse(f.active(0,12,16))

    def test_scalar_transition_is_retained_separately(self):
        f = BorderCompositionFactor(
            activation_transitions=8,
            history_limit=32,
            min_changes=4,
            min_action_classes=2,
            min_projection_compression=1.5,
        )
        frames = [bar(16-i) for i in range(10)]
        actions = [(3,None,None),(4,None,None)] * 5
        for i,(before,after) in enumerate(zip(frames,frames[1:])):
            f.observe(0,before,after,actions[i])
        before,after=bar(8),bar(7)
        f.note_transition(
            "w0",(3,None,None),"w1",
            f.scalar_signature(0,before),
            f.scalar_signature(0,after),
        )
        rows=f.transitions()
        self.assertEqual(len(rows),1)
        self.assertNotEqual(rows[0]["before"],rows[0]["after"])


if __name__=="__main__":
    unittest.main(verbosity=2)
