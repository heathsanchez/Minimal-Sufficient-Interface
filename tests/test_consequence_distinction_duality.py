import unittest

from consequence_distinction import (
    FailureKind,
    close_consequences,
    close_representation,
    descends,
    galois_holds,
    minimal_repair,
    phi,
    psi,
    residual_witness,
    classify_failure,
)
from consequential_core import EquivalenceRelation


X = (0, 1, 2, 3)


def parity(x):
    return x % 2


def low_high(x):
    return 0 if x < 2 else 1


def exact(x):
    return x


def constant(_x):
    return 0


UNIVERSE = (constant, parity, low_high, exact)


class ConsequenceDistinctionDualityTests(unittest.TestCase):
    def test_phi_is_the_common_kernel_of_protected_consequences(self):
        relation = phi(X, (parity, low_high))
        expected = EquivalenceRelation.from_partition(X, ({0}, {1}, {2}, {3}))
        self.assertEqual(relation, expected)

    def test_psi_is_exactly_the_consequences_that_descend(self):
        relation = EquivalenceRelation.from_partition(X, ({0, 2}, {1, 3}))
        admitted = psi(relation, UNIVERSE)
        self.assertEqual(admitted, (constant, parity))
        self.assertTrue(descends(relation, parity))
        self.assertFalse(descends(relation, low_high))

    def test_galois_law_holds_in_both_directions(self):
        relations = (
            EquivalenceRelation.from_partition(X, ({0, 1, 2, 3},)),
            EquivalenceRelation.from_partition(X, ({0, 2}, {1, 3})),
            EquivalenceRelation.from_partition(X, ({0, 1}, {2, 3})),
            EquivalenceRelation.from_partition(X, ({0}, {1}, {2}, {3})),
        )
        consequence_families = (
            (),
            (constant,),
            (parity,),
            (low_high,),
            (parity, low_high),
            UNIVERSE,
        )
        for relation in relations:
            for family in consequence_families:
                with self.subTest(relation=relation, family=family):
                    self.assertTrue(galois_holds(X, family, relation, UNIVERSE))

    def test_closure_operators_are_idempotent(self):
        consequences_once = close_consequences(X, (parity,), UNIVERSE)
        consequences_twice = close_consequences(X, consequences_once, UNIVERSE)
        self.assertEqual(consequences_once, consequences_twice)

        relation = EquivalenceRelation.from_partition(X, ({0}, {1}, {2, 3}))
        representation_once = close_representation(relation, UNIVERSE)
        representation_twice = close_representation(representation_once, UNIVERSE)
        self.assertEqual(representation_once, representation_twice)

    def test_residual_is_exactly_failure_to_descend_and_repair_is_coarsest(self):
        relation = EquivalenceRelation.from_partition(X, ({0, 2}, {1, 3}))
        witness = residual_witness(relation, low_high)
        self.assertIsNotNone(witness)
        left, right = witness
        self.assertTrue(relation.same(left, right))
        self.assertNotEqual(low_high(left), low_high(right))

        repaired = minimal_repair(relation, low_high)
        self.assertTrue(repaired.strictly_refines(relation))
        self.assertTrue(descends(repaired, low_high))

        # The exact discrete quotient is forced in this example: any relation
        # that still merges one of the old parity classes fails low_high.
        self.assertEqual(
            repaired,
            EquivalenceRelation.from_partition(X, ({0}, {1}, {2}, {3})),
        )

    def test_failure_diagnostic_trichotomy(self):
        parity_relation = phi(X, (parity,))
        discrete = phi(X, (exact,))

        self.assertEqual(
            classify_failure(
                parity_relation,
                low_high,
                reachable=(constant, parity),
                found=False,
            ),
            FailureKind.REPRESENTATION,
        )

        self.assertEqual(
            classify_failure(
                discrete,
                low_high,
                reachable=(constant, parity),
                found=False,
            ),
            FailureKind.CAPABILITY,
        )

        self.assertEqual(
            classify_failure(
                discrete,
                low_high,
                reachable=(constant, parity, low_high),
                found=False,
            ),
            FailureKind.SEARCH,
        )

        self.assertEqual(
            classify_failure(
                discrete,
                low_high,
                reachable=(constant, parity, low_high),
                found=True,
            ),
            FailureKind.SOLVED,
        )


if __name__ == "__main__":
    unittest.main()
