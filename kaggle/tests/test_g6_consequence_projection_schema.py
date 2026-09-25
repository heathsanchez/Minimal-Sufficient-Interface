import copy
import unittest

from arc3_public_g6_consequence_projection import (
    pair_route,
    validate_g6_result,
)


def replay_identity():
    return {
        "adapter_id": "adapter",
        "warrant_id": "warrant",
        "effect_classes": [f"effect:{index}" for index in range(6)],
        "columns": [[0, 1, 0, 0, 0, 0] for _ in range(6)],
        "controls": ["RR", "RR", "UU", "LL", "UU", "UL"],
        "terminal": [6, "NOT_FINISHED"],
        "progressed": True,
    }


def fixture_g6_result(*, status, unknown_slots=()):
    base = {
        "schema": "arc3.g6-consequence-projection@1",
        "head": "abc",
        "adapter_id": "adapter",
        "warrant_id": "warrant",
        "model_calls": 0,
        "source_inspection": False,
    }
    if status == "RESIDUAL":
        return {
            **base,
            "status": "RESIDUAL",
            "classification": "EXACT_RESIDUAL",
            "target_writes": 0,
            "unknown_slots": list(unknown_slots),
            "residual": {
                "missing_interface": "target.projection@1",
                "reason": "unseen_or_ambiguous_effect_class",
                "evidence": [f"effect:{slot}" for slot in unknown_slots],
            },
        }
    candidate = replay_identity()
    if status == "REJECTED":
        candidate["progressed"] = False
        return {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "target_writes": 7,
            "candidate": candidate,
            "verification": [],
            "ablation": {"without_adapter": "RESIDUAL"},
        }
    return {
        **base,
        "status": "PROMOTED",
        "classification": "WARRANTED_POSITIVE",
        "target_writes": 7,
        "candidate": candidate,
        "verification": [copy.deepcopy(candidate), copy.deepcopy(candidate)],
        "ablation": {"without_adapter": "RESIDUAL"},
    }


class G6ConsequenceProjectionSchema(unittest.TestCase):
    def test_route_is_partitioned_into_six_ordered_macro_effects(self):
        self.assertEqual(
            pair_route("RRRRUULLUUUL"),
            ("RR", "RR", "UU", "LL", "UU", "UL"),
        )

    def test_route_partition_rejects_odd_arity(self):
        with self.assertRaisesRegex(ValueError, "route_pair_arity"):
            pair_route("RRU")

    def test_unknown_macro_effect_performs_zero_target_writes(self):
        result = fixture_g6_result(status="RESIDUAL", unknown_slots=(5,))

        validate_g6_result(result, executing_head="abc")

        self.assertEqual(result["target_writes"], 0)

    def test_residual_with_target_write_is_rejected(self):
        result = fixture_g6_result(status="RESIDUAL", unknown_slots=(5,))
        result["target_writes"] = 1

        with self.assertRaisesRegex(ValueError, "residual_target_write"):
            validate_g6_result(result, executing_head="abc")

    def test_replay_identity_includes_adapter_classes_outputs_and_controls(self):
        result = fixture_g6_result(status="PROMOTED")
        result["verification"][1]["adapter_id"] = "different"

        with self.assertRaisesRegex(ValueError, "replay_identity_mismatch"):
            validate_g6_result(result, executing_head="abc")

    def test_failed_unique_projection_is_not_mislabeled_exact_residual(self):
        result = fixture_g6_result(status="REJECTED")

        validate_g6_result(result, executing_head="abc")

        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")
        self.assertGreater(result["target_writes"], 0)

    def test_stale_head_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale_evidence_head"):
            validate_g6_result(
                fixture_g6_result(status="PROMOTED"),
                executing_head="other",
            )


if __name__ == "__main__":
    unittest.main()
