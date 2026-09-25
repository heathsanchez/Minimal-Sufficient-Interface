from dataclasses import dataclass
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from arc3_public_g6_ordered_history_separator import (
    HISTORY_PAIRS,
    SUFFIXES,
    _semantic_id,
    build_result,
    compare_trials,
    observation_record,
    run_trial,
    validate_result,
)
from metalogic_arc3.protected_future import canonical_digest
from metalogic_arc3.semantic_path import _selector_controls


@dataclass
class FakeFrame:
    frame: object
    levels_completed: int = 5
    state: str = "GameState.NOT_FINISHED"


def source_grid(bits=(1, 0, 0, 0, 0, 0)):
    grid = [[0 for _ in range(40)] for _ in range(18)]
    for index, bit in enumerate(bits):
        color = 5 if bit else 1
        row = 1 + 3 * index
        for start in (1, 7, 13):
            for column in range(start, start + 3):
                grid[row][column] = color
    return grid


class CanonicalObservationContracts(unittest.TestCase):
    def test_observation_records_exact_public_change(self):
        prefix = source_grid()
        changed = copy.deepcopy(prefix)
        changed[0][10] = 5

        observed = observation_record(prefix, FakeFrame(changed), ("U", "L"))

        self.assertEqual(
            observed["changes"],
            [{"row": 0, "column": 10, "before": 0, "after": 5}],
        )
        self.assertEqual(observed["source_bits"], [1, 0, 0, 0, 0, 0])
        self.assertEqual(observed["trace"], ["U", "L"])
        self.assertEqual(observed["level"], 5)
        self.assertEqual(observed["state"], "GameState.NOT_FINISHED")

    def test_container_type_does_not_change_visible_digest(self):
        prefix = source_grid()
        list_observation = observation_record(prefix, FakeFrame(prefix), ())
        tuple_observation = observation_record(
            tuple(tuple(row) for row in prefix),
            FakeFrame(tuple(tuple(row) for row in prefix)),
            (),
        )

        self.assertEqual(
            list_observation["visible_digest"],
            tuple_observation["visible_digest"],
        )

    def test_one_pixel_change_changes_digest_and_explicit_delta(self):
        prefix = source_grid()
        changed = copy.deepcopy(prefix)
        changed[17][39] = 7

        unchanged = observation_record(prefix, FakeFrame(prefix), ())
        observed = observation_record(prefix, FakeFrame(changed), ("R",))

        self.assertNotEqual(observed["visible_digest"], unchanged["visible_digest"])
        self.assertEqual(
            observed["changes"],
            [{"row": 17, "column": 39, "before": 0, "after": 7}],
        )

    def test_dimension_mismatch_fails_closed(self):
        prefix = source_grid()
        with self.assertRaisesRegex(ValueError, "observation_dimensions"):
            observation_record(prefix, FakeFrame(prefix[:-1]), ())


def protected_observation(digest="same", trace=(), *, first=False):
    return {
        "visible_digest": canonical_digest(("fixture-visible", digest)),
        "changes": [],
        "source_bits": [1, 0, 0, 0, 0, 0],
        "level": 5,
        "state": "GameState.NOT_FINISHED",
        "trace": list(trace),
        "diagnostic_first": first,
    }


def trial(history, suffix, *, first="first", endpoint="same", response="same"):
    prefix = "RRRRUULLUU"
    prefix_observation = protected_observation("prefix", tuple(prefix))
    row = {
        "history": history,
        "endpoint": history[-1],
        "suffix": suffix,
        "prefix_digest": "prefix",
        "prefix_observation": prefix_observation,
        "first_observation": protected_observation(
            first, prefix + history[:1], first=True
        ),
        "endpoint_observation": protected_observation(endpoint, prefix + history),
        "suffix_observation": protected_observation(
            response, prefix + history + suffix
        ),
        "action_count": 12 + len(suffix),
        "target_writes": 0,
        "submit_clicks": 0,
    }
    row["semantic_id"] = _semantic_id(row)
    return row


