from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.resource_dominance import ResourceDominanceLedger


class ResourceDominanceLedgerContracts(unittest.TestCase):
    def test_lower_remaining_resource_is_dominated_for_decreasing_scalar(self):
        ledger = ResourceDominanceLedger()
        self.assertFalse(ledger.observe("w", (11, 80, -1))["dominated"])
        row = ledger.observe("w", (11, 40, -1))
        self.assertTrue(row["dominated"])
        self.assertEqual(row["best_quality"], 80)

    def test_increasing_consumed_scalar_prefers_lower_value(self):
        ledger = ResourceDominanceLedger()
        self.assertFalse(ledger.observe("w", (7, 10, 1))["dominated"])
        self.assertFalse(ledger.observe("w", (7, 5, 1))["dominated"])
        self.assertTrue(ledger.observe("w", (7, 8, 1))["dominated"])

    def test_worlds_are_compared_independently(self):
        ledger = ResourceDominanceLedger()
        ledger.observe("a", (11, 80, -1))
        self.assertFalse(ledger.observe("b", (11, 10, -1))["dominated"])
        self.assertEqual(ledger.best_quality("a"), 80)
        self.assertEqual(ledger.best_quality("b"), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
