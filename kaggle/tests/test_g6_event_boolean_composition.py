import unittest
import copy
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from arc3_public_g6_event_boolean_composition import (
    EVENT_SIGNATURES,
    collect_stable_codes,
    compose_bits,
    event_segments,
    spatial_columns,
    validate_result,
    _source_head,
    _semantic_id,
    build_result,
)


ROUTE = "RRRRUULLUUUL"
EVENTS = tuple(
    (step, (1, column))
    for step, column in zip((2, 4, 6, 8, 10, 12), (61, 60, 59, 58, 57, 56))
)


class EventSegmentationContracts(unittest.TestCase):
    def test_six_observed_events_define_six_two_control_segments(self):
        self.assertEqual(
            event_segments(ROUTE, EVENTS),
            (
                ("RR", (1, 61)),
                ("RR", (1, 60)),
                ("UU", (1, 59)),
                ("LL", (1, 58)),
                ("UU", (1, 57)),
                ("UL", (1, 56)),
            ),
        )

    def test_missing_duplicate_or_nonterminal_event_fails_closed(self):
        malformed = (
            EVENTS[:-1],
            EVENTS[:-1] + ((10, (1, 56)),),
            EVENTS[:-1] + ((11, (1, 56)),),
            EVENTS[:-1] + ((12, EVENTS[0][1]),),
        )
        for events in malformed:
            with self.subTest(events=events):
                with self.assertRaisesRegex(ValueError, "marker_event_partition"):
                    event_segments(ROUTE, events)

    def test_non_two_control_interval_fails_closed(self):
        events = ((1, (1, 61)),) + EVENTS[1:]
        with self.assertRaisesRegex(ValueError, "marker_event_segment_arity"):
            event_segments(ROUTE, events)


class BooleanCompositionContracts(unittest.TestCase):
    def test_exactly_five_remaining_observable_signatures_are_declared(self):
        self.assertEqual(EVENT_SIGNATURES, ("000", "100", "101", "110", "111"))

    def test_each_signature_maps_observed_00_10_11_rows_exactly(self):
        left = (0, 1, 1, 0, 1, 0)
        right = (0, 0, 1, 0, 0, 0)
        for signature in EVENT_SIGNATURES:
            with self.subTest(signature=signature):
                self.assertEqual(
                    compose_bits(signature, left, right)[:3],
                    tuple(int(bit) for bit in signature),
                )

    def test_marker_spatial_order_not_chronology_orders_target_columns(self):
        codes = {
            "R": (0, 1, 0, 0, 0, 0),
            "U": (1, 0, 0, 0, 0, 1),
            "L": (1, 0, 0, 0, 0, 0),
        }
        chronological = event_segments(ROUTE, EVENTS)
        expected = tuple(
            compose_bits("101", codes[pair[0]], codes[pair[1]])
            for pair, _ in reversed(chronological)
        )
        self.assertEqual(spatial_columns(chronological, codes, "101"), expected)

    def test_repeated_control_with_incompatible_code_fails_closed(self):
        observations = (
            ("R", (0, 1, 0, 0, 0, 0)),
            ("R", (1, 0, 0, 0, 0, 0)),
        )
        with self.assertRaisesRegex(ValueError, "inconsistent_control_code"):
            collect_stable_codes(observations)


def candidate(signature="101", progressed=True, semantic_id="same"):
    row = {
        "signature": signature,
        "segments": ["UL", "UU", "LL", "UU", "RR", "RR"],
        "event_positions": [[1, column] for column in range(56, 62)],
        "event_trace": [
            {"step": step, "position": [1, column]}
            for step, column in zip((2, 4, 6, 8, 10, 12), (61, 60, 59, 58, 57, 56))
        ],
        "codes": {
            "L": [1, 0, 0, 0, 0, 0],
            "R": [0, 1, 0, 0, 0, 0],
            "U": [1, 0, 0, 0, 0, 1],
        },
        "columns": [],
        "start_level": 5,
        "terminal": [6 if progressed else 5, "GameState.NOT_FINISHED"],
        "progressed": progressed,
        "target_writes": 0,
        "writes": [],
        "action_count": 19,
    }
    row["columns"] = [
        list(column)
        for column in spatial_columns(
            tuple((segment, tuple(position)) for segment, position in zip(row["segments"], row["event_positions"])),
            row["codes"],
            signature,
        )
    ]
    row["semantic_id"] = _semantic_id(row) if semantic_id == "same" else semantic_id
    return row


def result_fixture(status="REJECTED"):
    variants = [candidate(signature, progressed=False) for signature in EVENT_SIGNATURES]
    base = {
        "schema": "arc3.g6-event-boolean-composition@1",
        "head": "abc",
        "route": ROUTE,
        "signatures": list(EVENT_SIGNATURES),
        "variants": variants,
        "model_calls": 0,
        "source_inspection": False,
        "action_budget_per_run": 50,
    }
    if status == "REJECTED":
        return {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "verification": [],
            "target_writes": sum(row["target_writes"] for row in variants),
        }
    selected = candidate()
    variants[EVENT_SIGNATURES.index(selected["signature"])] = copy.deepcopy(selected)
    return {
        **base,
        "status": "PROMOTED",
        "classification": "WARRANTED_POSITIVE",
        "candidate": selected,
        "verification": [copy.deepcopy(selected), copy.deepcopy(selected)],
        "target_writes": selected["target_writes"] * 3,
    }


