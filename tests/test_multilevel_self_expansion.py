import itertools
import unittest
from collections import Counter, defaultdict


def all_maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def permutations(n):
    return tuple(m for m in all_maps(n) if len(set(m)) == n)


def apply_word(word, f, g, x):
    y = x
    for symbol in reversed(word):
        y = (f if symbol == 0 else g)[y]
    return y


def make_rows(fs, gs, n, verifier):
    return [
        (f, g, x, verifier(f, g, x))
        for f in fs
        for g in gs
        for x in range(n)
    ]


def feature_tuple(row, features):
    f, g, x, _ = row
    return tuple(apply_word(word, f, g, x) for word in features)


def sufficient(rows, features):
    table = {}
    for row in rows:
        key = feature_tuple(row, features)
        y = row[3]
        if key in table and table[key] != y:
            return False
        table[key] = y
    return True


def residual_pair_count(rows, features):
    """Count conflicting row pairs in O(rows), without materialising all pairs."""
    buckets = defaultdict(Counter)
    for row in rows:
        buckets[feature_tuple(row, features)][row[3]] += 1

    total = 0
    for counts in buckets.values():
        seen = 0
        for count in counts.values():
            total += seen * count
            seen += count
    return total


def generated_depth2_candidates():
    return ((0, 0), (0, 1), (1, 0), (1, 1))


def discover_missing_probe(rows, current):
    """Find the smallest generated observation whose addition repairs current aliasing."""
    survivors = []
    for candidate in generated_depth2_candidates():
        if sufficient(rows, current + (candidate,)):
            survivors.append(candidate)
    if not survivors:
        return None, ()
    survivors = tuple(sorted(survivors))
    return survivors[0], survivors


def infer_minimal_signature(rows, features):
    """Infer the smallest tuple of available observations determining verifier output."""
    for size in range(1, len(features) + 1):
        for indices in itertools.combinations(range(len(features)), size):
            candidate = tuple(features[i] for i in indices)
            if sufficient(rows, candidate):
                return candidate
    return None


def synthesize_lookup(rows, signature):
    table = {}
    for row in rows:
        key = feature_tuple(row, signature)
        y = row[3]
        if key in table and table[key] != y:
            raise ValueError("signature is not sufficient")
        table[key] = y
    return table


def predict(table, signature, f, g, x):
    row = (f, g, x, None)
    return table[feature_tuple(row, signature)]


class MultilevelSelfExpansion(unittest.TestCase):
    def test_residuals_force_probe_genesis_then_constructor_genesis(self):
        n = 4
        discovery = permutations(n)

        # Verifier-only law. It depends on a value not in the initial interface
        # and also produces values not reducible to simply returning an input.
        verifier = lambda f, g, x: (f[g[x]] + g[x]) % n
        rows = make_rows(discovery, discovery, n, verifier)

        # Stage 0: every currently available coordinate is present, yet the full
        # tuple x,F(x),G(x) is insufficient. This blocks any lookup/combine node
        # over the existing interface.
        current = ((), (0,), (1,))
        self.assertFalse(sufficient(rows, current))
        initial_residuals = residual_pair_count(rows, current)
        self.assertGreater(initial_residuals, 0)

        # Stage 1: only after that failure, blind executable probe generation is
        # allowed. Exactly one depth-2 observation repairs the information loss.
        learned_probe, survivors = discover_missing_probe(rows, current)
        self.assertEqual(survivors, ((0, 1),))
        self.assertEqual(learned_probe, (0, 1))  # F(G(x)), not supplied by name

        expanded = current + (learned_probe,)
        self.assertTrue(sufficient(rows, expanded))

        # Stage 2: the system now infers the smallest input signature needed for
        # a new value-producing constructor. It is not told which coordinates
        # should feed that constructor.
        signature = infer_minimal_signature(rows, expanded)
        self.assertEqual(signature, ((1,), (0, 1)))  # G(x), F(G(x))
        self.assertFalse(any(sufficient(rows, (feature,)) for feature in signature))

        table = synthesize_lookup(rows, signature)
        self.assertEqual(len(table), n * n)

        # The constructor is genuinely value-producing: many verified outputs
        # equal neither of its input values, so projection/branching is insufficient.
        impossible_by_projection = sum(
            row[3] not in feature_tuple(row, signature)
            for row in rows
        )
        self.assertGreater(impossible_by_projection, 0)

    def test_two_stage_invention_transfers_and_each_ablation_breaks_it(self):
        n = 4
        maps = all_maps(n)
        discovery_set = set(permutations(n))
        discovery = tuple(discovery_set)
        verifier = lambda f, g, x: (f[g[x]] + g[x]) % n

        discovery_rows = make_rows(discovery, discovery, n, verifier)
        current = ((), (0,), (1,))
        learned_probe, _ = discover_missing_probe(discovery_rows, current)
        self.assertIsNotNone(learned_probe)
        expanded = current + (learned_probe,)
        signature = infer_minimal_signature(discovery_rows, expanded)
        self.assertIsNotNone(signature)
        table = synthesize_lookup(discovery_rows, signature)

        # Stream the exhaustive held-out census once. This keeps exactly the same
        # 259,840 rows while avoiding the previous quadratic residual-pair materialisation.
        transfer_failures = 0
        heldout_rows = 0
        constructor_ablation_impossible = 0
        residual_counts = defaultdict(Counter)

        for f in maps:
            for g in maps:
                if f in discovery_set and g in discovery_set:
                    continue
                for x in range(n):
                    expected = verifier(f, g, x)
                    heldout_rows += 1

                    if predict(table, signature, f, g, x) != expected:
                        transfer_failures += 1

                    row = (f, g, x, expected)
                    if expected not in feature_tuple(row, signature):
                        constructor_ablation_impossible += 1

                    old_key = feature_tuple(row, current)
                    residual_counts[old_key][expected] += 1

        probe_ablation_residuals = 0
        for counts in residual_counts.values():
            seen = 0
            for count in counts.values():
                probe_ablation_residuals += seen * count
                seen += count

        discovery_initial_residuals = residual_pair_count(discovery_rows, current)

        print(
            "multilevel self-expansion: "
            f"discovery_rows={len(discovery_rows)}; "
            f"initial_residuals={discovery_initial_residuals}; "
            f"invented_probe={learned_probe}; "
            f"inferred_signature={signature}; "
            f"table_entries={len(table)}; "
            f"heldout_rows={heldout_rows}; "
            f"transfer_failures={transfer_failures}; "
            f"probe_ablation_residuals={probe_ablation_residuals}; "
            f"constructor_ablation_impossible={constructor_ablation_impossible}"
        )

        self.assertEqual(heldout_rows, 259840)
        self.assertEqual(transfer_failures, 0)
        self.assertGreater(probe_ablation_residuals, 0)
        self.assertGreater(constructor_ablation_impossible, 0)


if __name__ == "__main__":
    unittest.main()
