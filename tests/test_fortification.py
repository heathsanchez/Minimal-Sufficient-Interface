import itertools
import unittest

from test_constructor_genesis import (
    closure,
    compose,
    eval_term,
    generate_terms,
    identity,
    learn_constructor,
    term_map,
)


def pointwise_min(f, g):
    return tuple(min(f[x], g[x]) for x in range(len(f)))


def all_pointwise_tables(n):
    """All binary lookup tables phi : X x X -> X, in lexicographic order."""
    return itertools.product(range(n), repeat=n * n)


def eval_table(table, a, b, n):
    return table[a * n + b]


def table_map(table, f, g, n):
    return tuple(eval_table(table, f[x], g[x], n) for x in range(n))


def min_table(n):
    return tuple(min(a, b) for a in range(n) for b in range(n))


def relation_from_partition(blocks):
    pairs = set()
    for block in blocks:
        for x in block:
            for y in block:
                pairs.add((x, y))
    return frozenset(pairs)


class Fortification(unittest.TestCase):
    def test_empty_version_space_is_representation_failure_not_task_failure(self):
        """The old unary-word grammar must explicitly fail when target is outside it."""
        n = 3
        f = (0, 0, 2)
        g = (1, 0, 1)
        target = pointwise_min(f, g)
        terms = generate_terms(12)
        self.assertTrue(all(term_map(t, f, g, n) != target for t in terms))

    def test_generic_language_expansion_repairs_out_of_grammar_constructor(self):
        """After exhaustion, a generic richer representation can recover the hidden law.

        The expansion does not name `min`: it admits every pointwise binary table
        phi : X x X -> X. Counterexamples then retain exactly those tables that
        agree with the hidden constructor on every input pair reachable through
        the current action algebra. Ambiguity off that support is operationally
        irrelevant, mirroring MSI's quotient principle.
        """
        n = 3
        f0 = (0, 0, 2)
        g0 = (1, 0, 1)
        algebra = closure((f0, g0), n)

        # Unary constructor grammar is genuinely exhausted first.
        unary = generate_terms(12)
        self.assertTrue(
            all(
                any(term_map(t, f, g, n) != pointwise_min(f, g) for f in algebra for g in algebra)
                for t in unary
            )
        )

        # Verifier constraints on the richer generic pointwise language.
        required = {}
        for f in algebra:
            for g in algebra:
                target = pointwise_min(f, g)
                for x in range(n):
                    key = (f[x], g[x])
                    value = target[x]
                    if key in required:
                        self.assertEqual(required[key], value)
                    required[key] = value

        true_table = min_table(n)
        self.assertTrue(
            all(eval_table(true_table, a, b, n) == value for (a, b), value in required.items())
        )

        survivors = []
        for table in all_pointwise_tables(n):
            if all(eval_table(table, a, b, n) == value for (a, b), value in required.items()):
                survivors.append(table)

        self.assertGreater(len(survivors), 0)
        self.assertIn(true_table, survivors)

        # Every survivor is extensionally the same constructor on the reachable algebra.
        for table in survivors:
            for f in algebra:
                for g in algebra:
                    self.assertEqual(table_map(table, f, g, n), pointwise_min(f, g))

        # Any remaining syntactic ambiguity is only on input pairs the reachable
        # algebra never presents to the constructor.
        self.assertEqual(len(survivors), n ** (n * n - len(required)))

    def test_single_false_verifier_label_can_destroy_the_true_constructor(self):
        """Counterexample-driven synthesis is only as sound as verifier evidence."""
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        witness = None
        for a in maps:
            for b in maps:
                algebra = closure((a, b), n)
                survivors, _ = learn_constructor(algebra, n, 3)
                if survivors == [(0, 1)]:
                    witness = (algebra, a, b)
                    break
            if witness is not None:
                break
        self.assertIsNotNone(witness)
        algebra, _, _ = witness

        true_term = (0, 1)
        # Pick a reachable query and deliberately flip its verifier label.
        f = algebra[0]
        g = algebra[-1]
        x = 0
        correct = compose(f, g)[x]
        false = (correct + 1) % n
        self.assertNotEqual(eval_term(true_term, f, g, x), false)

        # A learner that trusts this label must eliminate the true constructor.
        candidates = list(generate_terms(3))
        candidates = [t for t in candidates if eval_term(t, f, g, x) == false]
        self.assertNotIn(true_term, candidates)

    def test_monotone_meet_cannot_retract_a_withdrawn_constraint(self):
        """Changing protected authority requires provenance/recompute above the kernel."""
        # E0 is the universal equivalence on three states.
        E0 = relation_from_partition(((0, 1, 2),))
        # K is a once-protected distinction separating 2 from {0,1}.
        K = relation_from_partition(((0, 1), (2,)))
        E1 = E0 & K
        self.assertNotEqual(E1, E0)

        # Any future meet can only remove pairs from E1. It can never restore the
        # pairs lost when K was retained, even if K later ceases to be protected.
        equivalences = [
            relation_from_partition(((0, 1, 2),)),
            relation_from_partition(((0, 1), (2,))),
            relation_from_partition(((0, 2), (1,))),
            relation_from_partition(((1, 2), (0,))),
            relation_from_partition(((0,), (1,), (2,))),
        ]
        self.assertTrue(all((E1 & K2) != E0 for K2 in equivalences))

        # Correct recovery is by recomputing the meet from the *currently active*
        # provenance set (empty here), not by applying another refinement update.
        recomputed = E0
        self.assertEqual(recomputed, E0)


if __name__ == "__main__":
    unittest.main()
