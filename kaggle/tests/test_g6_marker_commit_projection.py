import copy
import unittest

from arc3_public_g6_marker_commit_projection import (
    EVENT_STEPS,
    ROUTE,
    build_result,
    candidate_semantic_id,
    projection_from_trace,
    validate_result,
)


CODES = {
    "R": [0, 1, 0, 0, 0, 0],
    "U": [1, 0, 0, 0, 0, 1],
    "L": [1, 0, 0, 0, 0, 0],
}


def qualified_steps():
    rows = []
    marker_columns = {step: 62 - step // 2 for step in EVENT_STEPS}
    for step, control in enumerate(ROUTE, start=1):
        rows.append(
            {
                "step": step,
                "control": control,
                "source_code": CODES[control],
                "marker_position": (
                    [1, marker_columns[step]] if step in marker_columns else None
                ),
            }
        )
    return rows


def candidate(*, progressed, selector="commit"):
    columns, events = projection_from_trace(ROUTE, qualified_steps(), selector=selector)
    row = {
        "selector": selector,
        "columns": [list(column) for column in columns],
        "events": events,
        "progressed": progressed,
        "terminal": [6 if progressed else 5, "GameState.NOT_FINISHED"],
        "target_writes": 7,
        "submit_clicks": 1,
        "action_count": 20,
    }
    row["semantic_id"] = candidate_semantic_id(row)
    return row


class MarkerCommitProjection(unittest.TestCase):
    def test_commit_projection_uses_event_after_state_in_spatial_order(self):
        columns, events = projection_from_trace(
            ROUTE,
            qualified_steps(),
            selector="commit",
        )

        self.assertEqual(
            columns,
            (
                (1, 0, 0, 0, 0, 0),
                (1, 0, 0, 0, 0, 1),
                (1, 0, 0, 0, 0, 0),
                (1, 0, 0, 0, 0, 1),
                (0, 1, 0, 0, 0, 0),
                (0, 1, 0, 0, 0, 0),
            ),
        )
        self.assertEqual([row["controls"] for row in events], ["UL", "UU", "LL", "UU", "RR", "RR"])
        self.assertEqual([row["marker_rank"] for row in events], list(range(6)))

    def test_first_click_ablation_differs_only_at_mixed_event(self):
        commit, _ = projection_from_trace(ROUTE, qualified_steps(), selector="commit")
        first, _ = projection_from_trace(ROUTE, qualified_steps(), selector="first")

        self.assertEqual(first[1:], commit[1:])
        self.assertEqual(first[0], (1, 0, 0, 0, 0, 1))
        self.assertEqual(commit[0], (1, 0, 0, 0, 0, 0))

    def test_projection_rejects_missing_marker_boundary(self):
        steps = qualified_steps()
        steps[5]["marker_position"] = None

        with self.assertRaisesRegex(ValueError, "marker_event_census"):
            projection_from_trace(ROUTE, steps, selector="commit")

    def test_projection_rejects_non_binary_source_code(self):
        steps = qualified_steps()
        steps[1]["source_code"] = [0, 1, 2, 0, 0, 0]

        with self.assertRaisesRegex(ValueError, "source_code"):
            projection_from_trace(ROUTE, steps, selector="commit")


class MarkerCommitEvidence(unittest.TestCase):
    def test_failed_candidate_is_warranted_negative_without_variant_search(self):
        result = build_result(
            head="abc123",
            runner=lambda selector="commit": candidate(progressed=False, selector=selector),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")
        self.assertEqual(result["candidate"]["selector"], "commit")
        self.assertEqual(result["verification"], [])
        self.assertIsNone(result["ablation"])

    def test_progress_requires_two_exact_replays_and_first_click_ablation(self):
        calls = []

        def runner(selector="commit"):
            calls.append(selector)
            return candidate(progressed=selector == "commit", selector=selector)

        result = build_result(head="abc123", runner=runner)

        self.assertEqual(result["status"], "PROMOTED")
        self.assertEqual(result["classification"], "WARRANTED_POSITIVE")
        self.assertEqual(calls, ["commit", "commit", "commit", "first"])
        self.assertEqual(len(result["verification"]), 2)
        self.assertFalse(result["ablation"]["progressed"])

    def test_replay_identity_drift_is_non_evidence(self):
        rows = [candidate(progressed=True) for _ in range(3)]
        rows[1]["columns"][0][0] = 0
        rows[1]["events"][0]["source_code"][0] = 0
        rows[1]["semantic_id"] = candidate_semantic_id(rows[1])
        calls = iter(rows)

        result = build_result(head="abc123", runner=lambda selector="commit": next(calls))

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(result["residual"]["reason"], "verification_identity_drift")
        self.assertEqual(len(result["verification"]), 2)

    def test_residual_seal_rejects_tampered_preserved_verification(self):
        rows = [candidate(progressed=True) for _ in range(3)]
        rows[1]["columns"][0][0] = 0
        rows[1]["events"][0]["source_code"][0] = 0
        rows[1]["semantic_id"] = candidate_semantic_id(rows[1])
        calls = iter(rows)
        result = build_result(
            head="abc123",
            runner=lambda selector="commit": next(calls),
        )
        result["verification"][0]["events"][0]["selected_control"] = "U"
        result["verification"][0]["semantic_id"] = candidate_semantic_id(
            result["verification"][0]
        )

        with self.assertRaisesRegex(ValueError, "candidate_event_evidence"):
            validate_result(result, executing_head="abc123")

    def test_exact_head_and_model_free_boundary_seal(self):
        result = build_result(
            head="abc123",
            runner=lambda selector="commit": candidate(progressed=False, selector=selector),
        )

        self.assertEqual(validate_result(result, executing_head="abc123"), result)
        tampered = copy.deepcopy(result)
        tampered["model_calls"] = 1
        with self.assertRaisesRegex(ValueError, "scientific_boundary"):
            validate_result(tampered, executing_head="abc123")

    def test_seal_rejects_a_relabelled_selected_control(self):
        result = build_result(
            head="abc123",
            runner=lambda selector="commit": candidate(progressed=False, selector=selector),
        )
        result["candidate"]["events"][0]["selected_control"] = "U"
        result["candidate"]["semantic_id"] = candidate_semantic_id(result["candidate"])

        with self.assertRaisesRegex(ValueError, "candidate_event_evidence"):
            validate_result(result, executing_head="abc123")


if __name__ == "__main__":
    unittest.main()