class SeparatorBoundaryContracts(unittest.TestCase):
    def test_first_intermediate_difference_alone_is_not_separator(self):
        left = trial("UL", "R", first="after-U")
        right = trial("LL", "R", first="after-L")

        comparison = compare_trials(left, right)

        self.assertFalse(comparison["separated"])
        self.assertEqual(comparison["witnesses"], [])

    def test_shared_endpoint_visible_difference_is_separator(self):
        left = trial("UL", "", endpoint="left-end", response="left-end")
        right = trial("LL", "", endpoint="right-end", response="right-end")

        comparison = compare_trials(left, right)

        self.assertTrue(comparison["separated"])
        self.assertEqual(comparison["witnesses"][0]["phase"], "endpoint")
        self.assertIn("visible_digest", comparison["witnesses"][0]["fields"])

    def test_common_suffix_response_can_separate_equal_endpoints(self):
        left = trial("LU", "R", response="left-response")
        right = trial("UU", "R", response="right-response")

        comparison = compare_trials(left, right)

        self.assertTrue(comparison["separated"])
        self.assertEqual(comparison["witnesses"], [
            {"phase": "suffix", "fields": ["visible_digest"]}
        ])

    def test_different_endpoint_controls_are_not_comparable(self):
        with self.assertRaisesRegex(ValueError, "comparison_endpoint"):
            compare_trials(trial("UL", ""), trial("LU", ""))


def result_fixture(*, separated=False):
    trials = []
    comparisons = []
    for left_history, right_history in HISTORY_PAIRS:
        for suffix in SUFFIXES:
            left = trial(
                left_history,
                suffix,
                response="different" if separated and suffix == "R" else "same",
            )
            right = trial(right_history, suffix)
            trials.extend((left, right))
            comparisons.append(compare_trials(left, right))
    return {
        "schema": "arc3.g6-ordered-history-separator@1",
        "head": "abc",
        "status": "RESPONSE_SEPARATOR_ONLY" if separated else "REJECTED",
        "classification": "RESPONSE_SEPARATOR_ONLY" if separated else "WARRANTED_NEGATIVE",
        "prefix": "RRRRUULLUU",
        "history_pairs": [list(pair) for pair in HISTORY_PAIRS],
        "suffixes": list(SUFFIXES),
        "trials": trials,
        "comparisons": comparisons,
        "action_budget_per_trial": 13,
        "target_writes": 0,
        "submit_clicks": 0,
        "model_calls": 0,
        "source_inspection": False,
    }


class EvidenceContracts(unittest.TestCase):
    def test_complete_negative_is_accepted(self):
        validate_result(result_fixture(), executing_head="abc")

    def test_complete_response_separator_is_accepted(self):
        validate_result(result_fixture(separated=True), executing_head="abc")

    def test_incomplete_census_cannot_be_negative(self):
        result = result_fixture()
        result["trials"].pop()
        with self.assertRaisesRegex(ValueError, "trial_census"):
            validate_result(result, executing_head="abc")

    def test_classification_must_be_derived_from_comparisons(self):
        result = result_fixture(separated=True)
        result["status"] = "REJECTED"
        result["classification"] = "WARRANTED_NEGATIVE"
        with self.assertRaisesRegex(ValueError, "derived_classification"):
            validate_result(result, executing_head="abc")

    def test_forbidden_side_effects_invalidate_result(self):
        for field in ("target_writes", "submit_clicks", "model_calls"):
            result = result_fixture()
            result[field] = 1
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "scientific_boundary"):
                    validate_result(result, executing_head="abc")


DIRECTION_BITS = {
    "D": (1, 1, 0, 0, 0, 0),
    "L": (1, 0, 0, 0, 0, 0),
    "R": (0, 1, 0, 0, 0, 0),
    "U": (1, 0, 0, 0, 0, 1),
}


def public_g6_grid(bits=(0, 0, 0, 0, 0, 0)):
    grid = [[0 for _ in range(64)] for _ in range(64)]
    for index, bit in enumerate(bits):
        color = 5 if bit else 1
        row = 4 + 4 * index
        for start in (1, 7, 13):
            for column in range(start, start + 3):
                grid[row][column] = color
    for column in (4, 5, 6):
        grid[55][column] = 11  # U
    for column in (14, 15, 16):
        grid[60][column] = 11  # D
    for row in (57, 58, 59):
        grid[row][24] = 11  # L
        grid[row][36] = 11  # R
    return grid


