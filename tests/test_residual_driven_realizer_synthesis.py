import itertools
import unittest

from consequence_compiler import CompilerSpec
from realizer_synthesis import (
    SynthesisGrammar,
    extensionally_matches,
    synthesize_realizers,
)


class ResidualDrivenRealizerSynthesis(unittest.TestCase):
    def test_constitutional_semantic_realizers_are_hidden_and_rediscovered(self):
        carrier = tuple(itertools.product((0, 1), repeat=2))
        authority = lambda p: p[0]
        audit = lambda p: p[1]
        xor = lambda p: p[0] ^ p[1]

        # The search receives only anonymously named raw measurements and
        # generic Boolean constructors.  It is not handed audit/xor as
        # candidate realizers.
        grammar = SynthesisGrammar(
            primitives={
                "sensor_0": lambda p: p[0],
                "sensor_1": lambda p: p[1],
            },
            unary={"not": lambda x: 1 - x},
            binary={"xor": lambda x, y: x ^ y},
            max_size=3,
        )
        spec = CompilerSpec(
            name="constitutional_synthesis",
            carrier=carrier,
            interface={"authority": authority},
            protected={"audit": audit},
            realizers={},
            future_queries={"xor": xor},
        )

        report = synthesize_realizers(spec, grammar)
        self.assertEqual(len(report.base.residuals), 2)
        self.assertTrue(report.base.strict_repair)
        self.assertEqual(report.minimal_lawful_size, 1)
        self.assertTrue(report.base.exact_ablation_ok)

        audit_matches = [
            e for e in report.lawful_expressions
            if extensionally_matches(e, carrier, audit)
        ]
        xor_matches = [
            e for e in report.lawful_expressions
            if extensionally_matches(e, carrier, xor)
        ]
        self.assertTrue(audit_matches)
        self.assertTrue(xor_matches)
        self.assertIn("sensor_1", report.base.lawful_realizers)
        self.assertTrue(report.base.protected_factors_after["audit"])
        self.assertTrue(report.base.future_factors_after["xor"])

        print(
            "RESIDUAL_SYNTHESIS_CONSTITUTIONAL PASS "
            f"residuals={len(report.base.residuals)}; "
            f"expressions={len(report.expressions)}; "
            f"lawful={len(report.lawful_expressions)}; "
            f"min_size={report.minimal_lawful_size}; "
            "audit_class_rediscovered=true; xor_class_rediscovered=true; "
            "exact_ablation=true"
        )

    def test_irl_semantic_realizers_are_hidden_and_rediscovered(self):
        carrier = tuple(itertools.product(range(-2, 3), repeat=2))
        gap = lambda r: r[1] - r[0]
        r0 = lambda r: r[0]
        r1 = lambda r: r[1]
        sign = lambda r: -1 if gap(r) < 0 else (1 if gap(r) > 0 else 0)

        grammar = SynthesisGrammar(
            primitives={
                "sensor_0": lambda r: r[0],
                "sensor_1": lambda r: r[1],
            },
            unary={"neg": lambda x: -x},
            binary={
                "add": lambda x, y: x + y,
                "sub": lambda x, y: x - y,
            },
            max_size=3,
        )
        spec = CompilerSpec(
            name="irl_synthesis",
            carrier=carrier,
            interface={"policy_gap": gap},
            protected={"absolute_r0": r0},
            realizers={},
            future_queries={"optimal_action": sign, "absolute_r1": r1},
        )

        report = synthesize_realizers(spec, grammar)
        self.assertEqual(len(report.base.residuals), 30)
        self.assertTrue(report.base.strict_repair)
        self.assertEqual(report.minimal_lawful_size, 1)
        self.assertEqual(set(report.base.lawful_realizers), {"sensor_0", "sensor_1"})
        self.assertTrue(any(extensionally_matches(e, carrier, r0) for e in report.lawful_expressions))
        self.assertTrue(any(extensionally_matches(e, carrier, r1) for e in report.lawful_expressions))
        self.assertTrue(report.base.future_factors_before["optimal_action"])
        self.assertTrue(report.base.future_factors_after["optimal_action"])
        self.assertFalse(report.base.future_factors_before["absolute_r1"])
        self.assertTrue(report.base.future_factors_after["absolute_r1"])
        self.assertTrue(report.base.exact_ablation_ok)

        print(
            "RESIDUAL_SYNTHESIS_IRL PASS "
            f"rewards={len(carrier)}; residuals={len(report.base.residuals)}; "
            f"expressions={len(report.expressions)}; "
            f"lawful={len(report.lawful_expressions)}; "
            "minimal_realizers=2; r0_class_rediscovered=true; "
            "r1_class_rediscovered=true; invariant_query_stops=true; "
            "exact_ablation=true"
        )

    def test_missing_raw_information_cannot_be_conjured(self):
        carrier = tuple(itertools.product((0, 1), repeat=2))
        authority = lambda p: p[0]
        audit = lambda p: p[1]

        # Remove the second raw channel entirely.  Closure of functions of
        # authority alone cannot separate states collapsed by authority.
        grammar = SynthesisGrammar(
            primitives={"sensor_0": lambda p: p[0]},
            unary={"not": lambda x: 1 - x},
            binary={"xor": lambda x, y: x ^ y},
            max_size=5,
        )
        report = synthesize_realizers(
            CompilerSpec(
                name="constitutional_information_ablation",
                carrier=carrier,
                interface={"authority": authority},
                protected={"audit": audit},
                realizers={},
            ),
            grammar,
        )
        self.assertEqual(len(report.base.residuals), 2)
        self.assertEqual(report.lawful_expressions, ())
        self.assertIsNone(report.minimal_lawful_size)
        self.assertEqual(report.base.lawful_realizers, ())
        print(
            "RESIDUAL_SYNTHESIS_INFORMATION_ABLATION PASS "
            "residuals=2; lawful=0; unavailable_information_not_conjured=true"
        )

    def test_candidate_realizer_leakage_is_rejected(self):
        carrier = ((0, 0), (0, 1), (1, 0), (1, 1))
        authority = lambda p: p[0]
        audit = lambda p: p[1]
        grammar = SynthesisGrammar(
            primitives={"sensor_0": lambda p: p[0], "sensor_1": lambda p: p[1]},
            unary={},
            binary={},
            max_size=1,
        )
        with self.assertRaisesRegex(ValueError, "empty realizer list"):
            synthesize_realizers(
                CompilerSpec(
                    name="leakage_guard",
                    carrier=carrier,
                    interface={"authority": authority},
                    protected={"audit": audit},
                    realizers={"audit": audit},
                ),
                grammar,
            )
        print("RESIDUAL_SYNTHESIS_LEAKAGE_GUARD PASS supplied_realizers_rejected=true")


if __name__ == "__main__":
    unittest.main()
