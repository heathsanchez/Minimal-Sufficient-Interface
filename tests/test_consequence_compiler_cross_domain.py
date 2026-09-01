import itertools
import unittest

from consequence_compiler import CompilerSpec, compile_consequences


class ConsequenceCompilerCrossDomain(unittest.TestCase):
    def test_constitutional_instance_uses_only_generic_compiler(self):
        carrier = tuple(itertools.product((0, 1), repeat=2))
        authority = lambda p: p[0]
        audit = lambda p: p[1]
        xor = lambda p: p[0] ^ p[1]

        report = compile_consequences(
            CompilerSpec(
                name="constitutional",
                carrier=carrier,
                interface={"authority": authority},
                protected={"audit": audit},
                realizers={"audit": audit, "xor": xor},
                future_queries={"xor": xor},
                realization_costs={
                    "audit": {"audit": 1, "xor": 2},
                    "xor": {"audit": 2, "xor": 1},
                },
            )
        )

        self.assertEqual(len(report.residuals), 2)
        self.assertTrue(report.strict_repair)
        self.assertEqual(report.lawful_realizers, ("audit", "xor"))
        self.assertFalse(report.protected_factors_before["audit"])
        self.assertTrue(report.protected_factors_after["audit"])
        self.assertFalse(report.future_factors_before["xor"])
        self.assertTrue(report.future_factors_after["xor"])
        self.assertEqual(
            report.lawful_cost_profiles,
            {
                "audit": {"audit": 1, "xor": 2},
                "xor": {"audit": 2, "xor": 1},
            },
        )
        self.assertIsNotNone(report.certified_repair)
        self.assertEqual(report.after_state.active_representation, report.required)
        self.assertTrue(report.exact_ablation_ok)
        print(
            "CONSEQUENCE_COMPILER_CONSTITUTIONAL PASS "
            "residuals=2; strict_repair=true; lawful_realizers=2; "
            "cost_profiles=[(1,2),(2,1)]; exact_ablation=true"
        )

    def test_irl_instance_uses_same_generic_compiler(self):
        carrier = tuple(itertools.product(range(-2, 3), repeat=2))
        gap = lambda r: r[1] - r[0]
        r0 = lambda r: r[0]
        r1 = lambda r: r[1]
        sign = lambda r: -1 if gap(r) < 0 else (1 if gap(r) > 0 else 0)

        report = compile_consequences(
            CompilerSpec(
                name="irl_exact_gap",
                carrier=carrier,
                interface={"policy_gap": gap},
                protected={"absolute_r0": r0},
                realizers={"r0": r0, "r1": r1},
                future_queries={"optimal_action": sign, "absolute_r1": r1},
                realization_costs={
                    "r0": {"absolute_r0": 1, "absolute_r1": 2},
                    "r1": {"absolute_r0": 2, "absolute_r1": 1},
                },
            )
        )

        self.assertEqual(len(report.residuals), 30)
        self.assertTrue(report.strict_repair)
        self.assertEqual(report.lawful_realizers, ("r0", "r1"))
        self.assertFalse(report.protected_factors_before["absolute_r0"])
        self.assertTrue(report.protected_factors_after["absolute_r0"])
        self.assertTrue(report.future_factors_before["optimal_action"])
        self.assertTrue(report.future_factors_after["optimal_action"])
        self.assertFalse(report.future_factors_before["absolute_r1"])
        self.assertTrue(report.future_factors_after["absolute_r1"])
        self.assertEqual(
            report.lawful_cost_profiles,
            {
                "r0": {"absolute_r0": 1, "absolute_r1": 2},
                "r1": {"absolute_r0": 2, "absolute_r1": 1},
            },
        )
        self.assertIsNotNone(report.certified_repair)
        self.assertEqual(report.after_state.active_representation, report.required)
        self.assertTrue(report.exact_ablation_ok)
        print(
            "CONSEQUENCE_COMPILER_IRL PASS "
            "rewards=25; residuals=30; strict_repair=true; lawful_realizers=2; "
            "invariant_query_stops=true; exact_ablation=true"
        )

    def test_no_residual_is_a_fixed_point(self):
        carrier = (0, 1, 2, 3)
        identity = lambda x: x
        parity = lambda x: x % 2
        report = compile_consequences(
            CompilerSpec(
                name="already_sufficient",
                carrier=carrier,
                interface={"identity": identity},
                protected={"parity": parity},
                realizers={},
            )
        )
        self.assertEqual(report.residuals, ())
        self.assertFalse(report.strict_repair)
        self.assertEqual(report.current, report.required)
        self.assertIsNone(report.certified_repair)
        self.assertEqual(report.before_state, report.after_state)
        self.assertTrue(report.exact_ablation_ok)
        print("CONSEQUENCE_COMPILER_FIXED_POINT PASS residuals=0; repair=false")


if __name__ == "__main__":
    unittest.main()
