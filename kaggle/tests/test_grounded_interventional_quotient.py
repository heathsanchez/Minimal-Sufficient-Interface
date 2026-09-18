from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.grounded_interventional_quotient import (
    GroundedInterventionalQuotient,
)


class GroundedInterventionalQuotientContracts(unittest.TestCase):
    def q(self):
        return GroundedInterventionalQuotient()

    def add(self, q, name, legal=((6, 1, 1), (6, 2, 2))):
        q.observe_node(
            name,
            protected=("NOT_FINISHED", 0),
            legal_actions=legal,
        )

    def test_coordinate_variants_are_distinct_interventions(self):
        q = self.q()
        for name in ("a", "b", "c", "d"):
            self.add(q, name)
        q.observe_transition("a", (6, 1, 1), "c", outcome=("CONTINUE", 0))
        q.observe_transition("a", (6, 2, 2), "d", outcome=("CONTINUE", 0))
        self.assertEqual(len(q._observed_actions("a")), 2)

    def test_parameter_separator_splits_states(self):
        q = self.q()
        for name in ("a", "b", "c", "d"):
            self.add(q, name)
        q.observe_transition("a", (6, 1, 1), "c", outcome=("CONTINUE", 0))
        q.observe_transition("b", (6, 1, 1), "d", outcome=("LEVEL_INCREMENT", 1))
        parts = q.partitions(max_depth=1)
        self.assertNotEqual(parts[1]["a"], parts[1]["b"])

    def test_untried_grounded_action_is_not_full_equivalence_evidence(self):
        q = self.q()
        for name in ("a", "b", "c"):
            self.add(q, name)
        q.observe_transition("a", (6, 1, 1), "c", outcome=("CONTINUE", 0))
        q.observe_transition("b", (6, 1, 1), "c", outcome=("CONTINUE", 0))
        parts = q.partitions(max_depth=1)
        self.assertEqual(parts[1]["a"], parts[1]["b"])
        self.assertFalse(q.fully_observed_pair("a", "b"))
        stats = q.evidence_stats(parts[1])
        self.assertGreater(stats["unsupported_or_partial_pairs"], 0)

    def test_complete_matching_contract_can_be_fully_observed(self):
        q = self.q()
        for name in ("a", "b", "c"):
            self.add(q, name)
        for source in ("a", "b"):
            q.observe_transition(source, (6, 1, 1), "c", outcome=("CONTINUE", 0))
            q.observe_transition(source, (6, 2, 2), "c", outcome=("CONTINUE", 0))
        parts = q.partitions(max_depth=2)
        self.assertEqual(parts[-1]["a"], parts[-1]["b"])
        self.assertTrue(q.fully_observed_pair("a", "b"))

    def test_different_grounded_contracts_split_at_depth_zero(self):
        q = self.q()
        q.observe_node(
            "a",
            protected=("NOT_FINISHED", 0),
            legal_actions=((6, 1, 1),),
        )
        q.observe_node(
            "b",
            protected=("NOT_FINISHED", 0),
            legal_actions=((6, 2, 2),),
        )
        parts = q.partitions(max_depth=0)
        self.assertNotEqual(parts[0]["a"], parts[0]["b"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
