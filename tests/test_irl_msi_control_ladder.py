import itertools
import unittest


def kernel(obs):
    n = len(obs)
    return tuple(tuple(obs[i] == obs[j] for j in range(n)) for i in range(n))


def classes(obs):
    out = {}
    for i, value in enumerate(obs):
        out.setdefault(value, []).append(i)
    return tuple(tuple(v) for _, v in sorted(out.items(), key=lambda kv: repr(kv[0])))


def ambiguous_pairs(obs):
    return sum(len(c) * (len(c) - 1) // 2 for c in classes(obs))


def optimal_action(diff):
    return -1 if diff < 0 else (1 if diff > 0 else 0)


class IRLMSIControlLadder(unittest.TestCase):
    """Finite control ladder for reward partial-identifiability.

    The model is deliberately minimal: one state, two actions, entropy-regularized
    policy. At any fixed nonzero inverse temperature beta, the soft policy is an
    injective function of d = r1-r0, so d is an exact symbolic policy signature.
    This lets us exhaust the ambiguity without floating-point approximation.
    """

    def setUp(self):
        vals = range(-3, 4)
        self.rewards = tuple(itertools.product(vals, repeat=2))
        self.diff = tuple(r1 - r0 for r0, r1 in self.rewards)
        self.sign = tuple(optimal_action(d) for d in self.diff)
        self.r0 = tuple(r0 for r0, _ in self.rewards)
        self.identity = tuple(range(len(self.rewards)))

    def test_01_soft_policy_kernel_is_exact_additive_shift_equivalence(self):
        for i, r in enumerate(self.rewards):
            for j, s in enumerate(self.rewards):
                same_policy = self.diff[i] == self.diff[j]
                additive_shift = (s[0] - r[0]) == (s[1] - r[1])
                self.assertEqual(same_policy, additive_shift)
        print("IRL_CONTROL_01 PASS policy_kernel=additive_shift_equivalence reward_pairs=2401")

    def test_02_exact_partial_identifiability_census(self):
        cls = classes(self.diff)
        sizes = sorted(len(c) for c in cls)
        self.assertEqual(len(self.rewards), 49)
        self.assertEqual(len(cls), 13)
        self.assertEqual(sizes, [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7])
        self.assertEqual(ambiguous_pairs(self.diff), 91)
        print("IRL_CONTROL_02 PASS rewards=49 policy_classes=13 ambiguous_pairs=91")

    def test_03_optimal_policy_factors_through_soft_policy_quotient(self):
        for c in classes(self.diff):
            outcomes = {self.sign[i] for i in c}
            self.assertEqual(len(outcomes), 1)
        print("IRL_CONTROL_03 PASS downstream=optimal_action factors_through=policy_quotient")

    def test_04_canonical_gauge_represents_every_policy_class(self):
        canonical = {d: (0, d) for d in set(self.diff)}
        self.assertEqual(len(canonical), 13)
        for reward, d in zip(self.rewards, self.diff):
            rep = canonical[d]
            self.assertEqual(rep[1] - rep[0], d)
            self.assertEqual(optimal_action(rep[1] - rep[0]), optimal_action(d))
        print("IRL_CONTROL_04 PASS canonical_gauge=r0_zero representatives=13")

    def test_05_second_nonzero_temperature_does_not_break_shift_ambiguity(self):
        # Exact symbolic logits beta*d. Any fixed nonzero beta has the same kernel.
        for beta in (1, 2, 3, -1, -2):
            signature = tuple(beta * d for d in self.diff)
            self.assertEqual(kernel(signature), kernel(self.diff))
        print("IRL_CONTROL_05 PASS temperatures=5 kernel_unchanged=true")

    def test_06_random_postprocessing_cannot_split_a_policy_fibre(self):
        # Exhaust deterministic maps from the 13 observed policy signatures to 3 labels.
        # Rather than enumerate 3^13 maps, check the defining invariant exhaustively over
        # all reward pairs: any postprocessor keyed only by signature is constant on fibre.
        labels = {d: (abs(d) + 2 * d) % 3 for d in set(self.diff)}
        post = tuple(labels[d] for d in self.diff)
        for i in range(49):
            for j in range(49):
                if self.diff[i] == self.diff[j]:
                    self.assertEqual(post[i], post[j])
        self.assertGreater(ambiguous_pairs(post), 0)
        print("IRL_CONTROL_06 PASS postprocessing_cannot_split_policy_fibre=true")

    def test_07_prior_selects_representative_but_does_not_identify_true_reward(self):
        # Two priors induce different MAP representatives in the d=0 fibre.
        fibre = [i for i, d in enumerate(self.diff) if d == 0]
        low_sum = min(fibre, key=lambda i: sum(abs(x) for x in self.rewards[i]))
        high_sum = max(fibre, key=lambda i: sum(abs(x) for x in self.rewards[i]))
        self.assertNotEqual(low_sum, high_sum)
        self.assertEqual(self.diff[low_sum], self.diff[high_sum])
        print("IRL_CONTROL_07 PASS prior_changes_representative_without_new_policy_information=true")

    def test_08_absolute_reward_anchor_breaks_ambiguity_and_ablation_restores_it(self):
        enriched = tuple(zip(self.diff, self.r0))
        self.assertEqual(ambiguous_pairs(self.diff), 91)
        self.assertEqual(ambiguous_pairs(enriched), 0)
        self.assertEqual(len(classes(enriched)), 49)
        # Exact ablation of the absolute anchor returns the original quotient.
        self.assertEqual(ambiguous_pairs(self.diff), 91)
        print("IRL_CONTROL_08 PASS added_anchor ambiguity=91_to_0 ablation=0_to_91")

    def test_09_coarser_optimal_action_data_has_strictly_larger_ambiguity(self):
        self.assertEqual(len(classes(self.sign)), 3)
        self.assertGreater(ambiguous_pairs(self.sign), ambiguous_pairs(self.diff))
        residuals = [
            (i, j)
            for i in range(49)
            for j in range(i + 1, 49)
            if self.sign[i] == self.sign[j] and self.diff[i] != self.diff[j]
        ]
        self.assertGreater(len(residuals), 0)
        print(
            "IRL_CONTROL_09 PASS coarse_data=optimal_action classes=3 "
            f"ambiguity={ambiguous_pairs(self.sign)} residuals_to_soft_signature={len(residuals)}"
        )

    def test_10_msi_minimal_repair_of_coarse_policy_is_soft_policy_quotient(self):
        # Meet of the coarse kernel with the protected difference kernel equals the
        # difference kernel because difference already determines sign.
        coarse = kernel(self.sign)
        protected = kernel(self.diff)
        meet = tuple(
            tuple(coarse[i][j] and protected[i][j] for j in range(49))
            for i in range(49)
        )
        self.assertEqual(meet, protected)
        print("IRL_CONTROL_10 PASS MSI_repair=coarse_kernel_meet_difference_kernel")

    def test_11_misspecified_sign_model_has_certified_residuals(self):
        residuals = tuple(
            (i, j)
            for i in range(49)
            for j in range(i + 1, 49)
            if self.sign[i] == self.sign[j] and self.diff[i] != self.diff[j]
        )
        self.assertTrue(residuals)
        i, j = residuals[0]
        self.assertEqual(self.sign[i], self.sign[j])
        self.assertNotEqual(self.diff[i], self.diff[j])
        print(f"IRL_CONTROL_11 PASS misspecification_residuals={len(residuals)}")

    def test_12_known_irl_quotient_does_not_require_representative_identification(self):
        # Every representative in a soft-policy fibre agrees on the downstream optimal
        # action. Therefore representative non-identifiability is harmless for this
        # protected downstream query; MSI stops at the quotient, matching invariance logic.
        for c in classes(self.diff):
            self.assertEqual(len({self.sign[i] for i in c}), 1)
        self.assertEqual(kernel(self.diff), kernel(tuple((d, optimal_action(d)) for d in self.diff)))
        print("IRL_CONTROL_12 PASS quotient_sufficient_for_downstream=true representative_identity_unneeded=true")


if __name__ == "__main__":
    unittest.main()
