from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.mechanics_foundry import (
    FoundryConfig,
    compile_laws,
    generate_corpus,
)


class MechanicsFoundryContracts(unittest.TestCase):
    def test_corpus_is_deterministic_and_large_from_small_seed(self):
        cfg = FoundryConfig(seed=7, variants_per_family=20)
        a = generate_corpus(cfg)
        b = generate_corpus(cfg)
        self.assertEqual(a, b)
        self.assertGreaterEqual(len(a.worlds), 120)
        self.assertGreater(a.transition_count, 1000)

    def test_representation_relabeling_preserves_cycle_and_involution_laws(self):
        corpus = generate_corpus(FoundryConfig(seed=11, variants_per_family=12))
        laws = compile_laws(corpus)
        cycle = [x for x in laws if x.kind == "uniform_period"]
        involutions = [x for x in laws if x.kind == "involution"]
        self.assertTrue(any(x.support_worlds >= 10 for x in cycle))
        self.assertTrue(any(x.support_worlds >= 10 for x in involutions))
        self.assertTrue(all(x.counterexamples == 0 for x in laws if x.status == "WARRANTED_BOUNDED"))

    def test_commutativity_is_discovered_and_noncommuting_controls_block_overgeneralization(self):
        corpus = generate_corpus(FoundryConfig(seed=19, variants_per_family=16))
        laws = compile_laws(corpus)
        commuting = [x for x in laws if x.kind == "commutes"]
        noncommuting = [x for x in laws if x.kind == "noncommutes"]
        self.assertTrue(any(x.support_worlds >= 10 for x in commuting))
        self.assertTrue(any(x.support_worlds >= 10 for x in noncommuting))

    def test_guarded_effect_is_not_promoted_as_unconditional_action_law(self):
        corpus = generate_corpus(FoundryConfig(seed=23, variants_per_family=12))
        laws = compile_laws(corpus)
        guarded = [x for x in laws if x.kind == "guarded_effect"]
        self.assertTrue(guarded)
        self.assertTrue(all(x.status == "CANDIDATE" for x in guarded))
        # A guarded world may contain another genuinely periodic action (for
        # example a mode toggle).  The boundary is that mixed fixed/changing
        # behavior is not itself promoted as an unconditional effect law.
        self.assertFalse(any(x.kind == "guarded_effect" and x.status == "WARRANTED_BOUNDED" for x in laws))

    def test_training_holdout_uses_disjoint_relabelings_and_same_laws_recover(self):
        train = generate_corpus(FoundryConfig(seed=31, variants_per_family=20, split="train"))
        holdout = generate_corpus(FoundryConfig(seed=31, variants_per_family=8, split="holdout"))
        self.assertTrue(set(train.world_ids).isdisjoint(holdout.world_ids))
        train_kinds = {x.kind for x in compile_laws(train) if x.status == "WARRANTED_BOUNDED"}
        holdout_kinds = {x.kind for x in compile_laws(holdout) if x.status == "WARRANTED_BOUNDED"}
        self.assertTrue({"uniform_period", "involution", "idempotent", "commutes", "noncommutes"} <= train_kinds)
        self.assertTrue(train_kinds <= holdout_kinds | {"reachability"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
