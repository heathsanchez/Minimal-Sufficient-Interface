import itertools
import unittest

from tests.test_multi_object_category_genesis import (
    make_thin_category,
    recover_typed_structure,
    verify_recovered_category,
)


def all_presentations():
    """All distinct anonymous presentations of the bounded latent category family.

    Unlike the earlier cyclic-token test, this uses every token permutation.
    Candidates with identical observable partial-composition tables are quotiented
    extensionally before learning.
    """
    by_size = {}
    for edge_mask in range(8):
        arrows, index, compose = make_thin_category(3, edge_mask)
        m = len(arrows)
        for p in itertools.permutations(range(m)):
            # p[canonical_index] = anonymous token
            inv = {tok: i for i, tok in enumerate(p)}
            table = []
            for g_tok in range(m):
                for f_tok in range(m):
                    g = arrows[inv[g_tok]]
                    f = arrows[inv[f_tok]]
                    out = compose(g, f)
                    table.append(None if out is None else p[index[out]])
            by_size.setdefault(m, set()).add(tuple(table))
    return {m: tuple(sorted(ts, key=repr)) for m, ts in by_size.items()}


def response(table, m, q):
    g, f = q
    return table[g * m + f]


def choose_query(candidates, m, asked):
    """Minimax information query with a deterministic lexicographic tie-break."""
    best = None
    for q in itertools.product(range(m), repeat=2):
        if q in asked:
            continue
        buckets = {}
        for t in candidates:
            buckets.setdefault(response(t, m, q), 0)
            buckets[response(t, m, q)] += 1
        if len(buckets) <= 1:
            continue
        score = (max(buckets.values()), -len(buckets), q)
        if best is None or score < best[0]:
            best = (score, q)
    return None if best is None else best[1]


def active_identify(true_table, universe, m):
    candidates = list(universe)
    asked = {}
    while len(candidates) > 1:
        q = choose_query(candidates, m, asked)
        if q is None:
            break
        r = response(true_table, m, q)
        asked[q] = r
        candidates = [t for t in candidates if response(t, m, q) == r]
    # Extensional deduplication means one survivor is the exact withheld table.
    return candidates, asked


class SparseCategoryGenesis(unittest.TestCase):
    def test_sparse_residual_queries_recover_withheld_category(self):
        presentations = all_presentations()
        worlds = 0
        exact_recoveries = 0
        heldout_cells = 0
        max_queries = 0
        total_queries = 0
        recovery_failures = 0

        for m, universe in sorted(presentations.items()):
            self.assertGreater(len(universe), 0)
            for true_table in universe:
                worlds += 1
                survivors, asked = active_identify(true_table, universe, m)
                total_queries += len(asked)
                max_queries = max(max_queries, len(asked))
                self.assertEqual(len(survivors), 1)
                predicted = survivors[0]
                if predicted == true_table:
                    exact_recoveries += 1

                # The learner has not asked the full table: prediction is tested
                # on every withheld pair, not on the residuals used for selection.
                unseen = [
                    q for q in itertools.product(range(m), repeat=2)
                    if q not in asked
                ]
                self.assertGreater(len(unseen), 0)
                heldout_cells += len(unseen)
                for q in unseen:
                    self.assertEqual(response(predicted, m, q), response(true_table, m, q))

                table_dict = {
                    (g, f): response(predicted, m, (g, f))
                    for g in range(m) for f in range(m)
                }
                try:
                    ids, src, dst = recover_typed_structure(table_dict, m)
                except AssertionError:
                    recovery_failures += 1
                    continue
                if len(ids) != 3 or not verify_recovered_category(table_dict, m, ids, src, dst):
                    recovery_failures += 1

        print(
            "sparse category genesis: "
            f"worlds={worlds}; exact_recoveries={exact_recoveries}; "
            f"heldout_cells={heldout_cells}; total_queries={total_queries}; "
            f"max_queries={max_queries}; recovery_failures={recovery_failures}"
        )
        self.assertGreater(worlds, 0)
        self.assertEqual(exact_recoveries, worlds)
        self.assertGreater(heldout_cells, 0)
        self.assertEqual(recovery_failures, 0)
        # Every recovered category must require strictly fewer verifier answers
        # than blindly reading its full m^2 partial-composition table.
        for m, universe in presentations.items():
            for t in universe:
                _, asked = active_identify(t, universe, m)
                self.assertLess(len(asked), m * m)


if __name__ == "__main__":
    unittest.main()
