import unittest

from calculus_tournament import run_tournament


class CalculusTournamentTest(unittest.TestCase):
    def test_full_factorial_family_is_fully_separated(self):
        report = run_tournament()
        self.assertEqual(report.candidates, 32)
        self.assertEqual(report.attacks, 91)
        self.assertEqual(report.quotient_classes, 32)
        self.assertEqual(report.pairwise_distinctions, 496)
        self.assertEqual(report.pairwise_possible, 496)

    def test_exact_minimum_suite_has_five_attacks(self):
        report = run_tournament()
        self.assertEqual(len(report.selected), 5)
        self.assertEqual(
            tuple(attack.name for attack in report.selected),
            (
                "controller_r1_l0_c0_f0",
                "controller_r1_l1_c0_f0",
                "fixedpoint_new1",
                "provenance_a1_p0",
                "interaction_raw2_safe1",
            ),
        )
        self.assertEqual(report.selected_quotient_classes, 32)
        self.assertTrue(report.refined_unique)

    def test_each_selected_attack_is_necessary_for_full_quotient(self):
        report = run_tournament()
        self.assertEqual(
            dict(report.ablation_quotient_classes),
            {
                "controller_r1_l0_c0_f0": 24,
                "controller_r1_l1_c0_f0": 16,
                "fixedpoint_new1": 16,
                "provenance_a1_p0": 16,
                "interaction_raw2_safe1": 16,
            },
        )
        self.assertTrue(all(classes < 32 for classes in report.ablation_quotient_classes.values()))

    def test_every_refinement_has_a_consequential_witness(self):
        report = run_tournament()
        self.assertEqual(
            {name: len(witnesses) for name, witnesses in report.necessity_witnesses.items()},
            {
                "relative_fixed_point": 1,
                "requires_coverage_for_escalation": 5,
                "quotients_future_equivalent_realizers": 14,
                "preserves_provenance_outside_active_quotient": 10,
                "lawful_interaction_objective": 15,
            },
        )
        self.assertTrue(all(report.necessity_witnesses.values()))


if __name__ == "__main__":
    unittest.main()
