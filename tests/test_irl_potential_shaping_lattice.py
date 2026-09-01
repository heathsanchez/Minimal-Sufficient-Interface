import itertools
import unittest
from collections import Counter
from fractions import Fraction


GAMMA = Fraction(1, 2)
VALUES = (-1, 0, 1)


def sign(x):
    return -1 if x < 0 else (1 if x > 0 else 0)


def path_returns(reward):
    """Two deterministic two-step paths from a common start to terminal.

    reward = (r01, r1T, r02, r2T).  Path A is 0->1->T and path B is
    0->2->T.  The terminal potential is frozen to zero.
    """
    r01, r1t, r02, r2t = reward
    return (
        Fraction(r01) + GAMMA * Fraction(r1t),
        Fraction(r02) + GAMMA * Fraction(r2t),
    )


def return_difference(reward):
    a, b = path_returns(reward)
    return a - b


def optimal_choice(reward):
    return sign(return_difference(reward))


def shape(reward, potential):
    """Potential-based shaping r' = r + gamma*Phi(s') - Phi(s)."""
    r01, r1t, r02, r2t = reward
    p0, p1, p2 = potential
    pT = 0
    return (
        Fraction(r01) + GAMMA * p1 - p0,
        Fraction(r1t) + GAMMA * pT - p1,
        Fraction(r02) + GAMMA * p2 - p0,
        Fraction(r2t) + GAMMA * pT - p2,
    )


def kernel(obs):
    n = len(obs)
    return tuple(tuple(obs[i] == obs[j] for j in range(n)) for i in range(n))


def refines(finer, coarser):
    return all(
        not finer[i][j] or coarser[i][j]
        for i in range(len(finer))
        for j in range(len(finer))
    )


def strict_refines(finer, coarser):
    return refines(finer, coarser) and finer != coarser


