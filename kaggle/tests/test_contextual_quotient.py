from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.contextual_quotient import ContextualQuotient


def grid(world: int, resource: int, *, width: int = 8, height: int = 8):
    rows = [[0 for _ in range(width)] for _ in range(height)]
    rows[2][1 if world == 0 else 5] = 7
    for x in range(width):
        rows[-1][x] = 12 if x < resource else 11
    return tuple(tuple(row) for row in rows)


class ContextualQuotientContracts(unittest.TestCase):
    def test_certifies_recurrent_projection_with_deterministic_transitions(self):
        q = ContextualQuotient(
            activation_transitions=8,
            min_compression=2.0,
            min_repeated_events=6,
            depths=(1,),
        )
        world = 0
        resource = 8
        for i in range(8):
            before = grid(world, resource)
            action = (3 if world == 0 else 4, None, None)
            world = 1 - world
            resource -= 1
            after = grid(world, resource)
            q.observe(0, before, after, action, "CONTINUE")

        candidate = q.active_candidate(0, 8, 8)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["side"], "bottom")
        self.assertEqual(candidate["depth"], 1)
        self.assertEqual(candidate["transition_conflicts"], 0)
        self.assertEqual(candidate["outcome_conflicts"], 0)
        self.assertGreaterEqual(candidate["compression"], 2.0)

        self.assertEqual(
            q.context(0, grid(0, 8), "exact-a"),
            q.context(0, grid(0, 3), "exact-b"),
        )
        self.assertNotEqual(
            q.context(0, grid(0, 8), "exact-a"),
            q.context(0, grid(1, 8), "exact-c"),
        )

    def test_transition_conflict_blocks_certification(self):
        q = ContextualQuotient(
            activation_transitions=8,
            min_compression=1.1,
            min_repeated_events=2,
            depths=(1,),
        )
        # Same projected state + same action leads to two projected successors.
        for resource, target_world in [(8, 1), (7, 0), (6, 1), (5, 0)] * 2:
            q.observe(
                0,
                grid(0, resource),
                grid(target_world, max(0, resource - 1)),
                (3, None, None),
                "CONTINUE",
            )
        self.assertIsNone(q.active_candidate(0, 8, 8))

    def test_protected_outcome_conflict_blocks_certification(self):
        q = ContextualQuotient(
            activation_transitions=8,
            min_compression=1.1,
            min_repeated_events=2,
            depths=(1,),
        )
        outcomes = ["CONTINUE"] * 7 + ["GAME_OVER"]
        for i, outcome in enumerate(outcomes):
            resource = 8 - i
            q.observe(
                0,
                grid(0, max(1, resource)),
                grid(1, max(0, resource - 1)),
                (3, None, None),
                outcome,
            )
        self.assertIsNone(q.active_candidate(0, 8, 8))

    def test_no_activation_before_evidence_horizon(self):
        q = ContextualQuotient(
            activation_transitions=8,
            min_compression=1.1,
            min_repeated_events=2,
            depths=(1,),
        )
        for resource in range(8, 4, -1):
            q.observe(
                0,
                grid(0, resource),
                grid(1, resource - 1),
                (3, None, None),
                "CONTINUE",
            )
        self.assertIsNone(q.active_candidate(0, 8, 8))

    def test_projection_search_is_deferred_until_evidence_horizon(self):
        q = ContextualQuotient(
            activation_transitions=8,
            min_compression=1.1,
            min_repeated_events=2,
            depths=(1,),
        )
        for resource in range(8, 2, -1):
            q.observe(
                0,
                grid(0, resource),
                grid(1, resource - 1),
                (3, None, None),
                "CONTINUE",
            )
        self.assertEqual(q.evaluation_rounds, 0)
        q.observe(
            0,
            grid(0, 2),
            grid(1, 1),
            (3, None, None),
            "CONTINUE",
        )
        q.observe(
            0,
            grid(1, 1),
            grid(0, 0),
            (4, None, None),
            "CONTINUE",
        )
        self.assertEqual(q.evaluation_rounds, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
