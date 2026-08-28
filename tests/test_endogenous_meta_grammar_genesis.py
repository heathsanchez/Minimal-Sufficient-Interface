import itertools
import unittest


def identity(n):
    return tuple(range(n))


def compose(f, g):
    return tuple(f[g[x]] for x in range(len(g)))


def sequential_closure(generators, n):
    seen = {identity(n)}
    frontier = [identity(n)]
    while frontier:
        h = frontier.pop()
        for g in generators:
            gh = compose(g, h)
            if gh not in seen:
                seen.add(gh)
                frontier.append(gh)
    return seen


def constants(n):
    return tuple(tuple(a for _ in range(n)) for a in range(n))


def local_probe(row, index):
    maps, x, _ = row
    return maps[index][x]


def residual_hypergraph(rows, num_probes):
    """Every conflicting pair contributes the set of primitive probes that
    could possibly explain its output disagreement.

    The learner is not handed an arity change.  The required interface shape
    is inferred as a minimum hitting set of these verifier-generated residuals.
    """
    edges = set()
    for i, a in enumerate(rows):
        for b in rows[i + 1 :]:
            if a[2] == b[2]:
                continue
            diff = frozenset(
                j for j in range(num_probes)
                if local_probe(a, j) != local_probe(b, j)
            )
            if not diff:
                raise AssertionError(
                    "primitive probes cannot explain a verifier disagreement"
                )
            edges.add(diff)
    return tuple(sorted(edges, key=lambda e: (len(e), tuple(sorted(e)))))


def minimum_hitting_set(edges, num_probes):
    for r in range(num_probes + 1):
        for subset in itertools.combinations(range(num_probes), r):
            s = set(subset)
            if all(s.intersection(edge) for edge in edges):
                return subset
    return None


def representation_is_sufficient(rows, basis):
    table = {}
    for row in rows:
        key = tuple(local_probe(row, j) for j in basis)
        y = row[2]
        if key in table and table[key] != y:
            return False
        table[key] = y
    return True


def synthesize_lookup(rows, basis):
    table = {}
    for row in rows:
        key = tuple(local_probe(row, j) for j in basis)
        y = row[2]
        if key in table and table[key] != y:
            raise AssertionError("inferred interface is not sufficient")
        table[key] = y
    return table


def hidden_rule(values, dependency_count):
    """Verifier-only family.  The learner is not told the rule or its arity."""
    return min(values[:dependency_count])


def discovery_rows(n, num_probes, dependency_count):
    cs = constants(n)
    rows = []
    for maps in itertools.product(cs, repeat=num_probes):
        values = tuple(m[0] for m in maps)
        rows.append((maps, 0, hidden_rule(values, dependency_count)))
    return rows


def infer_interface(rows, num_probes):
    edges = residual_hypergraph(rows, num_probes)
    basis = minimum_hitting_set(edges, num_probes)
    if basis is None:
        raise AssertionError("no interface over available primitive probes can fit evidence")
    if not representation_is_sufficient(rows, basis):
        raise AssertionError("residual hitting set was not sufficient")
    return basis, synthesize_lookup(rows, basis), edges


def apply_learned(table, basis, maps, x):
    key = tuple(maps[j][x] for j in basis)
    return table[key]


class EndogenousMetaGrammarGenesis(unittest.TestCase):
    def test_residuals_infer_interface_arity_without_an_arity_proposal(self):
        n = 3
        num_probes = 3
        learned = {}

        # Same meta-procedure, three hidden worlds.  Nothing tells it whether
        # the missing interface should be unary, binary, or ternary.
        for dependency_count in (1, 2, 3):
            rows = discovery_rows(n, num_probes, dependency_count)
            basis, table, edges = infer_interface(rows, num_probes)
            learned[dependency_count] = (basis, table, edges)

            self.assertEqual(basis, tuple(range(dependency_count)))
            self.assertEqual(len(table), n ** dependency_count)
            self.assertGreater(len(edges), 0)

        self.assertEqual(tuple(len(learned[k][0]) for k in (1, 2, 3)), (1, 2, 3))

    def test_inferred_ternary_interface_transfers_and_unlocks_old_language(self):
        n = 3
        num_probes = 3
        rows = discovery_rows(n, num_probes, 3)
        basis, table, _ = infer_interface(rows, num_probes)
        self.assertEqual(basis, (0, 1, 2))

        maps = tuple(itertools.product(range(n), repeat=n))
        cs = set(constants(n))
        heldout_tuples = 0
        transfer_failures = 0

        for fs in itertools.product(maps, repeat=num_probes):
            if all(f in cs for f in fs):
                continue
            heldout_tuples += 1
            for x in range(n):
                expected = hidden_rule(tuple(f[x] for f in fs), 3)
                if apply_learned(table, basis, fs, x) != expected:
                    transfer_failures += 1

        self.assertEqual(transfer_failures, 0)

        # A concrete capability witness inherited from the earlier adversarial
        # break.  Adding identity as a third primitive does not enlarge the old
        # unary sequential closure, but the residual-inferred 3-coordinate
        # interface can express the pointwise target.
        f = (0, 0, 2)
        g = (1, 0, 1)
        h = identity(n)
        target = tuple(min(f[x], g[x], h[x]) for x in range(n))
        old_closure = sequential_closure((f, g, h), n)

        self.assertEqual(target, (0, 0, 1))
        self.assertNotIn(target, old_closure)
        learned_target = tuple(apply_learned(table, basis, (f, g, h), x) for x in range(n))
        self.assertEqual(learned_target, target)

        # Exact ablation: remove the inferred product interface / lookup and the
        # target again lies outside the original executable language.
        self.assertNotIn(learned_target, old_closure)

        print(
            "residual-inferred interface shape: "
            "discovered_arities=(1,2,3); "
            f"ternary_basis={basis}; "
            f"heldout_map_tuples={heldout_tuples}; "
            f"transfer_failures={transfer_failures}; "
            f"old_language_target_reachable={target in old_closure}"
        )


if __name__ == "__main__":
    unittest.main()
