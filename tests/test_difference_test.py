import itertools
import unittest


def partitions(xs):
    xs = tuple(xs)
    if not xs:
        yield ()
        return
    first, rest = xs[0], xs[1:]
    for p in partitions(rest):
        yield (frozenset((first,)),) + p
        for i in range(len(p)):
            q = list(p)
            q[i] = frozenset(set(q[i]) | {first})
            yield tuple(q)


def canon_partition(p):
    blocks = [tuple(sorted(b)) for b in p]
    return tuple(sorted(blocks))


def eq_from_partition(p):
    block_of = {}
    for i, b in enumerate(p):
        for x in b:
            block_of[x] = i
    return lambda x, y: block_of[x] == block_of[y]


def refines(p_new, p_old):
    e_old = eq_from_partition(p_old)
    for b in p_new:
        for x in b:
            for y in b:
                if not e_old(x, y):
                    return False
    return True


def invariant(p, g):
    e = eq_from_partition(p)
    xs = sorted({x for b in p for x in b})
    return all((not e(x, y)) or e(g[x], g[y]) for x in xs for y in xs)


def orbit(g, x):
    out = []
    seen = set()
    y = x
    while y not in seen:
        seen.add(y)
        out.append(y)
        y = g[y]
    return frozenset(out)


def action_closure(g):
    n = len(g)
    ident = tuple(range(n))
    seen = {ident}
    cur = ident
    while True:
        cur = tuple(g[cur[x]] for x in range(n))
        if cur in seen:
            return seen
        seen.add(cur)


def apply_map(f, x):
    return f[x]


def coarsest_lawful_repairs(X, old_p, residual_pair, g):
    x, y = residual_pair
    all_parts = {canon_partition(p): p for p in partitions(X)}
    lawful = [
        p
        for p in all_parts.values()
        if refines(p, old_p)
        and not eq_from_partition(p)(x, y)
        and invariant(p, g)
    ]
    if not lawful:
        return (), ()
    min_blocks = min(len(p) for p in lawful)
    coarsest = tuple(
        sorted(
            canon_partition(p)
            for p in lawful
            if len(p) == min_blocks
        )
    )
    return tuple(lawful), coarsest


def distinguishing_pairs(p, q):
    ep, eq = eq_from_partition(p), eq_from_partition(q)
    xs = sorted({x for b in p for x in b})
    return tuple(
        (x, y)
        for x in xs
        for y in xs
        if x < y and ep(x, y) != eq(x, y)
    )


def orbit_separator(g, x, y, X):
    """Generate a binary distinction from residual endpoints and dynamics only."""
    ox, oy = orbit(g, x), orbit(g, y)
    if not ox.isdisjoint(oy) or ox | oy != frozenset(X):
        return None
    return tuple(0 if z in ox else 1 for z in X)


