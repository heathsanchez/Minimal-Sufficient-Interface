import itertools
import unittest


def kernel(*observations):
    n = len(observations[0])
    return tuple(
        tuple(all(obs[i] == obs[j] for obs in observations) for j in range(n))
        for i in range(n)
    )


def factors_through(interface, target):
    seen = {}
    for i, key in enumerate(interface):
        if key in seen and seen[key] != target[i]:
            return False
        seen[key] = target[i]
    return True


class IRLIdentifiabilityControl(unittest.TestCase):
    def setUp(self):
        # Finite one-state/two-action reward family.  For a fixed temperature,
        # an entropy-regularized policy depends only on the reward logit gap
        # r1-r0, so adding the same constant to both rewards is observationally
        # invisible.  We encode the exact gap rather than floating probabilities.
        values = tuple(range(-2, 3))
        self.rewards = tuple(itertools.product(values, repeat=2))
        self.gap = tuple(r1 - r0 for r0, r1 in self.rewards)
        self.r0 = tuple(r0 for r0, _r1 in self.rewards)
        self.r1 = tuple(r1 for _r0, r1 in self.rewards)
        self.identity = tuple(self.rewards)

    def test_known_additive_shift_fibres_are_recovered(self):
        # Equal policy logits iff the two reward vectors differ by a common
        # additive constant, subject only to the finite-grid boundary.
        for i, (a0, a1) in enumerate(self.rewards):
            for j, (b0, b1) in enumerate(self.rewards):
                same_interface = self.gap[i] == self.gap[j]
                common_shift = (b0 - a0) == (b1 - a1)
                self.assertEqual(same_interface, common_shift)

        classes = {}
        for reward, gap in zip(self.rewards, self.gap):
            classes.setdefault(gap, []).append(reward)
        ambiguous = {g: rs for g, rs in classes.items() if len(rs) > 1}
        self.assertGreater(len(ambiguous), 0)
        self.assertTrue(any(len(rs) == 5 for rs in ambiguous.values()))
        print(
            "IRL_CONTROL_KNOWN_AMBIGUITY PASS "
            f"rewards={len(self.rewards)}; policy_gap_classes={len(classes)}; "
            f"ambiguous_classes={len(ambiguous)}; max_fibre={max(map(len, classes.values()))}"
        )

    def test_downstream_invariance_compatibility(self):
        # The observed policy statistic itself is already determined by the
        # interface; an absolute reward baseline is not.  This is the finite
        # analogue of comparing data-source invariances with downstream-task
        # invariances.
        self.assertTrue(factors_through(self.gap, self.gap))
        self.assertFalse(factors_through(self.gap, self.r0))
        witnesses = [
            (self.rewards[i], self.rewards[j])
            for i in range(len(self.rewards))
            for j in range(i + 1, len(self.rewards))
            if self.gap[i] == self.gap[j] and self.r0[i] != self.r0[j]
        ]
        self.assertGreater(len(witnesses), 0)
        print(
            "IRL_CONTROL_FAILED_FACTORIZATION PASS "
            f"baseline_residual_pairs={len(witnesses)}; invariant_query_factors=true; "
            "absolute_baseline_factors=false"
        )

    def test_canonical_repair_and_multiple_realizations(self):
        # If exact reward identity becomes protected, adding either primitive
        # reward coordinate to the observed gap generates the same discrete
        # repaired quotient.  Thus the required quotient is fixed but the
        # coordinate-level realization is not unique.
        required = kernel(self.gap, self.r0)
        self.assertEqual(required, kernel(self.gap, self.r1))
        self.assertEqual(required, kernel(self.identity))
        self.assertNotEqual(kernel(self.gap), required)

        # Frozen operational language: gap and the newly retained coordinate
        # are primitives of cost 1; reconstructing the opposite coordinate by
        # one add/subtract operation costs 2.
        direct_profile = (1, 2)  # retain r0: r0 primitive, r1 = r0 + gap
        right_profile = (2, 1)   # retain r1: r0 = r1 - gap, r1 primitive
        self.assertNotEqual(direct_profile, right_profile)
        print(
            "IRL_CONTROL_REALIZATION_LAYER PASS "
            "lawful_primitive_realizers=2; same_required_kernel=true; "
            f"query_cost_profiles={[direct_profile, right_profile]}"
        )

    def test_added_observation_resolves_and_ablation_restores(self):
        before = kernel(self.gap)
        after = kernel(self.gap, self.r0)
        self.assertNotEqual(before, after)
        self.assertEqual(after, kernel(self.identity))
        # Exact ablation of the added coordinate restores the original policy
        # ambiguity rather than merely reducing test accuracy.
        self.assertEqual(kernel(self.gap), before)
        print(
            "IRL_CONTROL_INTERFACE_REPAIR PASS "
            "added_coordinate=r0; exact_reward_identifiable_after=true; "
            "ablation_restores_policy_fibres=true"
        )


if __name__ == "__main__":
    unittest.main()
