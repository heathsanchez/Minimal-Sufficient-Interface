from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.memory_graph import ArcMemoryGraph


class ArcMemoryGraphContracts(unittest.TestCase):
    def test_refuted_program_is_canonical_restartable_and_guides_divergence(self):
        mg = ArcMemoryGraph()
        context = (0, "NOT_FINISHED", (3, 4), 64, 64, "start")
        a3 = (3, None, None)
        a4 = (4, None, None)
        program = (a3, a4, a3, a4)

        mg.note_attempt(context, a3)
        mg.note_attempt(context, a4)
        mg.add_refuted(context, program, consequence="GAME_OVER")
        mg.add_refuted(context, program, consequence="GAME_OVER")

        self.assertEqual(mg.attempt_count(context, a3), 1)
        self.assertEqual(mg.attempt_count(context, a4), 1)
        self.assertEqual(mg.refuted_count, 1)
        self.assertEqual(mg.forbidden_next(context, ()), {a3})
        self.assertEqual(mg.forbidden_next(context, (a3,)), {a4})
        self.assertEqual(mg.forbidden_next(context, (a4,)), set())

        text = mg.text()
        self.assertTrue(text.startswith("MG-ARC1\n"))
        restarted = ArcMemoryGraph.parse(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest(), mg.digest())
        self.assertEqual(restarted.forbidden_next(context, ()), {a3})


if __name__ == "__main__":
    unittest.main(verbosity=2)
