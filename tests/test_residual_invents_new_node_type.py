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


def source_value(source, row):
    f, g, x, _ = row
    if source == "x":
        return x
    if source == "F":
        return f[x]
    if source == "G":
        return g[x]
    raise ValueError(source)


def selector_tree_obstruction(rows, sources=("x", "F", "G")):
    """Certificate that no tree whose leaves only return old sources can be exact.

    Any such tree, regardless of branching depth, must return one of the values
    already exposed by its leaves. A row whose verified target is outside that
    set is therefore an expressivity witness, not a search failure.
    """
    witnesses = []
    for row in rows:
        exposed = tuple(source_value(s, row) for s in sources)
        if row[3] not in exposed:
            witnesses.append((row, exposed))
    return tuple(witnesses)


def residual_edges(rows, sources=("x", "F", "G")):
    """For conflicting labelled rows, record which old coordinates differ."""
    edges = []
    for i, a in enumerate(rows):
        for b in rows[i + 1 :]:
            if a[3] == b[3]:
                continue
            edge = frozenset(
                s for s in sources if source_value(s, a) != source_value(s, b)
            )
            if edge:
                edges.append(edge)
    return tuple(edges)


def minimum_hitting_set(edges, sources=("x", "F", "G")):
    for k in range(1, len(sources) + 1):
        for subset in itertools.combinations(sources, k):
            chosen = set(subset)
            if all(chosen.intersection(edge) for edge in edges):
                return subset
    return None


class Combine:
    """A node type created only after selector-tree impossibility is certified."""

    def __init__(self, inputs, table):
        self.inputs = tuple(inputs)
        self.table = dict(table)

    def predict(self, row):
        key = tuple(source_value(s, row) for s in self.inputs)
        return self.table[key]

    def signature(self):
        return ("combine", self.inputs, tuple(sorted(self.table.items())))


def synthesize_combine_node(rows, sources=("x", "F", "G")):
    """Infer a new value-producing node from residual structure.

    No named arithmetic/operator family is supplied. Once old selector trees are
    proven impossible, infer the smallest set of old coordinates that determines
    the verifier outcome and synthesize its finite local law extensionally.
    """
    obstruction = selector_tree_obstruction(rows, sources)
    if not obstruction:
        return None, obstruction

    edges = residual_edges(rows, sources)
    inputs = minimum_hitting_set(edges, sources)
    if inputs is None:
        return None, obstruction

    table = {}
    for row in rows:
        key = tuple(source_value(s, row) for s in inputs)
        y = row[3]
        if key in table and table[key] != y:
            # The residual hitting set is necessary but not sufficient; expand
            # monotonically until the output law becomes functional.
            for k in range(len(inputs) + 1, len(sources) + 1):
                for candidate in itertools.combinations(sources, k):
                    candidate_table = {}
                    ok = True
                    for r in rows:
                        ck = tuple(source_value(s, r) for s in candidate)
                        if ck in candidate_table and candidate_table[ck] != r[3]:
                            ok = False
                            break
                        candidate_table[ck] = r[3]
                    if ok:
                        return Combine(candidate, candidate_table), obstruction
            return None, obstruction
        table[key] = y
    return Combine(inputs, table), obstruction


def errors(rows, node):
    return sum(node.predict(row) != row[3] for row in rows)


class ResidualInventsNewNodeType(unittest.TestCase):
    def test_verified_obstruction_forces_value_producing_node(self):
        n = 4
        discovery = permutations(n)

        # Verifier-only law. It often returns a value that is not x, F(x), or
        # G(x), so no arbitrarily deep selector tree over those leaves can work.
        verifier = lambda f, g, x: (f[x] + g[x]) % n
        rows = make_rows(discovery, discovery, n, verifier)

        obstruction = selector_tree_obstruction(rows)
        self.assertGreater(len(obstruction), 0)

        node, obstruction2 = synthesize_combine_node(rows)
        self.assertEqual(obstruction2, obstruction)
        self.assertIsNotNone(node)
        self.assertEqual(errors(rows, node), 0)

        # Residual structure should discover that x is irrelevant and that both
        # transformation outputs are necessary.
        self.assertEqual(node.inputs, ("F", "G"))

    def test_new_node_transfers_and_ablation_restores_impossibility(self):
        n = 4
        maps = all_maps(n)
        discovery_set = set(permutations(n))
        discovery = tuple(discovery_set)
        verifier = lambda f, g, x: (f[x] + g[x]) % n

        discovery_rows = make_rows(discovery, discovery, n, verifier)
        node, obstruction = synthesize_combine_node(discovery_rows)
        self.assertIsNotNone(node)
        self.assertEqual(errors(discovery_rows, node), 0)

        heldout = [
            row
            for row in make_rows(maps, maps, n, verifier)
            if not (row[0] in discovery_set and row[1] in discovery_set)
        ]
        transfer_failures = errors(heldout, node)
        ablation_witnesses = selector_tree_obstruction(heldout)

        print(
            "residual new-node genesis: "
            f"discovery_rows={len(discovery_rows)}; "
            f"old_schema_impossibility_witnesses={len(obstruction)}; "
            f"new_node_inputs={node.inputs}; "
            f"table_size={len(node.table)}; "
            f"heldout_rows={len(heldout)}; "
            f"transfer_failures={transfer_failures}; "
            f"ablation_impossibility_witnesses={len(ablation_witnesses)}"
        )

        self.assertEqual(transfer_failures, 0)
        self.assertGreater(len(ablation_witnesses), 0)

    def test_same_genesis_rule_discovers_different_input_shapes(self):
        n = 4
        discovery = permutations(n)
        worlds = (
            (lambda f, g, x: (f[x] + 1) % n, ("F",)),
            (lambda f, g, x: (f[x] + g[x]) % n, ("F", "G")),
            (lambda f, g, x: (x + f[x] + g[x]) % n, ("x", "F", "G")),
        )

        for verifier, expected_inputs in worlds:
            rows = make_rows(discovery, discovery, n, verifier)
            node, obstruction = synthesize_combine_node(rows)
            self.assertGreater(len(obstruction), 0)
            self.assertIsNotNone(node)
            self.assertEqual(errors(rows, node), 0)
            self.assertEqual(node.inputs, expected_inputs)


if __name__ == "__main__":
    unittest.main()
