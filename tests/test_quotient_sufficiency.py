import math
import unittest

from msi.core import finite_factors_through, finite_quotient_counterexample


class QuotientSufficiencyTests(unittest.TestCase):
    def test_period_lattice_pair_refutes_coarse_factorization(self) -> None:
        k1 = (4, 0, 4, 0)
        k2 = (4, 4, 0, 0)
        situations = (k1, k2)

        def histogram(k: tuple[int, ...]) -> tuple[int, ...]:
            return tuple(k.count(i) for i in range(5))

        def multiplicity(k: tuple[int, ...]) -> int:
            out = 1
            for cls in k:
                out *= math.comb(4, cls)
            return out

        def mean_numerator(k: tuple[int, ...]) -> int:
            return sum(2 * cls - 4 for cls in k)

        def coarse(k: tuple[int, ...]) -> tuple[tuple[int, ...], int, int]:
            return histogram(k), multiplicity(k), mean_numerator(k)

        chi = (1, -1, 1, -1)

        def staggered_numerator(k: tuple[int, ...]) -> int:
            return sum(sign * (2 * cls - 4) for sign, cls in zip(chi, k))

        self.assertEqual(coarse(k1), coarse(k2))
        self.assertEqual(coarse(k1), ((2, 0, 0, 0, 2), 1, 0))
        self.assertEqual(staggered_numerator(k1), 16)
        self.assertEqual(staggered_numerator(k2), 0)
        self.assertEqual(
            finite_quotient_counterexample(situations, coarse, staggered_numerator),
            (k1, k2),
        )
        self.assertFalse(finite_factors_through(situations, coarse, staggered_numerator))

    def test_no_counterexample_when_target_is_quotient_function(self) -> None:
        situations = tuple(range(12))
        quotient = lambda x: x % 3
        target = lambda x: (x % 3) * 10

        self.assertIsNone(
            finite_quotient_counterexample(situations, quotient, target)
        )
        self.assertTrue(finite_factors_through(situations, quotient, target))


if __name__ == "__main__":
    unittest.main()
