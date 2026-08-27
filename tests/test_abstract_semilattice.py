from __future__ import annotations

import itertools
import unittest


class AbstractMeetSemilatticeKernel(unittest.TestCase):
    """Tests the state-update kernel using only (L, meet, top).

    We use a powerset meet-semilattice as an abstract model.  Its elements are
    not presented as equivalence relations on a common state space; meet is
    ordinary set intersection and top is the full carrier.
    """

    def test_all_three_generator_families_on_powerset3(self) -> None:
        atoms = frozenset({0, 1, 2})
        L = tuple(
            frozenset(s)
            for r in range(4)
            for s in itertools.combinations(atoms, r)
        )
        top = atoms

        def meet(a, b):
            return a & b

        def leq(a, b):
            # refinement order: a <= b iff a is at least as informative/fine.
            return meet(a, b) == a

        # Exhaust all ordered 3-generator families: 8^3 = 512.
        for generators in itertools.product(L, repeat=3):
            target = top
            for k in generators:
                target = meet(target, k)

            # Exhaust all retained subsets of the three generators.
            for mask in range(8):
                retained = [generators[i] for i in range(3) if mask & (1 << i)]
                current = top
                for k in retained:
                    current = meet(current, k)

                # Abstract update law and monotone descent.
                for k in L:
                    updated = meet(current, k)
                    self.assertTrue(leq(updated, current))
                    self.assertEqual(meet(updated, k), updated)  # idempotence

                # Exact stopping/witness theorem for a finitely generated target:
                # current == target iff no unretained generator strictly refines it.
                unretained = [generators[i] for i in range(3) if not mask & (1 << i)]
                witnesses = [k for k in unretained if meet(current, k) != current]
                self.assertEqual(current == target, len(witnesses) == 0)

                # Any witness gives strict progress.
                for k in witnesses:
                    nxt = meet(current, k)
                    self.assertNotEqual(nxt, current)
                    self.assertTrue(leq(nxt, current))

                # Repeatedly adding any available witness terminates at target.
                state = current
                remaining = list(unretained)
                steps = 0
                while state != target:
                    witness = next(k for k in remaining if meet(state, k) != state)
                    state = meet(state, witness)
                    remaining.remove(witness)
                    steps += 1
                    self.assertLessEqual(steps, len(unretained))
                self.assertEqual(state, target)

    def test_kernel_laws_need_only_meet_axioms(self) -> None:
        # A second abstract semilattice: positive divisors of 30 under gcd.
        # This is intentionally unrelated to partitions/equivalence relations.
        import math

        L = (1, 2, 3, 5, 6, 10, 15, 30)
        top = 30
        meet = math.gcd

        for a in L:
            self.assertEqual(meet(a, a), a)
            self.assertEqual(meet(a, top), a)
            for b in L:
                self.assertEqual(meet(a, b), meet(b, a))
                self.assertIn(meet(a, b), L)
                for c in L:
                    self.assertEqual(meet(meet(a, b), c), meet(a, meet(b, c)))

        # Order-independence and duplicate-insensitivity follow from the laws.
        for family in itertools.product(L, repeat=3):
            values = []
            for perm in itertools.permutations(family):
                x = top
                for k in perm:
                    x = meet(x, k)
                values.append(x)
            self.assertEqual(len(set(values)), 1)

            x = top
            for k in family:
                x = meet(x, k)
            for k in family:
                self.assertEqual(meet(x, k), x)


if __name__ == "__main__":
    unittest.main()
