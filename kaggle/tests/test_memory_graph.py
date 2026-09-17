from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.memory_graph import ArcMemoryGraph


class ArcMemoryGraphContracts(unittest.TestCase):
    def test_terminal_leaf_does_not_close_ancestor_until_all_legal_children_close(self):
        mg = ArcMemoryGraph()
        context = (0, "NOT_FINISHED", (3, 4), 64, 64, "start")
        a3 = (3, None, None)
        a4 = (4, None, None)
        legal = (a3, a4)
        failed = (a3, a4, a3, a4)

        for prefix in ((), (a3,), (a3, a4), (a3, a4, a3)):
            mg.note_legal(context, prefix, legal)
        mg.add_refuted(context, failed, consequence="GAME_OVER")

        self.assertTrue(mg.is_closed(context, failed))
        self.assertFalse(mg.is_closed(context, (a3, a4, a3)))
        self.assertEqual(mg.forbidden_next(context, ()), set())
        self.assertEqual(mg.forbidden_next(context, (a3,)), set())
        self.assertEqual(mg.forbidden_next(context, (a3, a4, a3)), {a4})

        sibling = (a3, a4, a3, a3)
        mg.add_refuted(context, sibling, consequence="GAME_OVER")
        self.assertTrue(mg.is_closed(context, (a3, a4, a3)))
        self.assertEqual(mg.forbidden_next(context, (a3, a4)), {a3})
        self.assertFalse(mg.is_closed(context, (a3, a4)))

    def test_verified_capability_is_source_scoped_restartable_and_available_as_hypothesis(self):
        mg = ArcMemoryGraph()
        source = (0, "NOT_FINISHED", (3, 4), 64, 64, "level0")
        a3 = (3, None, None)
        program = (a3, a3, a3, a3)

        mg.add_capability(source, program, source_level=0, target_level=1)
        mg.add_capability(source, program, source_level=0, target_level=1)

        self.assertEqual(mg.capability_count, 1)
        self.assertEqual(mg.capability_programs(), (program,))

        text = mg.text()
        self.assertTrue(text.startswith("MG-ARC4\n"))
        restarted = ArcMemoryGraph.parse(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest(), mg.digest())
        self.assertEqual(restarted.capability_programs(), (program,))

    def test_refutation_trie_is_canonical_restartable_and_preserves_attempts(self):
        mg = ArcMemoryGraph()
        context = (0, "NOT_FINISHED", (3, 4), 64, 64, "start")
        a3 = (3, None, None)
        a4 = (4, None, None)
        legal = (a3, a4)

        mg.note_attempt(context, a3)
        mg.note_attempt(context, a4)
        mg.note_legal(context, (), legal)
        mg.note_legal(context, (a3,), legal)
        mg.add_refuted(context, (a3, a4), consequence="GAME_OVER")
        mg.add_refuted(context, (a3, a4), consequence="GAME_OVER")

        self.assertEqual(mg.attempt_count(context, a3), 1)
        self.assertEqual(mg.attempt_count(context, a4), 1)
        self.assertEqual(mg.refuted_count, 1)
        self.assertEqual(mg.forbidden_next(context, ()), set())
        self.assertEqual(mg.forbidden_next(context, (a3,)), {a4})

        text = mg.text()
        self.assertTrue(text.startswith("MG-ARC4\n"))
        restarted = ArcMemoryGraph.parse(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest(), mg.digest())
        self.assertEqual(restarted.forbidden_next(context, ()), set())
        self.assertEqual(restarted.forbidden_next(context, (a3,)), {a4})


if __name__ == "__main__":
    unittest.main(verbosity=2)
