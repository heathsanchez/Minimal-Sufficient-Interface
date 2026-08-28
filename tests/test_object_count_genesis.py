import itertools
import math
import unittest

from tests.test_multi_object_category_genesis import recover_typed_structure, verify_recovered_category
from tests.test_sparse_category_genesis import active_identify, response


def thin_category(n, edge_mask):
    primitive = [(i, j) for i in range(n) for j in range(i + 1, n)]
    edges = [e for bit, e in enumerate(primitive) if edge_mask & (1 << bit)]
    reach = [[False] * n for _ in range(n)]
    for i in range(n):
        reach[i][i] = True
    for i, j in edges:
        reach[i][j] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    arrows = [(i, j) for i in range(n) for j in range(n) if reach[i][j]]
    index = {a: k for k, a in enumerate(arrows)}
    return arrows, index


def presentation_table(arrows, index, shift):
    m = len(arrows)
    perm = {i: (i + shift) % m for i in range(m)}
    inv = {tok: i for i, tok in perm.items()}
    table = []
    for gtok in range(m):
        for ftok in range(m):
            g = arrows[inv[gtok]]
            f = arrows[inv[ftok]]
            if f[1] != g[0]:
                table.append(None)
            else:
                table.append(perm[index[(f[0], g[1])]])
    return tuple(table)


def mixed_universe():
    """Mix latent categories with 1..4 unknown objects behind anonymous tokens."""
    by_size = {}
    truth = {}
    for n in range(1, 5):
        edge_count = n * (n - 1) // 2
        for edge_mask in range(1 << edge_count):
            arrows, index = thin_category(n, edge_mask)
            m = len(arrows)
            for shift in range(m):
                table = presentation_table(arrows, index, shift)
                prior = truth.get(table)
                if prior is not None and prior != n:
                    raise AssertionError("same partial-composition table encoded two object counts")
                truth[table] = n
                by_size.setdefault(m, set()).add(table)
    return {m: tuple(sorted(v, key=repr)) for m, v in by_size.items()}, truth


class ObjectCountGenesis(unittest.TestCase):
    def test_residuals_infer_number_of_objects_not_just_homs(self):
        universes, truth = mixed_universe()
        worlds = 0
        exact = 0
        object_count_failures = 0
        category_failures = 0
        heldout = 0
        max_queries = 0

        for m, universe in sorted(universes.items()):
            for true_table in universe:
                worlds += 1
                survivors, asked = active_identify(true_table, universe, m)
                self.assertEqual(len(survivors), 1)
                predicted = survivors[0]
                if predicted == true_table:
                    exact += 1
                max_queries = max(max_queries, len(asked))
                unseen = [q for q in itertools.product(range(m), repeat=2) if q not in asked]
                self.assertGreater(len(unseen), 0)
                heldout += len(unseen)
                for q in unseen:
                    self.assertEqual(response(predicted, m, q), response(true_table, m, q))

                table_dict = {
                    (g, f): response(predicted, m, (g, f))
                    for g in range(m) for f in range(m)
                }
                try:
                    ids, src, dst = recover_typed_structure(table_dict, m)
                except AssertionError:
                    category_failures += 1
                    continue
                if len(ids) != truth[true_table]:
                    object_count_failures += 1
                if not verify_recovered_category(table_dict, m, ids, src, dst):
                    category_failures += 1

        print(
            "object-count genesis: "
            f"worlds={worlds}; exact={exact}; heldout_cells={heldout}; "
            f"max_queries={max_queries}; object_count_failures={object_count_failures}; "
            f"category_failures={category_failures}"
        )
        self.assertGreater(worlds, 0)
        self.assertEqual(exact, worlds)
        self.assertGreater(heldout, 0)
        self.assertEqual(object_count_failures, 0)
        self.assertEqual(category_failures, 0)


if __name__ == "__main__":
    unittest.main()
