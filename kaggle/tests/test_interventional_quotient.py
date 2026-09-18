from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.interventional_quotient import PartialInterventionalQuotient


class InterventionalQuotientContracts(unittest.TestCase):
    def q(self):
        return PartialInterventionalQuotient()

    def add(self, q, name, protected=("NOT_FINISHED",), legal=(3, 4)):
        q.observe_node(name, protected=protected, legal_actions=legal)

    def test_matching_observed_consequences_may_share_class(self):
        q = self.q()
        for name in ("a", "b", "c", "d"):
            self.add(q, name)
        q.observe_transition("a", 3, "c", outcome=("CONTINUE", 0))
        q.observe_transition("b", 3, "d", outcome=("CONTINUE", 0))
        parts = q.partitions(max_depth=2)
        self.assertEqual(parts[1]["a"], parts[1]["b"])
        stats = q.evidence_stats(parts[1])
        self.assertGreaterEqual(stats["supported_merged_pairs"], 1)
        self.assertEqual(stats["contradictory_merged_pairs"], 0)

    def test_separator_outcome_splits_immediately(self):
        q = self.q()
        for name in ("a", "b", "c", "d"):
            self.add(q, name)
        q.observe_transition("a", 3, "c", outcome=("CONTINUE", 0))
        q.observe_transition("b", 3, "d", outcome=("LEVEL_INCREMENT", 1))
        parts = q.partitions(max_depth=1)
        self.assertNotEqual(parts[1]["a"], parts[1]["b"])

    def test_untried_action_remains_unknown_not_equivalent_evidence(self):
        q = self.q()
        for name in ("a", "b", "c"):
            self.add(q, name)
        q.observe_transition("a", 3, "c", outcome=("CONTINUE", 0))
        parts = q.partitions(max_depth=1)
        self.assertNotEqual(parts[1]["a"], parts[1]["b"])
        stats = q.evidence_stats(parts[0])
        self.assertGreater(stats["unsupported_or_partial_pairs"], 0)

    def test_deeper_separator_propagates_back_through_continuation(self):
        q = self.q()
        for name in ("a", "b", "c", "d", "e", "f"):
            self.add(q, name)
        q.observe_transition("a", 3, "c", outcome=("CONTINUE", 0))
        q.observe_transition("b", 3, "d", outcome=("CONTINUE", 0))
        q.observe_transition("c", 4, "e", outcome=("CONTINUE", 0))
        q.observe_transition("d", 4, "f", outcome=("LEVEL_INCREMENT", 1))
        parts = q.partitions(max_depth=3)
        self.assertEqual(parts[1]["a"], parts[1]["b"])
        self.assertNotEqual(parts[1]["c"], parts[1]["d"])
        self.assertNotEqual(parts[2]["a"], parts[2]["b"])

    def test_conflicting_raw_contract_is_rejected(self):
        q = self.q()
        self.add(q, "a")
        with self.assertRaises(ValueError):
            q.observe_node(
                "a",
                protected=("GAME_OVER",),
                legal_actions=(3, 4),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