class DifferenceTest(unittest.TestCase):
    """Minimal exhaustive consequential-distinction experiments.

    The first experiment deliberately isolates the representation-forcing core.
    Its four-state 2+2 geometry makes the coarsest lawful repair unique; that
    uniqueness is a property of this witness, not a generic theorem.

    The factorization enumeration below is likewise an executable sanity check
    of the residual premise, not independent evidence against search failure:
    once the target varies inside an old quotient block, non-factorization is
    immediate mathematically.

    Separate tests below stress genuine version-space non-uniqueness and an
    explicitly constructed cardinality family X_n = Z_n x {0,1}. The latter is
    only a cardinality check: the hidden-coordinate role is fixed by design, so
    it is not evidence of robustness to structural variation.
    """

    def run_equivariant_world(self, perm):
        X = tuple(range(4))
        inv = {perm[i]: i for i in X}

        g0 = (2, 3, 0, 1)
        g = tuple(perm[g0[inv[z]]] for z in X)

        old_blocks0 = ({0, 1}, {2, 3})
        old_p = tuple(frozenset(perm[z] for z in b) for b in old_blocks0)
        old_eq = eq_from_partition(old_p)

        x, y = perm[0], perm[1]
        self.assertTrue(old_eq(x, y))

        def old_obs(z):
            return 0 if z in old_p[0] else 1

        closure = action_closure(g)
        self.assertTrue(
            all(
                old_obs(apply_map(a, x)) == old_obs(apply_map(a, y))
                for a in closure
            )
        )

        target0 = (0, 1, 0, 1)
        target = tuple(target0[inv[z]] for z in X)
        self.assertNotEqual(target[x], target[y])

        delta = orbit_separator(g, x, y, X)
        self.assertIsNotNone(delta)
        self.assertNotEqual(delta[x], delta[y])

        lawful, coarsest = coarsest_lawful_repairs(X, old_p, (x, y), g)
        self.assertTrue(lawful)
        # Local witness only: this geometry happens to force a unique repair.
        self.assertEqual(len(coarsest), 1)

        new_groups = {}
        for z in X:
            new_groups.setdefault((old_obs(z), delta[z]), set()).add(z)
        new_p = tuple(frozenset(v) for v in new_groups.values())
        self.assertEqual(canon_partition(new_p), coarsest[0])

        # Executable instantiation of the already-known factorization failure.
        # Because target[x] != target[y] while old_obs(x) == old_obs(y), this is
        # a sanity check, not an independent search-vs-representation control.
        old_factorable = []
        for lut in itertools.product((0, 1), repeat=2):
            f = tuple(lut[old_obs(z)] for z in X)
            old_factorable.append(f)
        self.assertNotIn(target, old_factorable)

        same = all(delta[z] == target[z] for z in X)
        flipped = all((1 - delta[z]) == target[z] for z in X)
        self.assertTrue(same or flipped)

        return {
            "perm": perm,
            "closure_size": len(closure),
            "residual": (x, y),
            "generated_delta": delta,
            "coarsest": coarsest[0],
            "target": target,
        }

    def test_all_24_relabellings_are_equivariant_not_domain_transfer(self):
        results = [
            self.run_equivariant_world(perm)
            for perm in itertools.permutations(range(4))
        ]

        self.assertEqual(len(results), 24)
        self.assertGreater(len({r["generated_delta"] for r in results}), 1)

        print("DIFFERENCE TEST REPRESENTATION CORE PASS")
        print(
            f"relabelings=24/24; old_closure_size={results[0]['closure_size']}; "
            f"unique_surface_deltas={len({r['generated_delta'] for r in results})}"
        )

    def test_version_space_can_fork_before_discrete_refinement(self):
        """A residual need not determine one minimum repair, even at |X|=4."""
        X = tuple(range(4))
        old_p = (frozenset({0, 1, 2}), frozenset({3}))
        g = (0, 0, 0, 0)
        residual_pair = (0, 1)

        lawful, coarsest = coarsest_lawful_repairs(X, old_p, residual_pair, g)
        self.assertTrue(lawful)
        expected = {
            ((0,), (1, 2), (3,)),
            ((0, 2), (1,), (3,)),
        }
        self.assertEqual(set(coarsest), expected)
        self.assertTrue(all(len(p) == 3 for p in coarsest))
        self.assertTrue(all(len(p) < 4 for p in coarsest))

        p, q = coarsest
        probes = distinguishing_pairs(p, q)
        self.assertTrue(probes)
        x, y = probes[0]
        self.assertNotEqual(eq_from_partition(p)(x, y), eq_from_partition(q)(x, y))

        print(
            "DIFFERENCE TEST VERSION SPACE PASS "
            f"coarsest_repairs={len(coarsest)}; discriminating_pair={probes[0]}"
        )

    def test_residual_orbit_constructor_on_explicit_cardinality_family(self):
        """Cardinality-only family, not a structural-variation transfer claim.

        X_n = Z_n x {0,1}; g_n(i,b)=(i+1 mod n,b). Therefore |<g_n>|=n by
        construction, while the residual endpoints (0,0),(0,1) generate the two
        hidden-bit orbits. We test a bounded family only to ensure the executable
        constructor follows this elementary law rather than two hand-picked cases.
        """
        worlds = []
        for width in range(2, 9):
            X = tuple(range(2 * width))
            g = tuple(2 * (((z // 2) + 1) % width) + (z % 2) for z in X)
            old_p = tuple(
                frozenset({2 * phase, 2 * phase + 1})
                for phase in range(width)
            )
            x, y = 0, 1
            old_eq = eq_from_partition(old_p)
            self.assertTrue(old_eq(x, y))

            def old_obs(z):
                return z // 2

            closure = action_closure(g)
            self.assertEqual(len(closure), width)
            self.assertTrue(
                all(old_obs(apply_map(a, x)) == old_obs(apply_map(a, y)) for a in closure)
            )

            delta = orbit_separator(g, x, y, X)
            self.assertIsNotNone(delta)
            target = tuple(z % 2 for z in X)
            same = delta == target
            flipped = tuple(1 - b for b in delta) == target
            self.assertTrue(same or flipped)
            worlds.append((len(X), len(closure)))

        self.assertEqual(worlds, [(2 * n, n) for n in range(2, 9)])
        print(f"DIFFERENCE TEST CARDINALITY FAMILY PASS worlds={worlds}")


if __name__ == '__main__':
    unittest.main()
