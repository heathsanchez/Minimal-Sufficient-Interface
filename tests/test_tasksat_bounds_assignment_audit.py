import unittest

from experiments.tasksat_bounds_assignment_audit import (
    lean_reference_assignment_only,
    python_encoder_assignment_only,
)


class TestTaskSATBoundsAssignmentAudit(unittest.TestCase):
    def test_minimal_out_of_bounds_assignment_separates_orderings(self):
        bounds = (0.0, 10.0)
        self.assertEqual(lean_reference_assignment_only(5.0, bounds, 20.0), 10.0)
        self.assertEqual(python_encoder_assignment_only(5.0, bounds, 20.0), 20.0)

    def test_in_bounds_assignment_commutes(self):
        bounds = (0.0, 10.0)
        self.assertEqual(lean_reference_assignment_only(5.0, bounds, 7.0), 7.0)
        self.assertEqual(python_encoder_assignment_only(5.0, bounds, 7.0), 7.0)

    def test_no_assignment_commutes(self):
        bounds = (0.0, 10.0)
        self.assertEqual(lean_reference_assignment_only(20.0, bounds, None), 10.0)
        self.assertEqual(python_encoder_assignment_only(20.0, bounds, None), 10.0)

    def test_exact_assignment_only_commutation_law_on_finite_probe(self):
        bounds = (0.0, 10.0)
        for assigned in range(-5, 16):
            with self.subTest(assigned=assigned):
                ref = lean_reference_assignment_only(5.0, bounds, float(assigned))
                enc = python_encoder_assignment_only(5.0, bounds, float(assigned))
                self.assertEqual(ref == enc, 0.0 <= assigned <= 10.0)


if __name__ == "__main__":
    unittest.main()
