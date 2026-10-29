"""Test a missing causal link in the historical synthetic G3 witness.

The original descendant test starts from a handwritten arithmetic function.
Here the one-bit block must be executable *only* from independently selected,
budget-admitted, verifier-checked programs of the first generation.
"""

import unittest

from tests.test_blind_recursive_cross_grammar_genesis import (
    CARRY3,
    GRAMMARS,
    SUM3,
    Expr,
    discover_interface,
    frozen_task_split,
    learn_doubling_interface,
    synthesize_programs,
    target_block,
)

from g3_physical_k1_ancestry import (
    BudgetExceeded,
    InvalidCertificate,
    compile_promoted_block,
)


class PhysicalK1Ancestry(unittest.TestCase):
    def test_learned_and_verified_k1_executable_is_actual_parent_of_k2_k3_k4(self):
        training, _held_out = frozen_task_split()
        for grammar in GRAMMARS:
            with self.subTest(grammar=grammar.code):
                chosen, _winners, _cost, _frontier = discover_interface(
                    grammar, training
                )
                programs = synthesize_programs(3, grammar, chosen)
                one_bit_block = compile_promoted_block(
                    grammar, chosen, programs, SUM3, CARRY3, budget=6
                )

                # Independent source target, not the compiled program's evaluator.
                for a in (0, 1):
                    for b in (0, 1):
                        for incoming in (0, 1):
                            self.assertEqual(
                                one_bit_block(a, b, incoming),
                                target_block(1, a, b, incoming),
                            )

                parent = one_bit_block
                for width in (2, 4, 8):
                    plan, survivors, residuals, child = learn_doubling_interface(
                        parent, width // 2
                    )
                    self.assertEqual(len(survivors), 1)
                    self.assertGreater(len(residuals), 0)
                    for a in range(1 << width):
                        for b in range(1 << width):
                            for incoming in (0, 1):
                                self.assertEqual(
                                    child(a, b, incoming),
                                    target_block(width, a, b, incoming),
                                )
                    parent = child

                # Physical first-generation ablation: the same source grammar
                # cannot yield an admissible one-bit block at the frozen budget.
                cold_programs = synthesize_programs(3, grammar)
                with self.assertRaises(BudgetExceeded):
                    compile_promoted_block(
                        grammar, (), cold_programs, SUM3, CARRY3, budget=6
                    )
                # Stronger withdrawal: keep the original warm proof program,
                # but physically remove the learned constructor definitions.
                # There must be no implicit handwritten arithmetic fallback.
                with self.assertRaises(InvalidCertificate):
                    compile_promoted_block(
                        grammar, (), programs, SUM3, CARRY3, budget=6
                    )

    def test_false_certificate_cannot_enter_the_recursive_lineage(self):
        grammar = GRAMMARS[0]
        training, _ = frozen_task_split()
        chosen, _, _, _ = discover_interface(grammar, training)
        programs = synthesize_programs(3, grammar, chosen)
        poisoned = dict(programs)
        poisoned[SUM3] = (0, Expr("x0"))
        with self.assertRaises(InvalidCertificate):
            compile_promoted_block(
                grammar, chosen, poisoned, SUM3, CARRY3, budget=6
            )

        # A claimant cannot swap in an answer mask and have the compiler
        # simply memorize it in place of the executable program's behaviour.
        false_mask = SUM3 ^ 1
        fake_expected = dict(programs)
        fake_expected[false_mask] = fake_expected.pop(SUM3)
        with self.assertRaises(InvalidCertificate):
            compile_promoted_block(
                grammar, chosen, fake_expected, false_mask, CARRY3, budget=6
            )

        # After verified admission, only the two independently derived finite
        # behaviours are needed to run the capability: no history reread.
        compiled = compile_promoted_block(
            grammar, chosen, programs, SUM3, CARRY3, budget=6
        )
        programs.clear()
        self.assertEqual(compiled(1, 1, 1), (1, 1))


if __name__ == "__main__":
    unittest.main()
