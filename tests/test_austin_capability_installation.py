"""Bounded developmental transfer; mathematical claims require the Lean gate."""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import austin_capability_installation as d


class CapabilityInstallationTests(unittest.TestCase):
    def setUp(self):
        self.training = d.obligation("E40909", d.law40909)
        self.heldout = d.obligation("E11116", d.law11116)

    def test_acquisition_and_heldout_ablation(self):
        result = d.qualification()
        self.assertEqual((result["baseline_reachable"], result["installed_reachable"],
                          result["ablation_reachable"]), (0, 1, 0))
        self.assertEqual(result["source_bound"], 3)

    def test_training_does_not_consult_heldout(self):
        before = d.DevelopmentState()
        after, evidence = d.develop(before, self.training)
        self.assertEqual(evidence["rejected"], ("root",))
        self.assertEqual(len(evidence["promotions"]), 1)
        self.assertEqual(after.arithmetic_state, before.arithmetic_state)
        self.assertEqual(after.archive, before.archive + (evidence["certificate"],))
        self.assertEqual(len(d.apply(after, self.heldout)), 1)
        self.assertEqual(len(d.apply(before, self.heldout)), 0)

    def test_reject_forged_and_duplicate_capabilities(self):
        cert = d.certificate()
        for forged in (replace(cert, identity="0" * 64),
                       replace(cert, proof="trusted"),
                       replace(cert, dependencies=("future",)),
                       replace(cert, source=("install",))):
            with self.assertRaises(d.arithmetic.Rejected):
                d.verify_state(d.DevelopmentState(archive=(forged,)))
        with self.assertRaises(d.arithmetic.Rejected):
            d.verify_state(d.DevelopmentState(archive=(cert, cert)))
        self.assertEqual(d.develop(d.DevelopmentState(archive=(cert,)), self.heldout)[1], None)

    def test_generic_attachment_and_coordinate_ablation(self):
        for spec in (self.training, self.heldout):
            self.assertEqual(len(d.derive(spec, "root")), 0)
            self.assertEqual(len(d.derive(spec, d.OPERATOR)), 1)
            with self.assertRaises(d.arithmetic.Rejected):
                d.derive(spec, "unregistered")

    def test_generated_source_replay(self):
        actual = (Path(__file__).resolve().parents[1] / "lean/LemmaSynthesis/AustinCapabilityInstallation.lean").read_bytes()
        self.assertEqual(d.lean_source().encode("utf-8"), actual)


if __name__ == "__main__":
    unittest.main()
