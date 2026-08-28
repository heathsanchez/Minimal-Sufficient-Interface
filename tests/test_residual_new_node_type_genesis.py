import itertools
import unittest


def all_maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def permutations(n):
    return tuple(m for m in all_maps(n) if len(set(m)) == n)


def make_rows(fs, gs, n, verifier):
    return [
        (f, g, x, verifier(f, g, x))
        for f in fs
        for g in gs
        for x in range(n)
    ]


def source_value(row, source):
    f, g, x, _ = row
    if source == "x":
        return x
    if source == "F":
        return f[x]
    if source == "G":
        return g[x]
    raise KeyError(source)


def selector_language_impossibility(rows, sources=("x", "F", "G")):
    """Rows impossible for *any* decision tree whose leaves only select sources.

    Splitting more deeply cannot help if the verified output is not equal to the
    value of any admissible leaf on that row.  This gives a structural
    impossibility certificate for the old node language, not a depth failure.
    """
    bad = []
    for row in rows:
        y = row[3]
        if y not in {source_value(row, s) for s in sources}:
            bad.append(row)
    return tuple(bad)


def tuple_key(row, coords):
    return tuple(source_value(row, c) for c in coords)


def tuple_sufficient(rows, coords):
    seen = {}
    for row in rows:
        key = tuple_key(row, coords)
        y = row[3]
        if key in seen and seen[key] != y:
            return False
        seen[key] = y
    return True


def infer_constructor_coordinates(rows, sources=("x", "F", "G")):
    """Infer the smallest coordinate tuple needed to *construct* an output.

    No binary-local node is named.  After the selector-leaf language is proved
    impossible, MSI asks which currently observable values jointly determine the
    verifier output.  The minimal sufficient tuple becomes the signature of a
    newly admitted constructor node.
    """
    for arity in range(1, len(sources) + 1):
        for coords in itertools.combinations(sources, arity):
            if tuple_sufficient(rows, coords):
                return coords
    return None


def synthesize_constructor_table(rows, coords):
    table = {}
    for row in rows:
        key = tuple_key(row, coords)
        y = row[3]
        if key in table and table[key] != y:
            raise ValueError("coordinates are not sufficient")
        table[key] = y
    return table


def predict(row, coords, table):
    return table[tuple_key(row, coords)]


class ResidualNewNodeTypeGenesis(unittest.TestCase):
    def test_residuals_force_output_construction_not_more_branching(self):
        n = 4
        discovery = permutations(n)

        # Hidden verifier law.  The learner is not given addition, modular
        # arithmetic, or a binary-local constructor family.
        verifier = lambda f, g, x: (f[x] + g[x]) % n
        rows = make_rows(discovery, discovery, n, verifier)

        impossible = selector_language_impossibility(rows)
        self.assertGreater(len(impossible), 0)

        # This is stronger than saying the current tree is too shallow: every
        # old tree leaf must return one of x/F/G, yet these rows require a value
        # equal to none of them.  Therefore no amount of old-node branching can
        # repair the residual.
        self.assertEqual(len(impossible), 972)

        coords = infer_constructor_coordinates(rows)
        self.assertEqual(coords, ("F", "G"))

        table = synthesize_constructor_table(rows, coords)
        self.assertEqual(len(table), n * n)
        self.assertTrue(all(predict(r, coords, table) == r[3] for r in rows))

    def test_new_node_type_transfers_and_ablation_restores_impossibility(self):
        n = 4
        maps = all_maps(n)
        discovery = set(permutations(n))
        verifier = lambda f, g, x: (f[x] + g[x]) % n

        discovery_rows = make_rows(tuple(discovery), tuple(discovery), n, verifier)
        coords = infer_constructor_coordinates(discovery_rows)
        self.assertEqual(coords, ("F", "G"))
        table = synthesize_constructor_table(discovery_rows, coords)

        heldout = [
            row
            for row in make_rows(maps, maps, n, verifier)
            if not (row[0] in discovery and row[1] in discovery)
        ]

        failures = sum(predict(r, coords, table) != r[3] for r in heldout)
        ablation_impossibility = selector_language_impossibility(heldout)

        print(
            "residual new-node genesis: "
            f"discovery_rows={len(discovery_rows)}; "
            f"old_node_impossibility={len(selector_language_impossibility(discovery_rows))}; "
            f"inferred_signature={coords}; "
            f"constructor_table_entries={len(table)}; "
            f"heldout_rows={len(heldout)}; "
            f"transfer_failures={failures}; "
            f"ablation_impossible_rows={len(ablation_impossibility)}"
        )

        self.assertEqual(len(heldout), 259840)
        self.assertEqual(failures, 0)
        self.assertEqual(len(ablation_impossibility), 109620)

    def test_same_meta_rule_infers_different_constructor_signatures(self):
        n = 4
        discovery = permutations(n)

        worlds = {
            "fg": lambda f, g, x: (f[x] + g[x]) % n,
            "xg": lambda f, g, x: (x + g[x]) % n,
            "xfg": lambda f, g, x: (x + f[x] + g[x]) % n,
        }

        inferred = {}
        for name, verifier in worlds.items():
            rows = make_rows(discovery, discovery, n, verifier)
            self.assertGreater(len(selector_language_impossibility(rows)), 0)
            inferred[name] = infer_constructor_coordinates(rows)

        self.assertEqual(inferred["fg"], ("F", "G"))
        self.assertEqual(inferred["xg"], ("x", "G"))
        self.assertEqual(inferred["xfg"], ("x", "F", "G"))


if __name__ == "__main__":
    unittest.main()