class EvidenceContracts(unittest.TestCase):
    def test_local_source_head_is_bound_to_experiment_repo_not_process_cwd(self):
        repo_root = Path(__file__).resolve().parents[2]
        expected = subprocess.check_output(
            ("git", "rev-parse", "HEAD"),
            cwd=repo_root,
            text=True,
        ).strip()
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(("git", "init", "-q"), cwd=temporary, check=True)
            subprocess.run(
                (
                    "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                    "commit", "--allow-empty", "-qm", "foreign",
                ),
                cwd=temporary,
                check=True,
            )
            try:
                os.chdir(temporary)
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("GITHUB_SHA", None)
                    self.assertEqual(_source_head(), expected)
            finally:
                os.chdir(original)

    def test_complete_five_signature_negative_is_accepted(self):
        validate_result(result_fixture(), executing_head="abc")

    def test_model_calls_or_source_inspection_are_forbidden(self):
        for key, value in (("model_calls", 1), ("source_inspection", True)):
            result = result_fixture()
            result[key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "scientific_boundary"):
                    validate_result(result, executing_head="abc")

    def test_negative_must_preserve_exact_complete_family(self):
        result = result_fixture()
        result["variants"].pop()
        with self.assertRaisesRegex(ValueError, "boolean_family_census"):
            validate_result(result, executing_head="abc")

    def test_action_budget_is_enforced_per_variant(self):
        result = result_fixture()
        result["variants"][2]["action_count"] = 51
        with self.assertRaisesRegex(ValueError, "action_budget"):
            validate_result(result, executing_head="abc")

    def test_promotion_requires_two_matching_progressing_replays(self):
        result = result_fixture(status="PROMOTED")
        result["verification"][1] = candidate("100", progressed=True)
        with self.assertRaisesRegex(ValueError, "replay_identity"):
            validate_result(result, executing_head="abc")

    def test_each_run_must_retain_complete_reconstructable_evidence(self):
        for missing in (
            "terminal", "progressed", "segments", "event_positions", "event_trace",
            "codes", "columns", "semantic_id",
        ):
            result = result_fixture()
            result["variants"][0].pop(missing)
            with self.subTest(missing=missing):
                with self.assertRaisesRegex(ValueError, "run_evidence"):
                    validate_result(result, executing_head="abc")

    def test_replay_digest_is_recomputed_from_semantics(self):
        result = result_fixture(status="PROMOTED")
        stale_id = result["verification"][1]["semantic_id"]
        result["verification"][1] = candidate("100", progressed=True)
        result["verification"][1]["semantic_id"] = stale_id
        with self.assertRaisesRegex(ValueError, "run_semantic_id"):
            validate_result(result, executing_head="abc")

    def test_promoted_candidate_must_be_sole_progressing_census_variant(self):
        result = result_fixture(status="PROMOTED")
        index = EVENT_SIGNATURES.index(result["candidate"]["signature"])
        result["variants"][index] = candidate(
            result["candidate"]["signature"],
            progressed=False,
        )
        with self.assertRaisesRegex(ValueError, "promoted_census"):
            validate_result(result, executing_head="abc")

    def test_ambiguous_progress_preserves_all_completed_variants_as_non_evidence(self):
        rows = {signature: candidate(signature, progressed=signature in {"100", "101"}) for signature in EVENT_SIGNATURES}

        result = build_result(head="abc", runner=lambda signature, _: copy.deepcopy(rows[signature]))

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(len(result["variants"]), 5)
        self.assertEqual(result["residual"]["reason"], "ambiguous_progressing_signature")

    def test_complete_negative_build_retains_all_five_variants(self):
        rows = {signature: candidate(signature, progressed=False) for signature in EVENT_SIGNATURES}

        result = build_result(head="abc", runner=lambda signature, _: copy.deepcopy(rows[signature]))

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual([row["signature"] for row in result["variants"]], list(EVENT_SIGNATURES))

    def test_failed_replay_preserves_candidate_and_completed_replay(self):
        calls = {signature: 0 for signature in EVENT_SIGNATURES}

        def runner(signature, _):
            calls[signature] += 1
            if signature == "101" and calls[signature] == 3:
                raise RuntimeError("replay broke")
            return candidate(signature, progressed=signature == "101")

        result = build_result(head="abc", runner=runner)

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(len(result["variants"]), 5)
        self.assertEqual(len(result["verification"]), 1)
        self.assertEqual(result["residual"]["reason"], "candidate_run_exception")

    def test_stale_head_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale_evidence_head"):
            validate_result(result_fixture(), executing_head="other")


class HostedWorkflowContracts(unittest.TestCase):
    def test_workflow_seals_exact_public_event_boolean_gate(self):
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (
            repo_root / ".github/workflows/arc3-public-g6-event-boolean-composition.yml"
        ).read_text()
        required = (
            "arc3-public-g6-event-boolean-composition-v1",
            "tn36-ef4dde99",
            "python -m unittest discover -s kaggle/tests -v",
            "arc3_public_g6_event_boolean_composition.py",
            "validate_result(result, executing_head=os.environ[\"GITHUB_SHA\"])",
            "actions/upload-artifact@v4",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, workflow)


if __name__ == "__main__":
    unittest.main()
