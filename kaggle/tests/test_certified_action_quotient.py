from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.certified_action_quotient import (
    CERTIFIED_STATES,
    REPRESENTATIVES,
    CertifiedActionQuotient,
)


class CertifiedActionQuotientContracts(unittest.TestCase):
    def test_exact_scope_and_class_count(self):
        q = CertifiedActionQuotient()
        self.assertEqual(q.state_count, 10)
        self.assertEqual(q.representative_count, 10)
        self.assertEqual(len(CERTIFIED_STATES), 10)
        self.assertEqual(len(REPRESENTATIVES), 10)

    def test_unknown_state_preserves_every_action(self):
        q = CertifiedActionQuotient()
        self.assertTrue(q.keep("f" * 64, (6, 31, 63)))
        self.assertTrue(q.keep("f" * 64, (6, 6, 4)))

    def test_certified_state_keeps_representatives_and_non_coordinate_actions(self):
        q = CertifiedActionQuotient()
        state = next(iter(CERTIFIED_STATES))
        self.assertTrue(q.active(state))
        for action in REPRESENTATIVES:
            self.assertTrue(q.keep(state, action))
        self.assertTrue(q.keep(state, (3, None, None)))

    def test_nonrepresentative_coordinate_is_removed_only_in_scope(self):
        q = CertifiedActionQuotient()
        state = next(iter(CERTIFIED_STATES))
        self.assertFalse(q.keep(state, (6, 31, 63)))
        self.assertFalse(q.keep(state, (6, 40, 12)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
