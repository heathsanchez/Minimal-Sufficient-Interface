import itertools
import unittest

from msi import Interface


def interface_from_bits(bits, n_x=3, n_c=3):
    table = [bits[i * n_c : (i + 1) * n_c] for i in range(n_x)]
    return Interface(
        situations=tuple(range(n_x)),
        continuations=tuple(range(n_c)),
        outcome=lambda x, c, t=table: t[x][c],
    )


class ExhaustiveFiniteKernel(unittest.TestCase):
    def test_all_binary_3x3_worlds(self):
        tables = 0
        basis_contexts = 0
        subset_refinement_checks = 0
        update_checks = 0
        stopping_checks = 0
        lawful_repairs = 0

        for flat in itertools.product((0, 1), repeat=9):
            I = interface_from_bits(flat)
            tables += 1
            C = I.continuations
            subsets = [
                tuple(c for c in C if mask & (1 << c))
                for mask in range(1 << len(C))
            ]

            full_rel = I.relation(C)

            for B in subsets:
                basis_contexts += 1
                rel_B = I.relation(B)

                # Equivalence laws.
                for x in I.situations:
                    self.assertIn((x, x), rel_B)
                for x, y in rel_B:
                    self.assertIn((y, x), rel_B)
                for x, y in rel_B:
                    for y2, z in rel_B:
                        if y == y2:
                            self.assertIn((x, z), rel_B)

                # Exact stopping theorem.
                witness = I.residual_witness(B)
                self.assertEqual(witness is None, rel_B == full_rel)
                stopping_checks += 1

                # One-step intersection/update law.
                for c in C:
                    lhs = I.relation(tuple(dict.fromkeys(B + (c,))))
                    kernel_c = frozenset(
                        (x, y)
                        for x in I.situations
                        for y in I.situations
                        if I.outcome(x, c) == I.outcome(y, c)
                    )
                    self.assertEqual(lhs, rel_B & kernel_c)
                    update_checks += 1

            # Monotonicity for every ordered subset inclusion.
            for B in subsets:
                set_B = set(B)
                for Bp in subsets:
                    if set_B.issubset(Bp):
                        self.assertTrue(I.relation(Bp).issubset(I.relation(B)))
                        subset_refinement_checks += 1

            # The deterministic reference repair must terminate at sufficiency.
            repaired = I.lawful_repair(())
            self.assertTrue(I.sufficient(repaired))
            self.assertLessEqual(len(repaired), len(C))
            lawful_repairs += 1

        self.assertEqual(tables, 512)
        self.assertEqual(basis_contexts, 4096)
        self.assertGreater(subset_refinement_checks, 0)
        self.assertEqual(update_checks, 12288)
        self.assertEqual(stopping_checks, 4096)
        self.assertEqual(lawful_repairs, 512)

    def test_local_silence_is_not_global_sufficiency(self):
        # x0,x1,x2 are silent under c0 and c1, but c2 separates x2.
        rows = ((0, 0, 0), (0, 0, 0), (0, 0, 1))
        I = Interface((0, 1, 2), (0, 1, 2), lambda x, c: rows[x][c])
        self.assertEqual(I.relation(()), I.relation((0,)))
        self.assertFalse(I.sufficient((0,)))
        self.assertEqual(I.relation((0,)), I.relation((0, 1)))
        self.assertFalse(I.sufficient((0, 1)))
        self.assertTrue(I.sufficient((2,)))

    def test_lawful_repair_need_not_be_minimum(self):
        rows = (
            (0, 0, 0, 0),
            (0, 0, 0, 1),
            (0, 0, 1, 0),
            (0, 1, 1, 1),
        )
        I = Interface(tuple(range(4)), tuple(range(4)), lambda x, c: rows[x][c])
        self.assertEqual(len(I.minimum_basis()), 2)
        # c1 then c2 then c3 is lawful but redundant relative to the 2-element optimum.
        B = ()
        for c in (1, 2, 3):
            witness_pairs = [
                (x, y)
                for x in I.situations
                for y in I.situations
                if I.equivalent(x, y, B)
                and not I.equivalent(x, y, I.continuations)
                and I.separates(c, x, y)
            ]
            self.assertTrue(witness_pairs)
            B = B + (c,)
        self.assertTrue(I.sufficient(B))
        self.assertEqual(len(B), 3)

    def test_quotient_descent_iff_congruence(self):
        rows = ((0, 0, 0), (0, 0, 0), (0, 0, 1))
        I = Interface((0, 1, 2), (0, 1, 2), lambda x, c: rows[x][c])
        B = (2,)

        good = lambda x: x
        self.assertTrue(I.preserves_equivalence(good, B))
        self.assertIsInstance(I.quotient_map(good, B), dict)

        bad_map = {0: 0, 1: 2, 2: 0}
        bad = lambda x: bad_map[x]
        self.assertFalse(I.preserves_equivalence(bad, B))
        with self.assertRaises(ValueError):
            I.quotient_map(bad, B)


if __name__ == "__main__":
    unittest.main()
