import unittest

from recursive_process_compounding import run_recursive_compounding


class RecursiveProcessCompoundingTest(unittest.TestCase):
    def test_second_order_promotion_is_not_forced(self):
        r = run_recursive_compounding()
        self.assertEqual(r.second_order_decision, "NO_SECOND_ORDER_PROMOTION__RETAIN_FIRST_ORDER_LIBRARY")
        self.assertGreater(r.second_order_candidates, 0)
        self.assertGreaterEqual(r.second_order_total, r.second_order_baseline)

    def test_first_order_macros_change_held_out_frontier(self):
        r = run_recursive_compounding()
        self.assertFalse(r.cold_reaches)
        self.assertTrue(r.warm_reaches)
        self.assertLessEqual(r.held_out_warm_cost, r.held_out_budget)
        self.assertGreater(r.held_out_primitive_cost, r.held_out_budget)

    def test_sham_and_each_exact_ancestor_ablation_fail(self):
        r = run_recursive_compounding()
        self.assertFalse(r.sham_reaches)
        self.assertTrue(r.ablation_reaches)
        self.assertTrue(all(not reaches for reaches in r.ablation_reaches.values()))

    def test_process_macros_remain_transparent(self):
        r = run_recursive_compounding()
        self.assertTrue(r.exact_warm_expansion)

    def test_capability_promotion_is_causal_and_bounded(self):
        r = run_recursive_compounding()
        self.assertEqual(
            r.capability_decision,
            "PROMOTE_FIRST_ORDER_MACROS_AS_CAUSAL_PROCESS_CAPABILITY",
        )


if __name__ == "__main__":
    unittest.main()
