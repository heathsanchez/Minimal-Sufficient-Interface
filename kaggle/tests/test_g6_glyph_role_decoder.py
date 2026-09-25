import copy
import unittest

from arc3_public_g6_glyph_role_decoder import (
    ROLE_ORDER,
    build_result,
    candidate_semantic_id,
    canonical_glyph_family,
    compile_observed_candidate,
    compile_role_codebook,
    event_role_records,
    project_spatial_columns,
    run_candidate,
    solved_codes_from_training,
    validate_result,
)
from metalogic_arc3.protected_future import UnknownResidual


EMPTY = [[5] * 4 for _ in range(4)]
MOVER = [[4] * 4 for _ in range(4)]
LINE = [
    [11, 5, 5, 5],
    [11, 5, 5, 5],
    [5, 5, 5, 5],
    [5, 5, 5, 5],
]
INVERTED_LINE = [
    [11, 11, 11, 11],
    [5, 11, 11, 11],
    [5, 11, 11, 11],
    [11, 11, 11, 11],
]
CHECKER = [
    [11, 5, 11, 5],
    [5, 11, 5, 11],
    [11, 5, 11, 5],
    [5, 11, 5, 11],
]

CODES = {
    "R": [0, 1, 0, 0, 0, 0],
    "L": [1, 0, 0, 0, 0, 0],
    "I": [1, 0, 0, 1, 0, 0],
    "X": [1, 0, 1, 0, 0, 0],
    "T": [1, 1, 1, 1, 1, 1],
    "S": [0, 0, 0, 1, 0, 0],
}


def event(rank, controls, source, destination):
    return {
        "marker_rank": rank,
        "controls": controls,
        "trace_patches": [source, MOVER, destination],
    }


def chronological_events():
    return [
        event(5, "RR", LINE, EMPTY),
        event(4, "RR", EMPTY, EMPTY),
        event(3, "UU", EMPTY, CHECKER),
        event(2, "LL", CHECKER, EMPTY),
        event(1, "UU", EMPTY, EMPTY),
        event(0, "UL", EMPTY, LINE),
    ]


def codebook_inputs():
    solved = {
        "I": {"output": CODES["I"], "levels": [4]},
        "X": {"output": CODES["X"], "levels": [5]},
        "T": {"output": CODES["T"], "levels": [5]},
        "S": {"output": CODES["S"], "levels": [5]},
    }
    g6 = {"R": CODES["R"], "L": CODES["L"]}
    return solved, g6


def training_fixture():
    return {
        "levels": [
            {
                "level": 3,
                "terminal_warrant": {"consequence": "PROGRESS"},
                "examples": [
                    {"action": {"controls": ["R"]}, "output": CODES["R"]},
                ],
            },
            {
                "level": 4,
                "terminal_warrant": {"consequence": "PROGRESS"},
                "examples": [
                    {"action": {"controls": ["I"]}, "output": CODES["I"]},
                ],
            },
            {
                "level": 5,
                "terminal_warrant": {"consequence": "PROGRESS"},
                "examples": [
                    {"action": {"controls": ["X"]}, "output": CODES["X"]},
                    {"action": {"controls": ["T"]}, "output": CODES["T"]},
                    {"action": {"controls": ["S"]}, "output": CODES["S"]},
                ],
            },
        ]
    }


def candidate(progressed=False):
    solved, g6 = codebook_inputs()
    codebook = compile_role_codebook(solved, g6)
    roles = event_role_records(chronological_events())
    columns = project_spatial_columns(roles, codebook)
    row = {
        "status": "CANDIDATE",
        "roles": roles,
        "codebook": codebook,
        "columns": [list(column) for column in columns],
        "progressed": progressed,
        "terminal": [6 if progressed else 5, "GameState.NOT_FINISHED"],
        "target_writes": 17,
        "submit_clicks": 1,
        "action_count": 34,
    }
    row["semantic_id"] = candidate_semantic_id(row)
    return row


class GlyphCanonicalization(unittest.TestCase):
    def test_line_family_is_scale_normalized_but_orientation_preserved(self):
        line_two = {(0, 0), (1, 0)}
        line_three = {(0, 0), (1, 0), (2, 0)}

        self.assertEqual(canonical_glyph_family(line_two), ("line", "vertical"))
        self.assertEqual(
            canonical_glyph_family(line_two),
            canonical_glyph_family(line_three),
        )
        self.assertEqual(
            canonical_glyph_family({(0, 0), (0, 1)}),
            ("line", "horizontal"),
        )

    def test_checker_family_is_scale_normalized(self):
        checker_four = {
            (row, column)
            for row in range(4)
            for column in range(4)
            if (row + column) % 2 == 0
        }
        checker_five = {
            (row, column)
            for row in range(5)
            for column in range(5)
            if (row + column) % 2 == 0
        }

        self.assertEqual(canonical_glyph_family(checker_four), ("checker",))
        self.assertEqual(
            canonical_glyph_family(checker_four),
            canonical_glyph_family(checker_five),
        )


