import itertools
import unittest


def all_maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def permutations(n):
    return tuple(m for m in all_maps(n) if len(set(m)) == n)


def apply_word(word, f, g, x):
    y = x
    for symbol in reversed(word):
        y = (f if symbol == 0 else g)[y]
    return y


def source_value(source, f, g, x):
    if source == "x":
        return x
    if source == "F":
        return f[x]
    if source == "G":
        return g[x]
    raise ValueError(source)


def make_rows(fs, gs, n, verifier):
    return [
        (f, g, x, verifier(f, g, x))
        for f in fs
        for g in gs
        for x in range(n)
    ]


def generated_words(max_depth):
    words = [()]
    frontier = [()]
    for _ in range(max_depth):
        nxt = []
        for word in frontier:
            nxt.append((0,) + word)
            nxt.append((1,) + word)
        words.extend(nxt)
        frontier = nxt
    return tuple(sorted(set(words), key=lambda w: (len(w), w)))


def word_errors(rows, word):
    return sum(apply_word(word, f, g, x) != y for f, g, x, y in rows)


def leaf_errors(rows, source):
    return sum(source_value(source, f, g, x) != y for f, g, x, y in rows)


def feature_value(feature, row):
    f, g, x, _ = row
    return source_value(feature, f, g, x)


class Leaf:
    def __init__(self, source):
        self.source = source

    def predict(self, f, g, x):
        return source_value(self.source, f, g, x)

    def size(self):
        return 1

    def leaves(self):
        return (self.source,)

    def depth(self):
        return 0

    def signature(self):
        return ("leaf", self.source)


class Split:
    def __init__(self, feature, branches):
        self.feature = feature
        self.branches = dict(branches)

    def predict(self, f, g, x):
        key = source_value(self.feature, f, g, x)
        return self.branches[key].predict(f, g, x)

    def size(self):
        return 1 + sum(child.size() for child in self.branches.values())

    def leaves(self):
        out = []
        for key in sorted(self.branches):
            out.extend(self.branches[key].leaves())
        return tuple(out)

    def depth(self):
        return 1 + max(child.depth() for child in self.branches.values())

    def signature(self):
        return (
            "split",
            self.feature,
            tuple((k, self.branches[k].signature()) for k in sorted(self.branches)),
        )


def exact_leaf(rows, sources):
    for source in sources:
        if leaf_errors(rows, source) == 0:
            return Leaf(source)
    return None


def synthesize_residual_tree(rows, sources=("x", "F", "G"), max_depth=3):
    """Build a constructor schema by recursively partitioning unresolved residuals.

    There is no finite portfolio of named constructor families. The only generic
    developmental move is: if no current leaf explains a bucket, split that bucket
    by an available observable whose values change the residual profile, then solve
    the resulting buckets recursively. The resulting tree shape is data-derived.
    """

    memo = {}

    def solve(bucket, depth):
        key = (tuple(id(r) for r in bucket), depth)
        if key in memo:
            return memo[key]

        leaf = exact_leaf(bucket, sources)
        if leaf is not None:
            memo[key] = leaf
            return leaf
        if depth == 0:
            memo[key] = None
            return None

        best = None
        best_key = None
        for feature in sources:
            groups = {}
            for row in bucket:
                groups.setdefault(feature_value(feature, row), []).append(row)
            if len(groups) <= 1:
                continue

            branches = {}
            ok = True
            for value, subrows in groups.items():
                child = solve(subrows, depth - 1)
                if child is None:
                    ok = False
                    break
                branches[value] = child
            if not ok:
                continue

            tree = Split(feature, branches)
            score = (tree.size(), tree.depth(), tree.signature())
            if best is None or score < best_key:
                best = tree
                best_key = score

        memo[key] = best
        return best

    return solve(rows, max_depth)


def tree_errors(rows, tree):
    return sum(tree.predict(f, g, x) != y for f, g, x, y in rows)


def residual_profile(rows, sources=("x", "F", "G")):
    return {source: leaf_errors(rows, source) for source in sources}


