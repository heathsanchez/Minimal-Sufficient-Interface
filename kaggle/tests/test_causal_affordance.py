from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.causal_affordance import (
    AffordanceMemory,
    effect_signature,
)


class CausalAffordanceContracts(unittest.TestCase):
    def test_parameterized_action_prefers_spatially_aligned_effect(self):
        before = (
            (0, 0, 0, 0, 0),
            (0, 1, 1, 0, 0),
            (0, 1, 1, 0, 0),
            (0, 0, 0, 2, 2),
            (0, 0, 0, 2, 2),
        )
        near = tuple(
            tuple(3 if (x, y) == (1, 1) else v for x, v in enumerate(row))
            for y, row in enumerate(before)
        )
        far = tuple(
            tuple(3 if (x, y) == (4, 4) else v for x, v in enumerate(row))
            for y, row in enumerate(before)
        )
        aligned = effect_signature(before, near, (6, 1, 1))
        exogenous = effect_signature(before, far, (6, 1, 1))
        self.assertGreater(aligned.directness, exogenous.directness)

    def test_repeated_same_effect_across_coordinates_collapses_parameter_equivalence(self):
        mem = AffordanceMemory(limit=64)
        sig = (1, 1, 1, 0, 0, 1)
        mem.record("ctx-a", (6, 1, 1), "shape-x", sig, directness=0.0)
        mem.record("ctx-b", (6, 9, 9), "shape-x", sig, directness=0.0)
        self.assertTrue(
            mem.parameter_equivalent("shape-x", (6, 1, 1), (6, 9, 9))
        )

    def test_controllable_descriptor_outranks_novel_but_unaligned_change(self):
        mem = AffordanceMemory(limit=64)
        for i in range(3):
            mem.record(
                f"near-{i}",
                (6, 4, 4),
                "near",
                (1, 1, 1, 0, 0, 1),
                directness=1.0,
            )
        for i in range(3):
            mem.record(
                f"far-{i}",
                (6, 20 + i, 20),
                "far",
                (20, 8, 8, 3, 3, 5),
                directness=0.0,
            )
        self.assertGreater(mem.affordance_score("near"), mem.affordance_score("far"))

    def test_primitive_reversible_effect_is_recognized_as_controllable(self):
        mem = AffordanceMemory(limit=64)
        mem.record(
            "a",
            (1, None, None),
            "primitive:1",
            (4, 2, 1, 1, 0, 2),
            directness=1.0,
            target="b",
        )
        mem.record(
            "b",
            (2, None, None),
            "primitive:2",
            (4, 2, 1, -1, 0, 2),
            directness=1.0,
            target="a",
        )
        self.assertTrue(mem.has_reversible_pair("a", (1, None, None), "b"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
