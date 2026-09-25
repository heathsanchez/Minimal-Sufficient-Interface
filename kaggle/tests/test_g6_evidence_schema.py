from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))

from arc3_public_g6_future_quotient import _navigation_machine, validate_result
from metalogic_arc3.protected_future import CompiledCapability, compile_capability


def fixture_result():
    return {
        "parent": "abc123",
        "head": "def456",
        "status": "DIAGNOSTIC",
        "classification": "DIAGNOSTIC",
        "boundary": {"actions": ["U", "D", "L", "R"], "max_depth": 12, "max_states": 49},
        "states": [{"id": "s0", "cell": [0, 0]}],
        "transitions": [{"source": "s0", "action": "U", "target": "s0"}],
        "classes": [["s0"]],
        "witnesses": [],
        "congruence": True,
        "residual": {"missing_interface": "target.projection@1", "reason": "no_projection"},
        "action_count": 0,
        "model_calls": 0,
        "source_inspection": False,
        "target_writes": 0,
    }


class G6EvidenceSchemaContracts(unittest.TestCase):
    def test_navigation_machine_builds_successor_observations_independent_of_order(self):
        navigation = _navigation_machine((0, 0), (1, 1), blocked={(0, 1)})

        self.assertEqual(len(navigation.states), 48)
        self.assertEqual(len(navigation.transitions), 48 * 4)

    def test_navigation_machine_runs_through_generic_quotient_compiler(self):
        navigation = _navigation_machine((0, 0), (1, 1), blocked={(0, 1)})

        capability = compile_capability(
            navigation,
            (0, 0),
            ("observation.visible-board@1", "terminal.goal-cell@1"),
        )

        self.assertIsInstance(capability, CompiledCapability)
        self.assertEqual(capability.program, ("D", "R"))
        self.assertEqual(capability.control_program, capability.program)

    def test_complete_diagnostic_artifact_is_accepted(self):
        validate_result(fixture_result())

    def test_missing_target_write_count_is_rejected(self):
        result = fixture_result()
        del result["target_writes"]

        with self.assertRaisesRegex(ValueError, "missing_evidence_fields:target_writes"):
            validate_result(result)

    def test_diagnostic_cannot_claim_target_writes(self):
        result = fixture_result()
        result["target_writes"] = 1

        with self.assertRaisesRegex(ValueError, "diagnostic_target_write"):
            validate_result(result)

    def test_scientific_boundary_rejects_model_or_source_access(self):
        for field, value in (("model_calls", 1), ("source_inspection", True)):
            with self.subTest(field=field):
                result = fixture_result()
                result[field] = value

                with self.assertRaisesRegex(ValueError, "hard_scientific_boundary"):
                    validate_result(result)


if __name__ == "__main__":
    unittest.main()
