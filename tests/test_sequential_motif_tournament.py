import unittest

from sequential_motif_tournament import run_motif_tournament


class SequentialMotifTournamentTest(unittest.TestCase):
    def test_exact_three_macro_library_is_selected(self):
        r = run_motif_tournament()
        self.assertEqual(r.traces, 7)
        self.assertEqual(r.candidates, 33)
        self.assertEqual(
            r.champion,
            (
                ("APPLY_FUTURE", "VERIFY_REACH", "ABLATE"),
                ("PUSH", "VERIFY_FAILURE", "RESIDUAL"),
                ("SYNTHESIZE", "RETAIN", "PROMOTE"),
            ),
        )

    def test_macro_library_improves_description_length_after_definition_cost(self):
        r = run_motif_tournament()
        self.assertEqual(r.primitive_tokens, 59)
        self.assertEqual(r.encoded_trace_tokens, 33)
        self.assertEqual(r.definition_tokens, 12)
        self.assertEqual(r.total_description_tokens, 45)
        self.assertEqual(r.saved_tokens, 14)
        self.assertGreater(r.compression_ratio, 1.3)

    def test_transparent_expansion_preserves_causal_trace(self):
        r = run_motif_tournament()
        self.assertTrue(r.exact_expansion)

    def test_leave_one_domain_out_transfer_is_positive_everywhere(self):
        r = run_motif_tournament()
        self.assertTrue(all(v > 0 for v in r.leave_one_out_savings.values()))
        self.assertEqual(min(r.leave_one_out_savings.values()), 2)

    def test_promotion_is_earned_not_static_merge(self):
        r = run_motif_tournament()
        self.assertEqual(r.decision, "PROMOTE_TRANSPARENT_SEQUENTIAL_MACROS")


if __name__ == "__main__":
    unittest.main()
