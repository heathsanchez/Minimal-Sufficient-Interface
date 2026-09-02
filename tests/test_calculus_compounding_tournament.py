import unittest

from calculus_compounding_tournament import run_compounding_tournament


class CalculusCompoundingTournamentTest(unittest.TestCase):
    def test_all_set_partitions_are_tournamented(self):
        r = run_compounding_tournament()
        self.assertEqual(r.partition_candidates, 52)
        self.assertEqual(r.total_candidates, 53)
        self.assertEqual(r.full_classes, 32)

    def test_no_nontrivial_synchronized_merge_is_lossless(self):
        r = run_compounding_tournament()
        self.assertLess(r.best_nontrivial_classes, 32)
        self.assertEqual(r.champion.coordinates, 5)
        self.assertTrue(r.champion.structurally_licensed)
        self.assertTrue(r.champion.lossless)

    def test_opaque_recode_is_rejected_despite_empirical_fidelity(self):
        r = run_compounding_tournament()
        self.assertIn("opaque_32_state_codebook", r.unlicensed_empirical_survivors)
        self.assertGreaterEqual(r.lossless_candidates, 2)
        self.assertEqual(r.licensed_lossless_candidates, 1)

    def test_decision_retains_independent_refinements_and_changes_grammar(self):
        r = run_compounding_tournament()
        self.assertEqual(
            r.decision,
            "NO_COMPOUND_MERGE__RETAIN_FIVE_INDEPENDENT_REFINEMENTS__CHANGE_COMPOSITION_GRAMMAR",
        )
        self.assertIn("sequential operator motifs", r.next_grammar)
        self.assertIn("conditional/state-dependent composition", r.next_grammar)


if __name__ == "__main__":
    unittest.main()
