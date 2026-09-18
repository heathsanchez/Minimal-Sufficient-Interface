import itertools
import unittest

from msi import Interface
from qckn import (
    CertifiedSubstitution,
    NewContextDefect,
    assess_operation,
    defect_to_pair_residual,
)


class TestFrozenQCKFiniteAdapter(unittest.TestCase):
    def setUp(self):
        self.X = (0, 1, 2)
        self.v = {0: 0, 1: 0, 2: 1}
        self.O1_map = {0: 0, 1: 2, 2: 0}
        self.O1 = lambda x: self.O1_map[x]

        def outcome(x, c):
            if c == "v":
                return self.v[x]
            if c == "v_after_O1":
                return self.v[self.O1(x)]
            raise KeyError(c)

        self.interface = Interface(
            self.X,
            ("v", "v_after_O1"),
            outcome,
        )

    def test_capability_bridge_becomes_qck_defect_then_certified(self):
        before = assess_operation(self.interface, ("v",), self.O1)
        self.assertIsInstance(before, NewContextDefect)
        self.assertTrue(
            self.interface.equivalent(before.left, before.right, before.basis)
        )
        self.assertFalse(
            self.interface.equivalent(
                before.image_left, before.image_right, before.basis
            )
        )

        after = assess_operation(
            self.interface,
            ("v", "v_after_O1"),
            self.O1,
        )
        self.assertIsInstance(after, CertifiedSubstitution)

    def test_defect_compiles_into_existing_pair_residual_ledger(self):
        defect = assess_operation(self.interface, ("v",), self.O1)
        self.assertIsInstance(defect, NewContextDefect)
        residual = defect_to_pair_residual(self.interface, defect)
        self.assertTrue(residual.representation.same(residual.left, residual.right))
        self.assertNotEqual(residual.consequence_left, residual.consequence_right)

    def test_assessment_exactly_matches_finite_quotient_admissibility(self):
        interface = Interface(
            self.X,
            ("parity",),
            lambda x, _c: x % 2,
        )
        basis = ("parity",)

        for images in itertools.product(self.X, repeat=len(self.X)):
            table = dict(zip(self.X, images))
            action = lambda x, table=table: table[x]
            assessment = assess_operation(interface, basis, action)
            admissible = interface.preserves_equivalence(action, basis)

            self.assertEqual(
                isinstance(assessment, CertifiedSubstitution),
                admissible,
                msg=f"table={table}",
            )
            if isinstance(assessment, NewContextDefect):
                self.assertTrue(
                    interface.equivalent(
                        assessment.left, assessment.right, assessment.basis
                    )
                )
                self.assertFalse(
                    interface.equivalent(
                        assessment.image_left,
                        assessment.image_right,
                        assessment.basis,
                    )
                )


if __name__ == "__main__":
    unittest.main()