def ambiguity(obs):
    counts = Counter(obs)
    return sum(n * (n - 1) // 2 for n in counts.values())


class IRLPotentialShapingLattice(unittest.TestCase):
    def setUp(self):
        self.rewards = tuple(itertools.product(VALUES, repeat=4))
        self.potentials = tuple(itertools.product(VALUES, repeat=3))
        self.diff = tuple(return_difference(r) for r in self.rewards)
        self.choice = tuple(optimal_choice(r) for r in self.rewards)
        self.identity = self.rewards

    def test_01_all_potential_shaping_interventions_preserve_return_difference(self):
        checked = 0
        changed_concrete_rewards = 0
        for reward in self.rewards:
            base_diff = return_difference(reward)
            for potential in self.potentials:
                shaped = shape(reward, potential)
                self.assertEqual(return_difference(shaped), base_diff)
                checked += 1
                if shaped != tuple(map(Fraction, reward)):
                    changed_concrete_rewards += 1
        self.assertEqual(checked, 81 * 27)
        self.assertGreater(changed_concrete_rewards, 0)
        print(
            "IRL_SHAPING_01 PASS interventions=2187 return_difference_invariant=true "
            f"changed_concrete_rewards={changed_concrete_rewards}"
        )

    def test_02_all_potential_shaping_interventions_preserve_optimal_choice(self):
        for reward in self.rewards:
            base_choice = optimal_choice(reward)
            for potential in self.potentials:
                self.assertEqual(optimal_choice(shape(reward, potential)), base_choice)
        print("IRL_SHAPING_02 PASS interventions=2187 optimal_choice_invariant=true")

    def test_03_telescoping_shift_is_common_across_paths(self):
        checked = 0
        for reward in self.rewards:
            a, b = path_returns(reward)
            for potential in self.potentials:
                p0, _p1, _p2 = potential
                sa, sb = path_returns(shape(reward, potential))
                self.assertEqual(sa - a, -p0)
                self.assertEqual(sb - b, -p0)
                checked += 1
        self.assertEqual(checked, 2187)
        print("IRL_SHAPING_03 PASS telescoping_common_shift=-Phi(start) checks=2187")

    def test_04_data_source_refinement_lattice_is_strict(self):
        k_choice = kernel(self.choice)
        k_diff = kernel(self.diff)
        k_full = kernel(self.identity)
        self.assertTrue(strict_refines(k_diff, k_choice))
        self.assertTrue(strict_refines(k_full, k_diff))
        self.assertEqual(len(set(self.choice)), 3)
        self.assertEqual(len(set(self.diff)), 13)
        self.assertEqual(len(set(self.identity)), 81)
        print(
            "IRL_SHAPING_04 PASS lattice=full<return_difference<optimal_choice "
            "classes=81>13>3"
        )

    def test_05_ambiguity_decreases_monotonically_with_interface_richness(self):
        a_choice = ambiguity(self.choice)
        a_diff = ambiguity(self.diff)
        a_full = ambiguity(self.identity)
        self.assertEqual((a_choice, a_diff, a_full), (1200, 310, 0))
        self.assertGreater(a_choice, a_diff)
        self.assertGreater(a_diff, a_full)
        print("IRL_SHAPING_05 PASS ambiguity=1200_to_310_to_0")

    def test_06_failed_factorization_from_choice_to_return_difference_has_exact_residuals(self):
        residuals = tuple(
            (i, j)
            for i in range(81)
            for j in range(i + 1, 81)
            if self.choice[i] == self.choice[j] and self.diff[i] != self.diff[j]
        )
        self.assertEqual(len(residuals), 890)
        i, j = residuals[0]
        self.assertEqual(self.choice[i], self.choice[j])
        self.assertNotEqual(self.diff[i], self.diff[j])
        print("IRL_SHAPING_06 PASS choice_to_return_residuals=890")

    def test_07_msi_meet_repair_recovers_return_difference_kernel_exactly(self):
        k_choice = kernel(self.choice)
        k_diff = kernel(self.diff)
        meet = tuple(
            tuple(k_choice[i][j] and k_diff[i][j] for j in range(81))
            for i in range(81)
        )
        self.assertEqual(meet, k_diff)
        print("IRL_SHAPING_07 PASS MSI_meet_repair=return_difference_kernel")

    def test_08_full_reward_identity_is_not_required_for_choice_downstream(self):
        for d in set(self.diff):
            outcomes = {
                self.choice[i]
                for i, observed in enumerate(self.diff)
                if observed == d
            }
            self.assertEqual(len(outcomes), 1)
        self.assertEqual(kernel(tuple((d, sign(d)) for d in self.diff)), kernel(self.diff))
        print("IRL_SHAPING_08 PASS representative_reward_identity_unneeded_for_choice=true")

    def test_09_absolute_reward_query_forces_refinement_beyond_shaping_invariance(self):
        # Protecting one literal transition reward is deliberately not shaping-invariant.
        literal_r01 = tuple(r[0] for r in self.rewards)
        residuals = tuple(
            (i, j)
            for i in range(81)
            for j in range(i + 1, 81)
            if self.diff[i] == self.diff[j] and literal_r01[i] != literal_r01[j]
        )
        self.assertTrue(residuals)
        repaired = tuple(zip(self.diff, literal_r01))
        self.assertTrue(strict_refines(kernel(repaired), kernel(self.diff)))
        print(
            "IRL_SHAPING_09 PASS noninvariant_literal_query_forces_new_distinction "
            f"residuals={len(residuals)}"
        )

    def test_10_potential_shaping_is_realization_change_without_quotient_change(self):
        # Concrete reward maps vary while the protected return-difference quotient stays fixed.
        shaped_vectors = set()
        for reward in self.rewards:
            d = return_difference(reward)
            for potential in self.potentials:
                shaped = shape(reward, potential)
                shaped_vectors.add(shaped)
                self.assertEqual(return_difference(shaped), d)
        self.assertEqual(len(shaped_vectors), 1297)
        self.assertGreater(len(shaped_vectors), len(self.rewards))
        print(
            "IRL_SHAPING_10 PASS concrete_shaped_rewards=1297 base_rewards=81 "
            "protected_quotient_unchanged=true"
        )


if __name__ == "__main__":
    unittest.main()
