import unittest

from src.consequential_core_full import (
    DevelopmentState,
    FiniteObservationLanguage,
    ablate,
    certify_capability_repair,
    certify_residual,
    compile_capability,
    compile_representation,
    discriminating_pairs,
    equivalent,
    quotient_admissible,
    representation_version_space,
    select_by_verified_pair,
)


def residual_orbit_indicator(state, residual, generator):
    """Temporary adapter: indicator of the residual endpoint's generated orbit.

    This is deliberately tiny and will move into the shared core once the chain
    proves that the abstraction is sound. It uses only the certified residual
    endpoint and declared dynamics, not the hidden consequence column.
    """
    x, y = residual.pair
    seen = set()
    z = x
    while z not in seen:
        seen.add(z)
        z = generator[z]
    if y in seen:
        raise ValueError("residual endpoints lie in the same generated orbit")
    return tuple(1 if s in seen else 0 for s in state.carrier)


class ConsequentialSingleChain(unittest.TestCase):
    def test_one_state_object_runs_capability_then_version_space_then_ablation(self):
        X = (0, 1, 2, 3)
        identity = (0, 1, 2, 3)

        # S0: no consequential distinction is initially available.
        language0 = FiniteObservationLanguage(
            observations=((0, 0, 0, 0),),
            dynamics=(identity,),
        )
        s0 = DevelopmentState.from_language(X, language0)
        self.assertEqual(s0.representation, ((0, 1, 2, 3),))

        # Residual 1: verifier certifies that 3 and 0 must differ. Exhaustive old
        # closure still merges them. The hidden consequence is used only for
        # certification; its literal feature is not supplied to the constructor.
        hidden1 = (0, 0, 0, 1)
        rho1 = certify_residual(s0, (3, 0), hidden1)
        delta1 = residual_orbit_indicator(s0, rho1, identity)
        self.assertEqual(delta1, (0, 0, 0, 1))

        cap1 = certify_capability_repair(s0, rho1, delta1)
        s1 = compile_capability(s0, cap1, "capability-1")
        self.assertEqual(s1.representation, ((0, 1, 2), (3,)))

        # Residual 2 now lands in a genuine 3+1 geometry. Its pair-level evidence
        # does not uniquely determine a representation repair.
        rho2 = certify_residual(s1, (0, 1), None)
        version_space = representation_version_space(s1, rho2)
        self.assertEqual(len(version_space), 2)
        self.assertEqual(
            {r.new_representation for r in version_space},
            {
                ((0,), (1, 2), (3,)),
                ((0, 2), (1,), (3,)),
            },
        )

        # The ambiguity itself generates the next discriminating question.
        probes = discriminating_pairs(version_space)
        self.assertTrue(probes)
        probe = (0, 2)
        self.assertIn(probe, probes)

        # External answer: 0 and 2 are equal under the sealed target structure.
        survivors = select_by_verified_pair(version_space, probe, should_be_equal=True)
        self.assertEqual(len(survivors), 1)
        selected = survivors[0]
        self.assertEqual(selected.new_representation, ((0, 2), (1,), (3,)))

        s2 = compile_representation(s1, selected, "representation-2")

        # A downstream executable action was present all along but did not descend
        # through P1. It becomes quotient-admissible only after the selected repair.
        downstream = (0, 3, 2, 3)
        self.assertFalse(quotient_admissible(downstream, s1.representation))
        self.assertTrue(quotient_admissible(downstream, s2.representation))

        # Exact provenance ablation removes only the representation repair and
        # restores the previous developmental frontier.
        back_to_s1 = ablate(s2, "representation-2")
        self.assertEqual(back_to_s1, s1)
        self.assertFalse(quotient_admissible(downstream, back_to_s1.representation))

        # Ablating the earlier capability returns exactly to the indiscrete start.
        back_to_s0 = ablate(back_to_s1, "capability-1")
        self.assertEqual(back_to_s0, s0)

        print(
            "CONSEQUENTIAL SINGLE CHAIN PASS "
            "S0=1block capability->S1=3+1 version_space=2 "
            "experiment->S2=3blocks downstream=PASS ablation=FAIL"
        )


if __name__ == "__main__":
    unittest.main()
