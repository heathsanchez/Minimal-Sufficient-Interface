import itertools
import unittest
from functools import lru_cache

from msi.core import Interface


class CostedSelectionLayer(unittest.TestCase):
    @staticmethod
    def interface_from_rows(rows):
        X = tuple(range(len(rows)))
        C = tuple(range(len(rows[0])))
        return Interface(X, C, lambda x, c: rows[x][c])

    @staticmethod
    def immediate_pair_gain(I, basis, c):
        before = I.relation(basis)
        after = I.relation(tuple(basis) + (c,))
        return len(before) - len(after)

    @staticmethod
    def greedy_pair_basis(I):
        B = []
        while not I.sufficient(B):
            candidates = []
            for c in I.continuations:
                if c in B:
                    continue
                gain = CostedSelectionLayer.immediate_pair_gain(I, B, c)
                if gain > 0:
                    candidates.append((gain, -c, c))
            assert candidates
            B.append(max(candidates)[2])
        return tuple(B)

    def test_pair_gain_greedy_is_optimal_on_all_binary_4x4_worlds(self):
        # This is evidence about the small universe, not a theorem in general.
        n = m = 4
        checked = 0
        for bits in itertools.product((0, 1), repeat=n * m):
            rows = [bits[i*m:(i+1)*m] for i in range(n)]
            I = self.interface_from_rows(rows)
            g = self.greedy_pair_basis(I)
            optimum = I.minimum_basis()
            self.assertEqual(len(g), len(optimum))
            checked += 1
        self.assertEqual(checked, 2 ** 16)

    def test_pair_gain_greedy_is_not_globally_optimal(self):
        # Minimal counterexample found at |X|=5, |C|=4.
        rows = [
            (1, 1, 1, 0),
            (0, 1, 1, 0),
            (1, 0, 1, 0),
            (0, 0, 0, 0),
            (0, 0, 0, 0),
        ]
        I = self.interface_from_rows(rows)
        greedy = self.greedy_pair_basis(I)
        optimum = I.minimum_basis()
        self.assertEqual(len(optimum), 2)
        self.assertEqual(len(greedy), 3)

    def test_optimal_future_cost_is_residual_relative(self):
        rows = [
            (1, 1, 1, 0),
            (0, 1, 1, 0),
            (1, 0, 1, 0),
            (0, 0, 0, 0),
            (0, 0, 0, 0),
        ]
        I = self.interface_from_rows(rows)

        @lru_cache(None)
        def future_cost(B):
            B = tuple(B)
            if I.sufficient(B):
                return 0
            vals = []
            for c in I.continuations:
                if c in B:
                    continue
                if I.relation(B + (c,)) == I.relation(B):
                    continue
                vals.append(1 + future_cost(tuple(sorted(B + (c,)))))
            return min(vals)

        self.assertEqual(future_cost(tuple()), 2)
        # c2 has the largest immediate split under our deterministic tie-break,
        # but choosing it raises remaining total cost to 3 in this world.
        greedy_first = self.greedy_pair_basis(I)[0]
        self.assertEqual(1 + future_cost((greedy_first,)), 3)
        better = [c for c in I.continuations if 1 + future_cost((c,)) == 2]
        self.assertTrue(better)


if __name__ == "__main__":
    unittest.main()