class GlyphRoleProjection(unittest.TestCase):
    def test_endpoint_role_is_local_complement_invariant(self):
        events = chronological_events()
        events[0] = event(5, "RR", INVERTED_LINE, EMPTY)

        records = event_role_records(events)

        self.assertEqual(records[0]["role"], "endpoint.depart")
        self.assertEqual(records[0]["families"], [["line", "vertical"], ["empty"]])

    def test_visible_event_roles_form_the_nested_six_role_census(self):
        records = event_role_records(chronological_events())

        self.assertEqual([row["role"] for row in records], list(ROLE_ORDER))
        self.assertEqual([row["marker_rank"] for row in records], [5, 4, 3, 2, 1, 0])

    def test_role_projection_compiles_only_the_supervised_spatial_columns(self):
        solved, g6 = codebook_inputs()
        codebook = compile_role_codebook(solved, g6)
        columns = project_spatial_columns(
            event_role_records(chronological_events()),
            codebook,
        )

        self.assertEqual(
            columns,
            (
                (1, 0, 0, 0, 0, 0),  # endpoint.arrive -> L
                (0, 0, 0, 1, 0, 0),  # plain.after -> S
                (1, 1, 1, 1, 1, 1),  # checker.exit -> T
                (1, 0, 1, 0, 0, 0),  # checker.enter -> X
                (1, 0, 0, 1, 0, 0),  # plain.before -> I
                (0, 1, 0, 0, 0, 0),  # endpoint.depart -> R
            ),
        )

    def test_missing_or_conflicting_supervision_remains_unknown(self):
        solved, g6 = codebook_inputs()
        del solved["T"]
        self.assertIsInstance(compile_role_codebook(solved, g6), UnknownResidual)

        solved, g6 = codebook_inputs()
        solved["X"] = {
            "output": [CODES["X"], CODES["T"]],
            "levels": [5],
        }
        self.assertIsInstance(compile_role_codebook(solved, g6), UnknownResidual)

    def test_non_nested_event_geometry_is_rejected_before_projection(self):
        events = chronological_events()
        events[2] = event(3, "UU", EMPTY, EMPTY)

        with self.assertRaisesRegex(ValueError, "event_role_census"):
            event_role_records(events)

    def test_training_registry_rejects_conflicting_warranted_codes(self):
        training = training_fixture()
        training["levels"][2]["examples"].append(
            {"action": {"controls": ["X"]}, "output": CODES["T"]}
        )

        result = solved_codes_from_training(training)

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.reason, "conflicting_warranted_control_code")

    def test_observed_candidate_submits_one_exact_compiled_projection(self):
        submitted = []

        def executor(columns):
            submitted.append(columns)
            return {
                "progressed": False,
                "terminal": [5, "GameState.NOT_FINISHED"],
                "target_writes": 17,
                "submit_clicks": 1,
                "action_count": 34,
            }

        row = compile_observed_candidate(
            training=training_fixture(),
            events=chronological_events(),
            g6_codes={"R": CODES["R"], "L": CODES["L"]},
            executor=executor,
        )

        self.assertEqual(row["status"], "CANDIDATE")
        self.assertEqual(len(submitted), 1)
        self.assertEqual(tuple(row["columns"][0]), (1, 0, 0, 0, 0, 0))
        self.assertEqual(row["semantic_id"], candidate_semantic_id(row))

    def test_runtime_joins_only_the_declared_observers_and_executor(self):
        calls = []

        def training_reader():
            calls.append("training")
            return training_fixture()

        def event_reader():
            calls.append("events")
            return {"events": chronological_events(), "action_count": 12}

        def code_reader():
            calls.append("codes")
            return {"codes": {"R": CODES["R"], "L": CODES["L"]}, "action_count": 2}

        def executor(columns):
            calls.append("submit")
            return {
                "progressed": False,
                "terminal": [5, "GameState.NOT_FINISHED"],
                "target_writes": 17,
                "submit_clicks": 1,
                "action_count": 18,
            }

        row = run_candidate(
            training_reader=training_reader,
            event_reader=event_reader,
            code_reader=code_reader,
            executor=executor,
        )

        self.assertEqual(calls, ["training", "events", "codes", "submit"])
        self.assertEqual(row["action_count"], 32)


class GlyphRoleEvidence(unittest.TestCase):
    def test_unknown_role_mapping_performs_zero_submission(self):
        calls = []

        def runner():
            calls.append(1)
            return {
                "status": "UNKNOWN",
                "residual": {"reason": "missing_role_supervision"},
                "target_writes": 0,
                "submit_clicks": 0,
                "action_count": 16,
            }

        result = build_result(head="abc", runner=runner)

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "EXACT_RESIDUAL")
        self.assertEqual(result["target_writes"], 0)
        self.assertEqual(calls, [1])

    def test_failed_candidate_is_one_warranted_negative(self):
        calls = []

        def runner():
            calls.append(1)
            return candidate(progressed=False)

        result = build_result(head="abc", runner=runner)

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["verification"], [])

    def test_progress_requires_two_identical_replays(self):
        result = build_result(head="abc", runner=lambda: candidate(progressed=True))

        self.assertEqual(result["status"], "PROMOTED")
        self.assertEqual(result["classification"], "WARRANTED_POSITIVE")
        self.assertEqual(len(result["verification"]), 2)

    def test_progress_replay_action_drift_is_non_evidence(self):
        rows = [candidate(progressed=True) for _ in range(3)]
        rows[1]["action_count"] += 1
        iterator = iter(rows)

        result = build_result(head="abc", runner=lambda: next(iterator))

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(result["residual"]["reason"], "verification_identity_drift")

    def test_exact_head_and_candidate_semantics_are_sealed(self):
        result = build_result(head="abc", runner=lambda: candidate(progressed=False))
        self.assertEqual(validate_result(result, executing_head="abc"), result)

        tampered = copy.deepcopy(result)
        tampered["candidate"]["semantic_id"] = "tampered"
        with self.assertRaisesRegex(ValueError, "candidate_semantic_id"):
            validate_result(tampered, executing_head="abc")


if __name__ == "__main__":
    unittest.main()