class ResidualDerivedSchemaGenesis(unittest.TestCase):
    def test_residuals_build_schema_without_named_constructor_family(self):
        n = 4
        discovery = permutations(n)

        # Verifier-only law: the learner is not given this selector table or a
        # "state-gated" constructor family. It sees only executions and labels.
        hidden_choice = ("F", "G", "x", "F")

        def verifier(f, g, x):
            return source_value(hidden_choice[x], f, g, x)

        rows = make_rows(discovery, discovery, n, verifier)

        # Existing executable observation grammar: fixed words over F and G.
        # Exhaust a substantial bounded prefix; none is an exact constructor.
        words = generated_words(4)
        self.assertFalse(any(word_errors(rows, w) == 0 for w in words))

        # No existing primitive output source works either.
        profile = residual_profile(rows)
        self.assertTrue(all(errors > 0 for errors in profile.values()))

        # Generic residual partitioning constructs a new executable schema.
        tree = synthesize_residual_tree(rows, max_depth=2)
        self.assertIsNotNone(tree)
        self.assertEqual(tree_errors(rows, tree), 0)

        # The minimal exact schema discovers that x is the control variable and
        # derives the branch outputs from the residuals. No selector table was passed.
        self.assertIsInstance(tree, Split)
        self.assertEqual(tree.feature, "x")
        learned = tuple(tree.branches[s].source for s in range(n))
        self.assertEqual(learned, hidden_choice)
        self.assertEqual(tree.depth(), 1)

    def test_derived_schema_transfers_and_ablation_restores_failure(self):
        n = 4
        maps = all_maps(n)
        discovery_set = set(permutations(n))
        discovery = tuple(discovery_set)
        hidden_choice = ("F", "G", "x", "F")

        def verifier(f, g, x):
            return source_value(hidden_choice[x], f, g, x)

        discovery_rows = make_rows(discovery, discovery, n, verifier)
        tree = synthesize_residual_tree(discovery_rows, max_depth=2)
        self.assertIsNotNone(tree)
        self.assertEqual(tree_errors(discovery_rows, tree), 0)

        heldout = [
            row
            for row in make_rows(maps, maps, n, verifier)
            if not (row[0] in discovery_set and row[1] in discovery_set)
        ]
        transfer_failures = tree_errors(heldout, tree)

        # Exact ablation proxy: remove the synthesized branching schema and fall
        # back to the best single pre-existing source. Residual errors reappear.
        ablated_errors = min(leaf_errors(heldout, s) for s in ("x", "F", "G"))

        print(
            "residual-derived schema genesis: "
            f"discovery_rows={len(discovery_rows)}; "
            f"schema={tree.signature()}; "
            f"tree_size={tree.size()}; "
            f"heldout_rows={len(heldout)}; "
            f"transfer_failures={transfer_failures}; "
            f"ablated_best_leaf_errors={ablated_errors}"
        )

        self.assertEqual(transfer_failures, 0)
        self.assertGreater(ablated_errors, 0)

    def test_same_generator_builds_different_schema_shapes_from_different_residuals(self):
        n = 4
        discovery = permutations(n)
        worlds = (
            ("F", "F", "G", "G"),
            ("F", "G", "x", "F"),
            ("x", "G", "G", "x"),
        )

        learned = []
        for hidden_choice in worlds:
            def verifier(f, g, x, hidden_choice=hidden_choice):
                return source_value(hidden_choice[x], f, g, x)

            rows = make_rows(discovery, discovery, n, verifier)
            tree = synthesize_residual_tree(rows, max_depth=2)
            self.assertIsNotNone(tree)
            self.assertEqual(tree_errors(rows, tree), 0)
            self.assertIsInstance(tree, Split)
            learned_choice = tuple(tree.branches[s].source for s in range(n))
            self.assertEqual(learned_choice, hidden_choice)
            learned.append(tree.signature())

        self.assertEqual(len(set(learned)), len(worlds))


if __name__ == "__main__":
    unittest.main()