class FakePublicEnvironment:
    def __init__(self):
        self.grid = public_g6_grid()
        self.frame = FakeFrame(copy.deepcopy(self.grid))
        discovered = _selector_controls(self.grid)
        self.label_by_click = {(y, x): label for (x, y), label in discovered}
        self.clicked_labels = []

    def click(self, coordinate):
        if coordinate not in self.label_by_click:
            raise AssertionError(f"non-control click:{coordinate}")
        label = self.label_by_click[coordinate]
        self.clicked_labels.append(label)
        bits = DIRECTION_BITS[label]
        for index, bit in enumerate(bits):
            color = 5 if bit else 1
            row = 4 + 4 * index
            for start in (1, 7, 13):
                for column in range(start, start + 3):
                    self.grid[row][column] = color
        self.frame = FakeFrame(copy.deepcopy(self.grid))
        return self.frame


class OrderedHistoryExecutorContracts(unittest.TestCase):
    def test_trial_executes_exact_prefix_history_and_suffix_controls(self):
        environment = FakePublicEnvironment()
        with patch(
            "arc3_public_g6_ordered_history_separator._click_public",
            side_effect=lambda env, coordinate: env.click(coordinate),
        ):
            result = run_trial("UL", "R", enter_g6=lambda: (environment, environment.frame))

        self.assertEqual(environment.clicked_labels, list("RRRRUULLUUULR"))
        self.assertEqual(result["action_count"], 13)
        self.assertEqual(result["first_observation"]["trace"], list("RRRRUULLUUU"))
        self.assertEqual(result["endpoint_observation"]["trace"], list("RRRRUULLUUUL"))
        self.assertEqual(result["suffix_observation"]["trace"], list("RRRRUULLUUULR"))
        self.assertEqual(result["target_writes"], 0)
        self.assertEqual(result["submit_clicks"], 0)

    def test_empty_suffix_reuses_endpoint_as_suffix_observation(self):
        environment = FakePublicEnvironment()
        with patch(
            "arc3_public_g6_ordered_history_separator._click_public",
            side_effect=lambda env, coordinate: env.click(coordinate),
        ):
            result = run_trial("LL", "", enter_g6=lambda: (environment, environment.frame))

        self.assertEqual(environment.clicked_labels, list("RRRRUULLUULL"))
        self.assertEqual(result["action_count"], 12)
        self.assertEqual(result["suffix_observation"], result["endpoint_observation"])

    def test_builder_runs_twenty_fresh_history_trials_for_ten_comparisons(self):
        calls = []

        def runner(history, suffix, _):
            calls.append((history, suffix))
            return trial(history, suffix)

        result = build_result(head="abc", runner=runner)

        self.assertEqual(len(calls), 20)
        self.assertEqual(len(result["trials"]), 20)
        self.assertEqual(len(result["comparisons"]), 10)
        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")

    def test_exception_preserves_completed_trials_as_non_evidence(self):
        calls = []

        def runner(history, suffix, _):
            if len(calls) == 3:
                raise RuntimeError("probe broke")
            calls.append((history, suffix))
            return trial(history, suffix)

        result = build_result(head="abc", runner=runner)

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(len(result["trials"]), 3)
        self.assertEqual(result["residual"]["reason"], "trial_exception")

    def test_common_prefix_drift_is_non_evidence(self):
        calls = 0

        def runner(history, suffix, _):
            nonlocal calls
            calls += 1
            row = trial(history, suffix)
            if calls == 20:
                row["prefix_digest"] = "drift"
                row["semantic_id"] = _semantic_id(row)
            return row

        result = build_result(head="abc", runner=runner)

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertIn(
            result["residual"]["reason"],
            {"common_prefix_drift", "trial_exception"},
        )

    def test_missing_control_fails_before_any_noncontrol_click(self):
        environment = FakePublicEnvironment()
        for row in (57, 58, 59):
            environment.grid[row][36] = 0
        environment.frame = FakeFrame(copy.deepcopy(environment.grid))

        with self.assertRaisesRegex(ValueError, "selector_direction_geometry"):
            run_trial("UL", "", enter_g6=lambda: (environment, environment.frame))
        self.assertEqual(environment.clicked_labels, [])


