import unittest

from consequential_certification import (
    certify_finite_table_language_extension,
    certify_language_extension,
    certify_policy_update,
    certify_representation_repair,
)
from consequential_core import (
    AcquisitionResidual,
    ClosureCertificate,
    ClosureResidual,
    CoupledRepair,
    DevelopmentState,
    EquivalenceRelation,
    ExtendLanguage,
    PairResidual,
    UpdatePolicy,
    ablate,
    compile_repair,
    quotient_admissible,
)
from consequential_version_space import (
    coarsest_representation_repairs,
    discriminating_pairs,
    update_version_space_from_pair_answer,
)


def kernel_fingerprint(rel):
    """Domain policy feature; not part of the representation/repair kernel."""
    unseen = set(rel.carrier)
    sizes = []
    while unseen:
        x = min(unseen)
        block = {y for y in rel.carrier if rel.same(x, y)}
        sizes.append(len(block))
        unseen -= block
    return tuple(sorted(sizes))


class ConsequentialSingleChain(unittest.TestCase):
    def test_non_repairs_are_rejected_on_the_shared_path(self):
        X = tuple(range(4))
        old_E = EquivalenceRelation.from_partition(X, ({0, 1, 2}, {3}))
        rho = PairResidual(0, 1, old_E, consequence_left=0, consequence_right=1)

        good_E = EquivalenceRelation.from_partition(X, ({0}, {1, 2}, {3}))
        alternative_E = EquivalenceRelation.from_partition(X, ({0, 2}, {1}, {3}))
        S = DevelopmentState(
            X,
            active_representation=old_E,
            version_space=(good_E, alternative_E),
            language=("id",),
        )

        bad = CoupledRepair(new_representation=old_E, new_version_space=(old_E,))
        with self.assertRaises(ValueError):
            certify_representation_repair(
                S,
                rho,
                bad,
                experiment_pair=(0, 2),
                observed_same=False,
                attachment="should be rejected",
            )

        with self.assertRaises(ValueError):
            certify_representation_repair(
                S,
                rho,
                CoupledRepair(new_representation=good_E, new_version_space=(good_E,)),
                experiment_pair=(0, 2),
                observed_same=True,
                attachment="wrong survivor",
            )

        required = alternative_E
        closure = ClosureCertificate(
            interactions=("id",),
            complete=True,
            regime="identity-only",
            language_snapshot=S.language,
        )
        rho_closure = ClosureResidual(required, (old_E,), closure)
        with self.assertRaises(ValueError):
            certify_language_extension(
                S,
                rho_closure,
                ExtendLanguage("sham"),
                realized_required_kernel=old_E,
                lawful_under_active_representation=True,
                attachment="wrong kernel",
            )

        with self.assertRaises(ValueError):
            certify_finite_table_language_extension(
                S,
                rho_closure,
                ExtendLanguage(("wrong-artifact", (0, 1, 2, 3))),
                executable_table=(0, 0, 2, 3),
                attachment="delta/table mismatch",
            )

    def test_representation_to_language_to_second_order_development(self):
        X = tuple(range(4))
        old_E = EquivalenceRelation.from_partition(X, ({0, 1, 2}, {3}))
        rho1 = PairResidual(0, 1, old_E, consequence_left=0, consequence_right=1)

        pre = DevelopmentState(X, active_representation=old_E, language=("id",))
        dynamics = (lambda _z: 0,)
        H0 = coarsest_representation_repairs(pre, rho1, dynamics)
        self.assertEqual(len(H0), 2)
        self.assertTrue(all(h.strictly_refines(old_E) for h in H0))

        S0 = DevelopmentState(
            X,
            active_representation=old_E,
            version_space=H0,
            language=("id",),
            policy=None,
        )

        probes = discriminating_pairs(H0)
        self.assertTrue(probes)
        # Pick an explicit available discriminating experiment; do not rely on
        # implementation sort order to select the developmental branch.
        probe = (0, 2)
        self.assertIn(probe, probes)
        observed_same = True
        survivors = update_version_space_from_pair_answer(
            H0, probe, observed_same=observed_same
        )
        self.assertEqual(len(survivors), 1)
        selected = survivors[0]

        repair1 = CoupledRepair(
            new_representation=selected,
            new_version_space=(selected,),
        )
        certified1 = certify_representation_repair(
            S0,
            rho1,
            repair1,
            experiment_pair=probe,
            observed_same=observed_same,
            attachment=f"verified experiment {probe} collapses residual-relative H",
        )
        S1, token1 = compile_repair(S0, certified1)
        self.assertEqual(S1.active_representation, selected)
        self.assertEqual(S1.version_space, (selected,))

        action_table = (0, 3, 2, 3)
        action = lambda z: action_table[z]
        self.assertFalse(quotient_admissible(action, old_E))
        self.assertTrue(quotient_admissible(action, selected))

        required1 = EquivalenceRelation.from_observation(X, action)
        identity_kernel = EquivalenceRelation.from_observation(X, lambda z: z)
        self.assertNotEqual(required1, identity_kernel)
        closure1 = ClosureCertificate(
            interactions=("id",),
            complete=True,
            regime="one-step identity-only executable language",
            language_snapshot=S1.language,
        )
        rho2 = ClosureResidual(required1, (identity_kernel,), closure1)

        executable_delta = ("licensed_action", action_table)
        repair2 = ExtendLanguage(executable_delta)
        certified2 = certify_finite_table_language_extension(
            S1,
            rho2,
            repair2,
            executable_table=action_table,
            attachment="new quotient makes the executable operator lawful",
        )
        S2, token2 = compile_repair(S1, certified2)

        def executable_capability(state):
            return (
                executable_delta in state.language
                and state.active_representation is not None
                and quotient_admissible(action, state.active_representation)
            )

        self.assertFalse(executable_capability(S1))
        self.assertTrue(executable_capability(S2))
        S2_without_language = ablate(S2, token2)
        self.assertEqual(S2_without_language, S1)
        self.assertFalse(executable_capability(S2_without_language))

        self.assertEqual(ablate(S1, token1), S0)
        self.assertFalse(quotient_admissible(action, S0.active_representation))

        learned_policy = kernel_fingerprint(required1)
        self.assertEqual(learned_policy, (1, 1, 2))

        future_tables = {
            "future_bad": (0, 1, 2, 3),
            "future_good": (0, 1, 1, 2),
        }
        future_kernels = {
            name: EquivalenceRelation.from_observation(X, lambda i, t=table: t[i])
            for name, table in future_tables.items()
        }
        future_target = future_kernels["future_good"]
        self.assertNotEqual(future_target, required1)
        self.assertEqual(kernel_fingerprint(future_target), learned_policy)
        self.assertNotEqual(kernel_fingerprint(future_kernels["future_bad"]), learned_policy)

        def acquisition_episode(policy):
            order = ("future_bad", "future_good")
            if policy is None:
                chosen = order[0]
            else:
                matches = [
                    q for q in order
                    if kernel_fingerprint(future_kernels[q]) == policy
                ]
                chosen = matches[0] if matches else order[0]
            return chosen, future_kernels[chosen] == future_target

        cold_choice, cold_success = acquisition_episode(S2.policy)
        self.assertEqual(cold_choice, "future_bad")
        self.assertFalse(cold_success)

        rho3 = AcquisitionResidual(
            task="select an unseen target-realizing extension in one proposal",
            language_snapshot=S2.language,
            policy_snapshot=S2.policy,
            budget=1,
            cold_success=False,
        )
        repair3 = UpdatePolicy(learned_policy)
        warm_success_before_compile = acquisition_episode(repair3.new_policy)[1]
        certified3 = certify_policy_update(
            S2,
            rho3,
            repair3,
            warm_success=warm_success_before_compile,
            attachment="prior successful repair changes the next bounded acquisition",
        )
        S3, token3 = compile_repair(S2, certified3)

        warm_choice, warm_success = acquisition_episode(S3.policy)
        self.assertEqual(warm_choice, "future_good")
        self.assertTrue(warm_success)

        S3_ablated = ablate(S3, token3)
        self.assertEqual(S3_ablated, S2)
        self.assertFalse(acquisition_episode(S3_ablated.policy)[1])

        print(
            "CONSEQUENTIAL SINGLE CHAIN PASS "
            "H=2->1 representation_unlock=PASS language_compile=PASS "
            "language_ablation=FAIL second_order_warm=PASS "
            "second_order_ablation=FAIL"
        )


if __name__ == "__main__":
    unittest.main()
