from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.typed_factor import BorderCompositionFactor
from metalogic_arc3.runtime import normalize_frame


def frame(grid, *, level=0, actions=(3,4), state="NOT_FINISHED"):
    return {
        "frame":[grid],
        "levels_completed":level,
        "state":state,
        "available_actions":list(actions),
    }


def bar(active: int, width=16, height=12):
    grid=[[4 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        grid[-1][x]=12 if x<active else 11
    return tuple(tuple(row) for row in grid)


class TypedFactorControllerContracts(unittest.TestCase):
    def _controller(self):
        c=ConsequenceController((3,4),archived_capabilities=())
        c.typed_factor=BorderCompositionFactor(
            activation_transitions=2,
            history_limit=8,
            min_changes=1,
            min_action_classes=2,
            min_projection_compression=1.1,
        )
        c.typed_factor.observe(0,bar(16),bar(15),(3,None,None))
        c.typed_factor.observe(0,bar(15),bar(14),(4,None,None))
        return c

    def test_exact_memory_context_is_never_quotiented(self):
        c=self._controller()
        obs=normalize_frame(frame(bar(13)))
        self.assertTrue(c.typed_factor.active(0,12,16))
        self.assertEqual(c._memory_context(obs)[-1],obs.frame_digest)

    def test_consequence_context_uses_world_projection_and_keeps_scalar(self):
        c=self._controller()
        a=normalize_frame(frame(bar(13)))
        b=normalize_frame(frame(bar(10)))
        self.assertEqual(
            c._consequence_context(a,bar(13)),
            c._consequence_context(b,bar(10)),
        )
        self.assertNotEqual(
            c._typed_scalar(a,bar(13)),
            c._typed_scalar(b,bar(10)),
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
