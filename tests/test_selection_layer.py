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
        # Exhaustive small-universe census, implemented directly for speed.
        n = m = 4

        def rows_from_mask(mask):
            return tuple(tuple((mask >> (i*m + c)) & 1 for c in range(m)) for i in range(n))

        def partition(rows, basis_mask):
            groups = {}
            for i, row in enumerate(rows):
                sig = tuple(row[c] for c in range(m) if (basis_mask >> c) & 1)
                groups.setdefault(sig, []).append(i)
            return tuple(sorted(tuple(v) for v in groups.values()))

        def relation_size_from_partition(p):
            return sum(len(g) * len(g) for g in p)

        for mask in range(1 << (n*m)):
            rows = rows_from_mask(mask)
            target = partition(rows, (1 << m) - 1)

            optimum = None
            for r in range(m + 1):
                for cols in itertools.combinations(range(m), r):
                    bmask = sum(1 << c for c in cols)
                    if partition(rows, bmask) == target:
                        optimum = r
                        break
                if optimum is not None:
                    break

            bmask = 0
            greedy_len = 0
            while partition(rows, bmask) != target:
                cur = partition(rows, bmask)
                cur_size = relation_size_from_partition(cur)
                choices = []
                for c in range(m):
                    if (bmask >> c) & 1:
                        continue
                    nxt = partition(rows, bmask | (1 << c))
                    gain = cur_size - relation_size_from_partition(nxt)
                    if gain > 0:
                        choices.append((gain, -c, c))
                self.assertTrue(choices)
                c = max(choices)[2]
                bmask |= 1 << c
                greedy_len += 1

            self.assertEqual(greedy_len, optimum)

    def test_pair_gain_greedy_is_not_globally_optimal(self):
        # Counterexample at |X|=5, |C|=4.
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
        greedy_first = self.greedy_pair_basis(I)[0]
        self.assertEqual(1 + future_cost((greedy_first,)), 3)
        better = [c for c in I.continuations if 1 + future_cost((c,)) == 2]
        self.assertTrue(better)


if __name__ == "__main__":
    unittest.main()
