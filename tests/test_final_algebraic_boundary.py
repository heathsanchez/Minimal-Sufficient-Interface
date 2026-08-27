import itertools
import unittest


class FinalAlgebraicBoundary(unittest.TestCase):
    def test_top_not_needed_when_initial_state_is_supplied(self):
        # Powerset intersection gives a concrete idempotent commutative semigroup.
        universe = frozenset(range(3))
        elems = [frozenset(s) for r in range(4) for s in itertools.combinations(universe, r)]

        def meet(a, b):
            return a & b

        # Start from every possible externally supplied initial state, not from top.
        for e0 in elems:
            for ks in itertools.product(elems, repeat=3):
                # Sequential update depends only on the multiset of constraints.
                ref = e0
                for k in ks:
                    ref = meet(ref, k)
                for perm in set(itertools.permutations(ks)):
                    got = e0
                    for k in perm:
                        got = meet(got, k)
                    self.assertEqual(got, ref)
                # Duplicates are inert.
                for k in ks:
                    self.assertEqual(meet(meet(e0, k), k), meet(e0, k))
                # Every step is monotone under the induced order a <= b iff a∧b=a.
                cur = e0
                for k in ks:
                    nxt = meet(cur, k)
                    self.assertEqual(meet(nxt, cur), nxt)
                    cur = nxt

    def test_each_semilattice_law_is_independently_needed_for_the_corresponding_claim(self):
        # Non-idempotent: addition mod 2 is associative+commutative but duplicate-sensitive.
        xor = lambda a, b: a ^ b
        self.assertNotEqual(xor(xor(1, 1), 1), xor(1, 1))

        # Non-commutative: left projection is associative+idempotent but order-sensitive.
        left = lambda a, b: a
        self.assertNotEqual(left(0, 1), left(1, 0))

        # Non-associative: NAND is commutative but bracketing-sensitive.
        nand = lambda a, b: 1 - (a & b)
        witness = None
        for a, b, c in itertools.product([0, 1], repeat=3):
            if nand(nand(a, b), c) != nand(a, nand(b, c)):
                witness = (a, b, c)
                break
        self.assertIsNotNone(witness)

    def test_finite_convergence_needs_strict_progress_and_finiteness_not_top(self):
        # Divisors of 30 under gcd: start from arbitrary state.
        import math
        elems = [1, 2, 3, 5, 6, 10, 15, 30]
        for start in elems:
            for ks in itertools.product(elems, repeat=3):
                cur = start
                strict_steps = 0
                for k in ks:
                    nxt = math.gcd(cur, k)
                    if nxt != cur:
                        strict_steps += 1
                    cur = nxt
                # No strictly descending chain can exceed |L|-1.
                self.assertLessEqual(strict_steps, len(elems) - 1)

    def test_empty_family_requires_identity_only_if_we_want_canonical_uninformed_state(self):
        # With a supplied start, no identity is needed. To define fold(empty) canonically,
        # an identity/top element is needed. Intersection's identity is the universe.
        u = frozenset(range(3))
        elems = [frozenset(s) for r in range(4) for s in itertools.combinations(u, r)]
        for a in elems:
            self.assertEqual(a & u, a)
            self.assertEqual(u & a, a)


if __name__ == '__main__':
    unittest.main()
