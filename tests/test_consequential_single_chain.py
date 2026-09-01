import unittest

from consequential_certification import (
    certify_finite_table_language_extension,
    certify_kernel_policy_update,
    certify_language_extension,
    certify_representation_repair,
    kernel_fingerprint,
)
from consequential_core import (
    AcquisitionResidual, ClosureCertificate, ClosureResidual, CoupledRepair,
    DevelopmentState, EquivalenceRelation, ExtendLanguage, PairResidual,
    UpdatePolicy, ablate, compile_repair, quotient_admissible,
)
from consequential_version_space import (
    coarsest_representation_repairs, discriminating_pairs,
    update_version_space_from_pair_answer,
)


class ConsequentialSingleChain(unittest.TestCase):
    def test_non_repairs_and_nonminimal_repairs_are_rejected(self):
        X = tuple(range(4))
        old_E = EquivalenceRelation.from_partition(X, ({0, 1, 2}, {3}))
        rho = PairResidual(0, 1, old_E, consequence_left=0, consequence_right=1)
        dynamics = (lambda _z: 0,)
        good_E = EquivalenceRelation.from_partition(X, ({0}, {1, 2}, {3}))
        alternative_E = EquivalenceRelation.from_partition(X, ({0, 2}, {1}, {3}))
        S = DevelopmentState(X, active_representation=old_E,
                             version_space=(good_E, alternative_E), language=("id",))

        # Incorrect: leaves the motivating pair merged.
        bad = CoupledRepair(new_representation=old_E, new_version_space=(old_E,))
        with self.assertRaises(ValueError):
            certify_representation_repair(S, rho, bad, experiment_pair=(0, 2),
                observed_same=False, dynamics=dynamics, attachment="unresolved")

        # Correct but non-minimal: discrete E resolves rho and is lawful, but a
        # strictly coarser lawful resolver exists. Certification must reject it.
        discrete = EquivalenceRelation.from_partition(X, ({0}, {1}, {2}, {3}))
        self.assertFalse(discrete.same(0, 1))
        with self.assertRaises(ValueError):
            certify_representation_repair(
                DevelopmentState(X, active_representation=old_E, language=("id",)),
                rho, CoupledRepair(new_representation=discrete,
                                   new_version_space=(discrete,)),
                experiment_pair=(0, 2), observed_same=False, dynamics=dynamics,
                attachment="valid but over-refined")

        # Correct/minimal candidate, wrong verified version-space answer.
        with self.assertRaises(ValueError):
            certify_representation_repair(S, rho,
                CoupledRepair(new_representation=good_E, new_version_space=(good_E,)),
                experiment_pair=(0, 2), observed_same=True, dynamics=dynamics,
                attachment="wrong survivor")

        required = alternative_E
        closure = ClosureCertificate(("id",), True, "identity-only", S.language)
        rho_closure = ClosureResidual(required, (old_E,), closure)
        with self.assertRaises(ValueError):
            certify_language_extension(S, rho_closure, ExtendLanguage("sham"),
                realized_required_kernel=old_E,
                lawful_under_active_representation=True, attachment="wrong kernel")
        with self.assertRaises(ValueError):
            certify_finite_table_language_extension(S, rho_closure,
                ExtendLanguage(("wrong-artifact", (0, 1, 2, 3))),
                executable_table=(0, 0, 2, 3), attachment="delta/table mismatch")

    def test_representation_to_language_to_second_order_development(self):
        X = tuple(range(4))
        old_E = EquivalenceRelation.from_partition(X, ({0, 1, 2}, {3}))
        rho1 = PairResidual(0, 1, old_E, consequence_left=0, consequence_right=1)
        dynamics = (lambda _z: 0,)
        pre = DevelopmentState(X, active_representation=old_E, language=("id",))
        H0 = coarsest_representation_repairs(pre, rho1, dynamics)
        self.assertEqual(len(H0), 2)
        self.assertTrue(all(h.strictly_refines(old_E) for h in H0))
        S0 = DevelopmentState(X, active_representation=old_E,
                              version_space=H0, language=("id",), policy=None)

        probes = discriminating_pairs(H0)
        probe = (0, 2)
        self.assertIn(probe, probes)
        observed_same = True
        survivors = update_version_space_from_pair_answer(H0, probe,
                                                           observed_same=observed_same)
        self.assertEqual(len(survivors), 1)
        selected = survivors[0]
        repair1 = CoupledRepair(new_representation=selected,
                                new_version_space=(selected,))
        certified1 = certify_representation_repair(
            S0, rho1, repair1, experiment_pair=probe, observed_same=observed_same,
            dynamics=dynamics,
            attachment=f"verified experiment {probe} collapses residual-relative H")
        S1, token1 = compile_repair(S0, certified1)

        action_table = (0, 3, 2, 3)
        action = lambda z: action_table[z]
        self.assertFalse(quotient_admissible(action, old_E))
        self.assertTrue(quotient_admissible(action, selected))
        required1 = EquivalenceRelation.from_observation(X, action)
        identity_kernel = EquivalenceRelation.from_observation(X, lambda z: z)
        closure1 = ClosureCertificate(("id",), True,
            "one-step identity-only executable language", S1.language)
        rho2 = ClosureResidual(required1, (identity_kernel,), closure1)
        executable_delta = ("licensed_action", action_table)
        certified2 = certify_finite_table_language_extension(
            S1, rho2, ExtendLanguage(executable_delta), executable_table=action_table,
            attachment="new quotient makes the executable operator lawful")
        S2, token2 = compile_repair(S1, certified2)

        def executable_capability(state):
            return executable_delta in state.language and state.active_representation is not None and quotient_admissible(action, state.active_representation)
        self.assertFalse(executable_capability(S1))
        self.assertTrue(executable_capability(S2))
        self.assertFalse(executable_capability(ablate(S2, token2)))
        self.assertEqual(ablate(S1, token1), S0)

        learned_policy = kernel_fingerprint(required1)
        self.assertEqual(learned_policy, (1, 1, 2))
        future_tables = {"future_bad": (0, 1, 2, 3), "future_good": (0, 1, 1, 2)}
        future_kernels = {name: EquivalenceRelation.from_observation(
            X, lambda i, t=table: t[i]) for name, table in future_tables.items()}
        future_target = future_kernels["future_good"]
        self.assertNotEqual(future_target, required1)
        self.assertEqual(kernel_fingerprint(future_target), learned_policy)

        def acquisition_episode(policy):
            order = ("future_bad", "future_good")
            if policy is None:
                chosen = order[0]
            else:
                matches = [q for q in order if kernel_fingerprint(future_kernels[q]) == policy]
                chosen = matches[0] if matches else order[0]
            return chosen, future_kernels[chosen] == future_target

        self.assertFalse(acquisition_episode(S2.policy)[1])
        rho3 = AcquisitionResidual(
            "select an unseen target-realizing extension in one proposal",
            S2.language, S2.policy, budget=1, cold_success=False)

        # Structural D negative: behavioural success cannot license an unrelated
        # policy. The policy must be derived from the prior certified kernel.
        wrong_policy = (4,)
        self.assertFalse(wrong_policy == learned_policy)
        with self.assertRaises(ValueError):
            certify_kernel_policy_update(S2, rho3, UpdatePolicy(wrong_policy),
                source_kernel=required1, warm_success=True,
                attachment="behaviour alone must not license D")

        repair3 = UpdatePolicy(learned_policy)
        certified3 = certify_kernel_policy_update(
            S2, rho3, repair3, source_kernel=required1,
            warm_success=acquisition_episode(repair3.new_policy)[1],
            attachment="prior certified kernel changes the next bounded acquisition")
        S3, token3 = compile_repair(S2, certified3)
        self.assertTrue(acquisition_episode(S3.policy)[1])
        S3_ablated = ablate(S3, token3)
        self.assertEqual(S3_ablated, S2)
        self.assertFalse(acquisition_episode(S3_ablated.policy)[1])

        print("CONSEQUENTIAL SINGLE CHAIN PASS H=2->1 minimal_E=PASS "
              "representation_unlock=PASS language_compile=PASS "
              "language_ablation=FAIL structural_D=PASS second_order_warm=PASS "
              "second_order_ablation=FAIL")


if __name__ == "__main__":
    unittest.main()
