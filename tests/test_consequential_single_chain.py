import unittest

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
    certify_repair,
    compile_repair,
    quotient_admissible,
    residual_resolved_by_representation,
)
from tests.test_difference_test import coarsest_lawful_repairs, distinguishing_pairs


def rel_from_partition(X, p):
    return EquivalenceRelation.from_partition(X, p)


def kernel_fingerprint(rel):
    unseen = set(rel.carrier)
    sizes = []
    while unseen:
        x = min(unseen)
        block = {y for y in rel.carrier if rel.same(x, y)}
        sizes.append(len(block))
        unseen -= block
    return tuple(sorted(sizes))


class ConsequentialSingleChain(unittest.TestCase):
    def test_representation_to_language_to_second_order_development(self):
        X = tuple(range(4))
        old_p = (frozenset({0, 1, 2}), frozenset({3}))
        old_E = EquivalenceRelation.from_partition(X, old_p)
        rho1 = PairResidual(0, 1, old_E, consequence_left=0, consequence_right=1)

        g = (0, 0, 0, 0)
        lawful, coarsest = coarsest_lawful_repairs(X, old_p, (0, 1), g)
        self.assertTrue(lawful)
        self.assertEqual(len(coarsest), 2)
        H0 = tuple(rel_from_partition(X, p) for p in coarsest)
        self.assertTrue(all(h.strictly_refines(old_E) for h in H0))

        S0 = DevelopmentState(
            X,
            active_representation=old_E,
            version_space=H0,
            language=("id",),
            policy=None,
        )

        probe_pairs = distinguishing_pairs(coarsest[0], coarsest[1])
        self.assertTrue(probe_pairs)
        probe = probe_pairs[0]
        observed_same = True
        survivors = tuple(h for h in H0 if h.same(*probe) == observed_same)
        self.assertEqual(len(survivors), 1)
        selected = survivors[0]

        repair1 = CoupledRepair(
            new_representation=selected,
            new_version_space=(selected,),
        )
        certified1 = certify_repair(
            S0,
            rho1,
            repair1,
            lambda _s, r, rho: (
                residual_resolved_by_representation(rho, r.new_representation)
                and r.new_version_space == (r.new_representation,)
            ),
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
        repair2 = ExtendLanguage("licensed_action")
        certified2 = certify_repair(
            S1,
            rho2,
            repair2,
            lambda s, r, rho: (
                r.delta == "licensed_action"
                and quotient_admissible(action, s.active_representation)
                and EquivalenceRelation.from_observation(X, action) == rho.required
            ),
            attachment="new quotient makes the new executable operator lawful",
        )
        S2, token2 = compile_repair(S1, certified2)

        def executable_capability(state):
            return (
                "licensed_action" in state.language
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
                matches = [q for q in order if kernel_fingerprint(future_kernels[q]) == policy]
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
        certified3 = certify_repair(
            S2,
            rho3,
            repair3,
            lambda _s, r, _rho: acquisition_episode(r.new_policy)[1],
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
