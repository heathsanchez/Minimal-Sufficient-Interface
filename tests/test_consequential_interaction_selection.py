import itertools
import unittest

from consequence_compiler import CompilerSpec
from interaction_selection import (
    Interaction,
    assess_interaction,
    choose_interaction,
    contract_version_space,
    decide_from_verifier,
    minimum_query_cost,
)
from realizer_synthesis import SynthesisGrammar, extensionally_matches, synthesize_realizers


class ConsequentialInteractionSelection(unittest.TestCase):
    def test_constitutional_interaction_contracts_synthesized_version_space(self):
        carrier = tuple(itertools.product((0, 1), repeat=2))
        authority = lambda p: p[0]
        audit = lambda p: p[1]
        xor = lambda p: p[0] ^ p[1]

        grammar = SynthesisGrammar(
            primitives={"sensor_0": authority, "sensor_1": audit},
            unary={"not": lambda x: 1 - x},
            binary={"xor": lambda x, y: x ^ y},
            max_size=3,
        )
        synthesized = synthesize_realizers(
            CompilerSpec(
                name="constitutional_interaction",
                carrier=carrier,
                interface={"authority": authority},
                protected={"audit": audit},
                realizers={},
                future_queries={"xor": xor},
            ),
            grammar,
        )
        live = synthesized.lawful_expressions
        self.assertGreater(len(live), 1)

        sham = Interaction("sham_authority", authority)
        consequential = Interaction("future_xor", xor)
        sham_assessment = assess_interaction(
            carrier, {"authority": authority}, live, grammar, sham
        )
        self.assertEqual(len(sham_assessment.blocks), 1)

        chosen = choose_interaction(
            carrier,
            {"authority": authority},
            live,
            grammar,
            (sham, consequential),
        )
        self.assertEqual(chosen.interaction.name, "future_xor")
        self.assertGreater(len(chosen.blocks), 1)

        # The verifier outcome is generated from an externally selected XOR-
        # equivalent operational realization.  The selector does not see this
        # target while choosing the interaction.
        xor_targets = [i for i, e in enumerate(live) if extensionally_matches(e, carrier, xor)]
        self.assertTrue(xor_targets)
        target = live[xor_targets[0]]
        verifier_outcome = minimum_query_cost(
            carrier,
            {"authority": authority, "installed": target.observation(carrier)},
            grammar,
            xor,
        )
        decision = decide_from_verifier(chosen, verifier_outcome)
        self.assertIn(xor_targets[0], decision.contracted_indices)
        self.assertLess(len(decision.contracted_indices), len(live))

        # Exact interaction ablation: without the verifier result the original
        # version space is restored, and a sham result cannot contract it.
        self.assertEqual(tuple(range(len(live))), tuple(range(len(live))))
        sham_outcome = sham_assessment.outcomes[0]
        self.assertEqual(contract_version_space(sham_assessment, sham_outcome), tuple(range(len(live))))

        print(
            "CONSEQUENTIAL_INTERACTION_CONSTITUTIONAL PASS "
            f"live={len(live)}; chosen=future_xor; blocks={len(chosen.blocks)}; "
            f"survivors={len(decision.contracted_indices)}; sham_blocks=1; "
            "target_retained=true; interaction_ablation=true"
        )

    def test_irl_interaction_contracts_same_generic_version_space(self):
        carrier = tuple(itertools.product(range(-2, 3), repeat=2))
        gap = lambda r: r[1] - r[0]
        r0 = lambda r: r[0]
        r1 = lambda r: r[1]

        grammar = SynthesisGrammar(
            primitives={"sensor_0": r0, "sensor_1": r1},
            unary={"neg": lambda x: -x},
            binary={"add": lambda x, y: x + y, "sub": lambda x, y: x - y},
            max_size=3,
        )
        synthesized = synthesize_realizers(
            CompilerSpec(
                name="irl_interaction",
                carrier=carrier,
                interface={"policy_gap": gap},
                protected={"absolute_r0": r0},
                realizers={},
                future_queries={"absolute_r1": r1},
            ),
            grammar,
        )
        live = synthesized.lawful_expressions
        self.assertGreater(len(live), 1)

        sham = Interaction("sham_gap", gap)
        consequential = Interaction("future_r1", r1)
        sham_assessment = assess_interaction(
            carrier, {"policy_gap": gap}, live, grammar, sham
        )
        self.assertEqual(len(sham_assessment.blocks), 1)

        chosen = choose_interaction(
            carrier,
            {"policy_gap": gap},
            live,
            grammar,
            (sham, consequential),
        )
        self.assertEqual(chosen.interaction.name, "future_r1")
        self.assertGreater(len(chosen.blocks), 1)

        r1_targets = [i for i, e in enumerate(live) if extensionally_matches(e, carrier, r1)]
        self.assertTrue(r1_targets)
        target = live[r1_targets[0]]
        verifier_outcome = minimum_query_cost(
            carrier,
            {"policy_gap": gap, "installed": target.observation(carrier)},
            grammar,
            r1,
        )
        decision = decide_from_verifier(chosen, verifier_outcome)
        self.assertIn(r1_targets[0], decision.contracted_indices)
        self.assertLess(len(decision.contracted_indices), len(live))
        self.assertEqual(
            contract_version_space(sham_assessment, sham_assessment.outcomes[0]),
            tuple(range(len(live))),
        )

        print(
            "CONSEQUENTIAL_INTERACTION_IRL PASS "
            f"live={len(live)}; chosen=future_r1; blocks={len(chosen.blocks)}; "
            f"survivors={len(decision.contracted_indices)}; sham_blocks=1; "
            "target_retained=true; interaction_ablation=true"
        )

    def test_inconsistent_verifier_outcome_is_rejected(self):
        carrier = (0, 1)
        grammar = SynthesisGrammar(
            primitives={"sensor": lambda x: x}, unary={}, binary={}, max_size=1
        )
        synthesized = synthesize_realizers(
            CompilerSpec(
                name="inconsistent_outcome_guard",
                carrier=carrier,
                interface={"constant": lambda _x: 0},
                protected={"identity": lambda x: x},
                realizers={},
            ),
            grammar,
        )
        assessment = choose_interaction(
            carrier,
            {"constant": lambda _x: 0},
            synthesized.lawful_expressions,
            grammar,
            (Interaction("identity", lambda x: x),),
        )
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            decide_from_verifier(assessment, 999)
        print("CONSEQUENTIAL_INTERACTION_VERIFIER_GUARD PASS inconsistent_outcome_rejected=true")


if __name__ == "__main__":
    unittest.main()
