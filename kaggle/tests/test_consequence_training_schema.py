import copy
import unittest

from arc3_public_consequence_training import (
    record_warranted_level,
    validate_training_result,
)


def fixture_training_result():
    return {
        "schema": "arc3.consequence-training@1",
        "head": "abc",
        "levels": [
            {
                "level": level,
                "terminal_warrant": {
                    "consequence": "PROGRESS",
                    "evidence_ref": f"run:G{level}",
                },
                "examples": [
                    {"example_id": f"G{level}:{slot}", "slot_index": slot}
                    for slot in range(6)
                ],
            }
            for level in (3, 4, 5)
        ],
        "corpus_id": "corpus",
        "adapter_id": "adapter",
        "warrant_id": "warrant",
        "model_calls": 0,
        "source_inspection": False,
    }


def point_frame(row, col):
    grid = [[0 for _ in range(8)] for _ in range(8)]
    grid[row][col] = 7
    return grid


class ConsequenceTrainingSchema(unittest.TestCase):
    def test_corpus_contains_six_warranted_slots_per_level(self):
        result = fixture_training_result()

        validate_training_result(result, executing_head="abc")

        self.assertEqual(
            [len(level["examples"]) for level in result["levels"]],
            [6, 6, 6],
        )

    def test_stale_head_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale_evidence_head"):
            validate_training_result(
                fixture_training_result(),
                executing_head="other",
            )

    def test_nonprogressing_trace_cannot_train_adapter(self):
        result = copy.deepcopy(fixture_training_result())
        result["levels"][1]["terminal_warrant"]["consequence"] = "CONTINUE"

        with self.assertRaisesRegex(ValueError, "terminal_warrant_required"):
            validate_training_result(result, executing_head="abc")

    def test_record_warranted_level_uses_observed_probe_frames(self):
        traces = {
            "R": (point_frame(3, 3), point_frame(3, 4)),
            "U": (point_frame(3, 3), point_frame(2, 3)),
        }
        path = "RURURU"
        codes = {
            "R": (0, 1, 0, 0, 0, 0),
            "U": (1, 0, 0, 0, 0, 0),
        }

        examples = record_warranted_level(
            level=3,
            path=path,
            probe_traces=traces,
            codes=codes,
            warrant_ref="run:G3",
        )

        self.assertEqual(len(examples), 6)
        self.assertEqual([item.intervention.controls[0] for item in examples], list(path))
        self.assertEqual(examples[0].effect.effect_id, examples[2].effect.effect_id)
        self.assertNotEqual(examples[0].effect.effect_id, examples[1].effect.effect_id)

    def test_record_warranted_level_rejects_unobserved_operator(self):
        with self.assertRaisesRegex(ValueError, "missing_probe_trace:U"):
            record_warranted_level(
                level=3,
                path="RRRRRU",
                probe_traces={
                    "R": (point_frame(3, 3), point_frame(3, 4)),
                },
                codes={
                    "R": (0, 1, 0, 0, 0, 0),
                    "U": (1, 0, 0, 0, 0, 0),
                },
                warrant_ref="run:G3",
            )


if __name__ == "__main__":
    unittest.main()
