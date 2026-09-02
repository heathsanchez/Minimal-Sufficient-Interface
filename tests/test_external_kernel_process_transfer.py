import unittest

from external_kernel_process_transfer import PDRC, run_external_transfer


class ExternalKernelProcessTransferTest(unittest.TestCase):
    def test_exact_learned_macros_are_not_forced(self):
        r = run_external_transfer()
        self.assertLess(r.exact_macro_coverage, len(r.learned_macros))

    def test_high_level_pdrc_order_survives(self):
        r = run_external_transfer()
        self.assertTrue(r.pdrc_order_preserved)
        self.assertEqual(r.pdrc_distinct_phases, len(PDRC))

    def test_decision_records_partial_transfer(self):
        r = run_external_transfer()
        self.assertEqual(r.decision, "NO_EXACT_MACRO_TRANSFER__PDRC_SKELETON_TRANSFERS")

    def test_external_trace_is_not_one_of_training_traces(self):
        r = run_external_transfer()
        from sequential_motif_tournament import TRACES
        self.assertNotIn(r.low_trace, TRACES.values())


if __name__ == "__main__":
    unittest.main()
