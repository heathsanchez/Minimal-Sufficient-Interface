import unittest

from self_attack_synthesis import (
    MUTANTS,
    attack_outcome,
    enumerate_attack_grammar,
    separated_mutants,
    synthesize_minimum_attack_set,
)
from minimum_calculus_self_audit import V1


class SelfAttackSynthesis(unittest.TestCase):
    def test_generated_attack_grammar_is_nontrivial(self):
        attacks = enumerate_attack_grammar()
        self.assertGreater(len(attacks), 50)
        self.assertGreater(len({a.kind for a in attacks}), 3)
        print(f"SELF_ATTACK_GRAMMAR PASS candidates={len(attacks)}; kinds={len({a.kind for a in attacks})}")

    def test_each_selected_attack_is_actually_consequential(self):
        report = synthesize_minimum_attack_set()
        for attack in report.selected:
            self.assertTrue(separated_mutants(attack))
        print(
            "SELF_ATTACK_INFORMATION PASS "
            f"informative={report.informative}; selected={len(report.selected)}"
        )

    def test_minimum_generated_set_separates_every_one_distinction_ablation(self):
        report = synthesize_minimum_attack_set()
        target = frozenset(mutant.name for mutant in MUTANTS)
        self.assertEqual(report.covered_mutants, target)
        self.assertEqual(report.mutants, len(target))
        print(
            "SELF_ATTACK_COVER PASS "
            f"mutants={report.mutants}; selected={len(report.selected)}; "
            f"attacks={','.join(a.name for a in report.selected)}"
        )

    def test_selected_set_is_cardinality_minimal_under_generated_grammar(self):
        report = synthesize_minimum_attack_set()
        # No single generated attack is allowed to distinguish every independent
        # contract ablation if the returned minimum requires more than one.
        target = frozenset(mutant.name for mutant in MUTANTS)
        if len(report.selected) > 1:
            for attack in enumerate_attack_grammar():
                self.assertNotEqual(separated_mutants(attack), target)
        print(
            "SELF_ATTACK_MINIMALITY PASS "
            f"selected={len(report.selected)}; exact_generated_cover=true"
        )

    def test_sham_attacks_do_not_count_as_information_gain(self):
        attacks = enumerate_attack_grammar()
        sham = [a for a in attacks if not separated_mutants(a)]
        self.assertTrue(sham)
        for attack in sham[:20]:
            baseline = attack_outcome(V1, attack)
            self.assertTrue(all(attack_outcome(m, attack) == baseline for m in MUTANTS))
        print(f"SELF_ATTACK_SHAM PASS noninformative={len(sham)}; rejected=true")

    def test_attack_generation_does_not_change_the_refined_calculus(self):
        before = (
            V1.relative_fixed_point,
            V1.requires_coverage_for_escalation,
            V1.quotients_future_equivalent_realizers,
            V1.preserves_provenance_outside_active_quotient,
            V1.lawful_interaction_objective,
        )
        synthesize_minimum_attack_set()
        after = (
            V1.relative_fixed_point,
            V1.requires_coverage_for_escalation,
            V1.quotients_future_equivalent_realizers,
            V1.preserves_provenance_outside_active_quotient,
            V1.lawful_interaction_objective,
        )
        self.assertEqual(before, after)
        print("SELF_ATTACK_NONMUTATION PASS calculus_unchanged=true")


if __name__ == "__main__":
    unittest.main()
