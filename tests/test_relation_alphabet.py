import itertools
import unittest


X = (0, 1, 2)
C = (0, 1, 2)
ALL_PAIRS = frozenset((x, y) for x in X for y in X)


def partitions(items):
    items = tuple(items)
    if not items:
        yield ()
        return
    first = items[0]
    for p in partitions(items[1:]):
        # New block.
        yield ((first,),) + p
        # Insert into each existing block.
        for i in range(len(p)):
            q = list(p)
            q[i] = tuple(sorted((first,) + q[i]))
            # Canonicalize block order to avoid duplicates.
            q = tuple(sorted(q, key=lambda b: (b[0], len(b), b)))
            yield q


def canonical_partitions():
    seen = set()
    out = []
    for p in partitions(X):
        cp = tuple(sorted((tuple(sorted(b)) for b in p), key=lambda b: b[0]))
        if cp not in seen:
            seen.add(cp)
            out.append(cp)
    return tuple(out)


PARTITIONS = canonical_partitions()


def relation_of_partition(p):
    block_of = {x: i for i, block in enumerate(p) for x in block}
    return frozenset((x, y) for x in X for y in X if block_of[x] == block_of[y])


EQUIVS = tuple(relation_of_partition(p) for p in PARTITIONS)


def induced_relation(kernel_family, basis):
    rel = ALL_PAIRS
    for c in basis:
        rel = rel & kernel_family[c]
    return rel


def quotient_labels(eq):
    """Canonical quotient map x |-> [x]_eq represented by minimum member of its class."""
    labels = {}
    for x in X:
        cls = tuple(y for y in X if (x, y) in eq)
        labels[x] = min(cls)
    return labels


class RelationOnlyAlphabet(unittest.TestCase):
    def test_three_state_equivalence_relations_are_complete(self):
        # Bell number B_3 = 5.
        self.assertEqual(len(EQUIVS), 5)

    def test_every_equivalence_kernel_has_an_outcome_map_representation(self):
        # Every equivalence relation K is ker(q_K) of its quotient map.
        for K in EQUIVS:
            q = quotient_labels(K)
            reconstructed = frozenset((x, y) for x in X for y in X if q[x] == q[y])
            self.assertEqual(K, reconstructed)

    def test_all_kernel_families_need_no_outcome_ontology(self):
        # Exhaust all 5^3 = 125 families of equivalence kernels and all 2^3 bases.
        checks = 0
        for family_tuple in itertools.product(EQUIVS, repeat=len(C)):
            family = {c: family_tuple[c] for c in C}
            quotient_maps = {c: quotient_labels(family[c]) for c in C}
            for mask in range(1 << len(C)):
                basis = tuple(c for c in C if mask & (1 << c))
                relation_direct = induced_relation(family, basis)
                relation_via_outcomes = frozenset(
                    (x, y)
                    for x in X for y in X
                    if all(quotient_maps[c][x] == quotient_maps[c][y] for c in basis)
                )
                self.assertEqual(relation_direct, relation_via_outcomes)
                checks += 1
        self.assertEqual(checks, 125 * 8)

    def test_laws_hold_on_full_relation_only_universe(self):
        checks = 0
        for family_tuple in itertools.product(EQUIVS, repeat=len(C)):
            family = {c: family_tuple[c] for c in C}
            target = induced_relation(family, C)
            for mask in range(1 << len(C)):
                basis = tuple(c for c in C if mask & (1 << c))
                E = induced_relation(family, basis)

                # Equivalence.
                self.assertTrue(all((x, x) in E for x in X))
                self.assertTrue(all((y, x) in E for x, y in E))
                self.assertTrue(all((x, z) in E for x in X for y in X for z in X
                                    if (x, y) in E and (y, z) in E))

                # One-step update and monotonicity.
                for c in C:
                    E2 = induced_relation(family, tuple(dict.fromkeys(basis + (c,))))
                    self.assertEqual(E2, E & family[c])
                    self.assertTrue(E2 <= E)

                # Exact stopping / residual equivalence.
                residual = any((x, y) in E and (x, y) not in target for x in X for y in X)
                separator = any(
                    (x, y) in E and (x, y) not in family[c]
                    for x in X for y in X for c in C if c not in basis
                )
                self.assertEqual(residual, separator)
                self.assertEqual(not residual, E == target)
                checks += 1
        self.assertEqual(checks, 125 * 8)


if __name__ == '__main__':
    unittest.main()
