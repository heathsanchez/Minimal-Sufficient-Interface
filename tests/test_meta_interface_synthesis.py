import itertools
import unittest


def apply_word(word, f, g, x):
    y = x
    for symbol in reversed(word):
        y = (f if symbol == 0 else g)[y]
    return y


def feature_value(name, f, g, x):
    words = {
        "x": (),
        "F": (0,),
        "G": (1,),
        "FF": (0, 0),
        "FG": (0, 1),
        "GF": (1, 0),
        "GG": (1, 1),
    }
    return apply_word(words[name], f, g, x)


def dataset(n, target):
    maps = tuple(itertools.product(range(n), repeat=n))
    rows = []
    for f in maps:
        for g in maps:
            for x in range(n):
                rows.append((f, g, x, target(f, g, x)))
    return rows


def representation_is_sufficient(rows, features):
    seen = {}
    for f, g, x, y in rows:
        key = tuple(feature_value(name, f, g, x) for name in features)
        if key in seen and seen[key] != y:
            return False
        seen[key] = y
    return True


def residual_pair(rows, features):
    buckets = {}
    for row in rows:
        f, g, x, y = row
        key = tuple(feature_value(name, f, g, x) for name in features)
        prev = buckets.get(key)
        if prev is not None and prev[3] != y:
            return prev, row
        buckets[key] = row
    return None


def minimum_feature_basis(rows, feature_names):
    for r in range(len(feature_names) + 1):
        for subset in itertools.combinations(feature_names, r):
            if representation_is_sufficient(rows, subset):
                return subset
    return None


def synthesize_lookup(rows, features):
    table = {}
    for f, g, x, y in rows:
        key = tuple(feature_value(name, f, g, x) for name in features)
        if key in table and table[key] != y:
            raise ValueError("representation is not sufficient")
        table[key] = y
    return table


class MetaInterfaceSynthesis(unittest.TestCase):
    def test_sequential_constructor_has_one_feature_minimal_interface(self):
        n = 3
        features = ("x", "F", "G", "FF", "FG", "GF", "GG")
        rows = dataset(n, lambda f, g, x: f[g[x]])
        basis = minimum_feature_basis(rows, features)
        self.assertEqual(basis, ("FG",))
        table = synthesize_lookup(rows, basis)
        self.assertEqual(table, {(0,): 0, (1,): 1, (2,): 2})

    def test_out_of_grammar_min_residual_forces_two_feature_interface(self):
        """The unary-word failure can be diagnosed as a missing dependency.

        No single generated trace feature is sufficient for the hidden pointwise
        constructor. The smallest sufficient interface is the pair (F(x),G(x)).
        Once that interface is admitted, the constructor itself is just a learned
        lookup table; `min` is never supplied to the synthesis procedure.
        """
        n = 3
        primitive = ("x", "F", "G", "FF", "FG", "GF", "GG")
        rows = dataset(n, lambda f, g, x: min(f[x], g[x]))

        for feature in primitive:
            self.assertFalse(representation_is_sufficient(rows, (feature,)))
            self.assertIsNotNone(residual_pair(rows, (feature,)))

        # Expand the representation language only by allowing pairs of already
        # available trace features; no named min/max constructor is introduced.
        basis = minimum_feature_basis(rows, primitive)
        self.assertEqual(basis, ("F", "G"))

        table = synthesize_lookup(rows, basis)
        self.assertEqual(len(table), n * n)
        for a in range(n):
            for b in range(n):
                self.assertEqual(table[(a, b)], min(a, b))

    def test_representation_failure_and_repair_are_the_same_msi_pattern(self):
        n = 3
        rows = dataset(n, lambda f, g, x: min(f[x], g[x]))
        coarse = ("F",)
        refined = ("F", "G")
        self.assertIsNotNone(residual_pair(rows, coarse))
        self.assertIsNone(residual_pair(rows, refined))
        self.assertFalse(representation_is_sufficient(rows, coarse))
        self.assertTrue(representation_is_sufficient(rows, refined))


if __name__ == "__main__":
    unittest.main()