class ExecutorEvidenceFailureContracts(unittest.TestCase):
    def test_over_budget_trial_is_rejected_even_with_fresh_semantic_id(self):
        result = result_fixture()
        result["trials"][0]["action_count"] = 14
        result["trials"][0]["semantic_id"] = _semantic_id(result["trials"][0])
        with self.assertRaisesRegex(ValueError, "trial_action_count"):
            validate_result(result, executing_head="abc")

    def test_stale_head_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale_evidence_head"):
            validate_result(result_fixture(), executing_head="other")

    def test_stale_trial_semantic_id_is_rejected(self):
        result = result_fixture()
        result["trials"][0]["endpoint_observation"]["source_bits"] = [0] * 6
        result["trials"][0]["suffix_observation"]["source_bits"] = [0] * 6
        with self.assertRaisesRegex(ValueError, "trial_semantic_id"):
            validate_result(result, executing_head="abc")

    def test_trial_target_write_is_rejected(self):
        result = result_fixture()
        result["trials"][0]["target_writes"] = 1
        result["trials"][0]["semantic_id"] = _semantic_id(result["trials"][0])
        with self.assertRaisesRegex(ValueError, "scientific_boundary"):
            validate_result(result, executing_head="abc")

    def test_public_prefix_state_drift_cannot_seal_negative(self):
        calls = 0

        def runner(history, suffix, _):
            nonlocal calls
            calls += 1
            row = trial(history, suffix)
            if calls % 2 == 0:
                row["prefix_observation"]["state"] = "GameState.GAME_OVER"
                row["semantic_id"] = _semantic_id(row)
            return row

        result = build_result(head="abc", runner=runner)

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertIn(
            result["residual"]["reason"],
            {"common_prefix_drift", "trial_exception"},
        )

    def test_malformed_observation_payload_cannot_be_rehashed_into_evidence(self):
        mutations = (
            ("visible_digest", None),
            ("changes", "not-a-change-list"),
            ("source_bits", []),
            ("level", -100),
            ("state", None),
        )
        for field, value in mutations:
            result = result_fixture()
            for row in result["trials"][:2]:
                row["endpoint_observation"][field] = value
                row["suffix_observation"][field] = value
                row["semantic_id"] = _semantic_id(row)
            result["comparisons"][0] = compare_trials(
                result["trials"][0], result["trials"][1]
            )
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "trial_observation"):
                    validate_result(result, executing_head="abc")

    def test_trace_must_equal_declared_prefix_history_and_suffix(self):
        result = result_fixture()
        for row in result["trials"][:2]:
            row["endpoint_observation"]["trace"].append("TARGET_WRITE")
            row["suffix_observation"]["trace"].append("TARGET_WRITE")
            row["semantic_id"] = _semantic_id(row)
        result["comparisons"][0] = compare_trials(
            result["trials"][0], result["trials"][1]
        )
        with self.assertRaisesRegex(ValueError, "trial_trace"):
            validate_result(result, executing_head="abc")

    def test_empty_suffix_observation_must_equal_endpoint_observation(self):
        result = result_fixture()
        row = result["trials"][0]
        row["suffix_observation"] = copy.deepcopy(row["suffix_observation"])
        row["suffix_observation"]["visible_digest"] = "f" * 64
        row["semantic_id"] = _semantic_id(row)
        result["comparisons"][0] = compare_trials(
            result["trials"][0], result["trials"][1]
        )
        with self.assertRaisesRegex(ValueError, "empty_suffix_observation"):
            validate_result(result, executing_head="abc")


class HostedWorkflowContracts(unittest.TestCase):
    def test_workflow_qualifies_exact_public_zero_write_gate(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (
            root
            / ".github/workflows/arc3-public-g6-ordered-history-separator.yml"
        ).read_text()
        required = (
            "arc3-public-g6-ordered-history-separator-v1",
            "7652836056c59e044f093e3c13ed7438c814169e",
            "tn36-ef4dde99",
            "python -m unittest discover -s kaggle/tests -v",
            "arc3_public_g6_ordered_history_separator.py",
            'validate_result(result, executing_head=os.environ["GITHUB_SHA"])',
            'assert result["target_writes"] == 0',
            'assert result["submit_clicks"] == 0',
            "if: always()",
            "actions/upload-artifact@v4",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, workflow)

if __name__ == "__main__":
    unittest.main()
