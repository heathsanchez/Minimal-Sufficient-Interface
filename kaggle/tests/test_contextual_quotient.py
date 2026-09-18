from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.contextual_quotient import ContextualQuotient


def grid(world: int, nuisance: int, *, h=6, w=6):
    rows = [[0 for _ in range(w)] for _ in range(h)]
    rows[2][2] = world
    # Two-column right-side nuisance display spanning separated rows, so a
    # horizontal crop cannot accidentally satisfy the same contract.
    for y in (0, 2, 4):
        rows[y][w-2] = nuisance
        rows[y][w-1] = nuisance + 20
    return tuple(tuple(row) for row in rows)


P0 = (0, "NOT_FINISHED", (3, 4))
P1 = (1, "NOT_FINISHED", (3, 4))


class ContextualQuotientContracts(unittest.TestCase):
    def _safe_trace(self):
        q = ContextualQuotient(
            activation_transitions=8,
            evaluation_interval=4,
            min_compression=2.0,
            min_repeated_events=6,
            min_boundary_events=0,
            candidate_depths=(1, 2),
        )
        current = grid(1, 0)
        for i in range(8):
            action = (3, None, None) if i % 2 == 0 else (4, None, None)
            target_world = 2 if i % 2 == 0 else 1
            nxt = grid(target_world, i + 1)
            q.observe(current, action, nxt, P0, P0)
            current = nxt
        return q

    def test_dormant_before_evidence_horizon(self):
        q = ContextualQuotient(
            activation_transitions=8,
            evaluation_interval=4,
            min_compression=2.0,
            min_repeated_events=6,
            candidate_depths=(1, 2),
        )
        current = grid(1, 0)
        for i in range(7):
            action = (3, None, None) if i % 2 == 0 else (4, None, None)
            target_world = 2 if i % 2 == 0 else 1
            nxt = grid(target_world, i + 1)
            q.observe(current, action, nxt, P0, P0)
            current = nxt
        self.assertFalse(q.active(6, 6))

    def test_admits_compressive_deterministic_protected_projection(self):
        q = self._safe_trace()
        cert = q.certificate(6, 6)
        self.assertIsNotNone(cert)
        self.assertEqual(cert["side"], "right")
        self.assertEqual(cert["depth"], 2)
        self.assertEqual(cert["conflicting_events"], 0)
        self.assertEqual(cert["outcome_conflicts"], 0)
        self.assertGreaterEqual(cert["compression"], 2.0)
        self.assertEqual(
            q.project(grid(1, 100)),
            q.project(grid(1, 999)),
        )
        self.assertNotEqual(
            q.project(grid(1, 100)),
            q.project(grid(2, 100)),
        )

    def test_rejects_projection_with_nondeterministic_successor(self):
        q = ContextualQuotient(
            activation_transitions=8,
            evaluation_interval=4,
            min_compression=1.1,
            min_repeated_events=2,
            min_boundary_events=0,
            candidate_depths=(2,),
        )
        source = grid(1, 0)
        # Same projected source/action, two different projected targets.
        rows = [
            (source, (3, None, None), grid(2, 1)),
            (grid(1, 2), (3, None, None), grid(3, 3)),
        ] * 4
        for before, action, after in rows:
            q.observe(before, action, after, P0, P0)
        self.assertFalse(q.active(6, 6))

    def test_rejects_projection_that_merges_protected_levels(self):
        q = ContextualQuotient(
            activation_transitions=8,
            evaluation_interval=4,
            min_compression=1.1,
            min_repeated_events=2,
            min_boundary_events=0,
            candidate_depths=(2,),
        )
        current = grid(1, 0)
        for i in range(8):
            protected = P0 if i < 4 else P1
            nxt = grid(2 if i % 2 == 0 else 1, i + 1)
            q.observe(current, (3 if i % 2 == 0 else 4, None, None),
                      nxt, protected, protected)
            current = nxt
        self.assertFalse(q.active(6, 6))

    def test_certificate_is_observed_contract_not_universal_claim(self):
        q = self._safe_trace()
        cert = q.certificate(6, 6)
        self.assertEqual(cert["status"], "BOUNDED_EMPIRICAL_SUBSTITUTION")
        self.assertEqual(cert["sample_transitions"], 8)

    def test_default_admission_waits_for_protected_boundary(self):
        q = ContextualQuotient(
            activation_transitions=8,
            evaluation_interval=1,
            min_compression=2.0,
            min_repeated_events=6,
            candidate_depths=(1, 2),
        )
        current = grid(1, 0)
        for i in range(8):
            action = (3, None, None) if i % 2 == 0 else (4, None, None)
            target_world = 2 if i % 2 == 0 else 1
            nxt = grid(target_world, i + 1)
            q.observe(current, action, nxt, P0, P0)
            current = nxt
        self.assertFalse(q.active(6, 6))

        terminal = (0, "GAME_OVER", (3, 4))
        target = grid(9, 99)
        q.observe(current, (3, None, None), target, P0, terminal)
        cert = q.certificate(6, 6)
        self.assertIsNotNone(cert)
        self.assertEqual(cert["boundary_events"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
