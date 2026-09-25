from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from arc3_public_g3_g5_local_role_supervision import (
    _enter_visible_frame,
    _source_port_mode,
    build_result,
    canonical_local_relation,
    compile_supervised_candidate,
    fit_relation_codebook,
    validate_result,
)
from metalogic_arc3.protected_future import UnknownResidual


EMPTY = ((4, 4), (4, 4))
MARK = ((4, 5), (4, 4))


def relation(index: int) -> str:
    patch = ((4, 5 if index % 2 else 4), (5 if index >= 2 else 4, 4))
    return canonical_local_relation(
        (EMPTY, patch),
        trace_cells=((8 + index, 20), (9 + index, 20)),
        component_relations=(("touch", index),),
    )


def training_slots(*, conflict: bool = False):
    rows = []
    for level in (3, 4, 5):
        for slot_index in range(6):
            output_index = slot_index
            if conflict and level == 5 and slot_index == 0:
                output_index = 1
            rows.append(
                {
                    "level": level,
                    "slot_index": slot_index,
                    "terminal_consequence": "PROGRESS",
                    "relation_id": relation(slot_index),
                    "output": [int(bit == output_index) for bit in range(6)],
                }
            )
    return rows


class LocalRoleSupervisionTests(unittest.TestCase):
    def test_source_port_mode_is_palette_invariant_and_separates_selection(self):
        broadcast = [
            [0, 0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1, 1],
        ]
        selected = [
            [0, 0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1, 1],
        ]
        rows = (((0, 0), (1, 0), (2, 0)), ((0, 1), (1, 1), (2, 1)))
        selected[0][1] = 9
        selected[1][1] = 9
        palette = {0: 7, 1: 4, 9: 3}
        complement = [[palette[value] for value in row] for row in selected]
        self.assertEqual(_source_port_mode(broadcast, rows=rows), ((0, 0, 0),))
        self.assertEqual(_source_port_mode(selected, rows=rows), ((0, 1, 0),))
        self.assertEqual(
            _source_port_mode(selected, rows=rows),
            _source_port_mode(complement, rows=rows),
        )

    def test_entry_uses_public_observation_not_helper_trace_payload(self):
        visible = [[1, 2], [3, 4]]

        class Environment:
            observation_space = visible

        env, frame = _enter_visible_frame(
            lambda: (Environment(), [{"phase": "qualified-prefix"}])
        )
        self.assertIs(frame, visible)
        self.assertIs(frame, env.observation_space)

    def test_canonical_local_relation_is_palette_and_translation_invariant(self):
        first = canonical_local_relation(
            (EMPTY, MARK),
            trace_cells=((5, 8), (6, 8)),
            component_relations=(("touch", 1),),
        )
        complement = canonical_local_relation(
            (((11, 11), (11, 11)), ((11, 5), (11, 11))),
            trace_cells=((15, 28), (16, 28)),
            component_relations=(("touch", 1),),
        )
        self.assertEqual(first, complement)

    def test_fit_relation_codebook_requires_exact_warranted_18_slot_census(self):
        residual = fit_relation_codebook(training_slots()[:-1])
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "warranted_slot_census")

    def test_fit_relation_codebook_accepts_functional_supervision(self):
        codebook = fit_relation_codebook(training_slots())
        self.assertNotIsInstance(codebook, UnknownResidual)
        self.assertEqual(len(codebook), 6)
        self.assertEqual(codebook[relation(4)]["output"], [0, 0, 0, 0, 1, 0])
        self.assertEqual(codebook[relation(4)]["source_levels"], [3, 4, 5])

    def test_fit_relation_codebook_preserves_output_collision(self):
        residual = fit_relation_codebook(training_slots(conflict=True))
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "nonfunctional_local_relation")
        self.assertTrue(any("G3:slot0" in item for item in residual.evidence))
        self.assertTrue(any("G5:slot0" in item for item in residual.evidence))

    def test_fit_relation_codebook_rejects_missing_relation_identity(self):
        slots = training_slots()
        slots[0]["relation_id"] = None
        residual = fit_relation_codebook(slots)
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "missing_local_relation")

    def test_compile_candidate_fails_closed_on_uncovered_g6_relation(self):
        calls = []
        candidate = compile_supervised_candidate(
            training_slots(),
            [relation(index) for index in range(5)] + ["unseen"],
            executor=lambda columns: calls.append(columns),
        )
        self.assertEqual(candidate["status"], "UNKNOWN")
        self.assertEqual(candidate["residual"]["reason"], "uncovered_g6_relation")
        self.assertEqual(candidate["target_writes"], 0)
        self.assertEqual(candidate["submit_clicks"], 0)
        self.assertEqual(calls, [])

    def test_compile_candidate_executes_once_only_after_total_functional_join(self):
        calls = []

        def execute(columns):
            calls.append(columns)
            return {
                "progressed": False,
                "terminal": [5, "GameState.NOT_FINISHED"],
                "target_writes": 6,
                "submit_clicks": 1,
                "action_count": 7,
            }

        candidate = compile_supervised_candidate(
            training_slots(),
            [relation(index) for index in range(6)],
            executor=execute,
        )
        self.assertEqual(candidate["status"], "CANDIDATE")
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            tuple(tuple(int(bit == index) for bit in range(6)) for index in range(6)),
        )
        self.assertEqual(candidate["target_writes"], 6)
        self.assertEqual(candidate["submit_clicks"], 1)

    def test_build_result_stops_after_exact_residual(self):
        calls = []

        def runner():
            calls.append(1)
            return {
                "status": "UNKNOWN",
                "residual": {
                    "missing_interface": "event.history-conditioned-local-relation@1",
                    "reason": "nonfunctional_local_relation",
                    "evidence": ["collision"],
                },
                "target_writes": 0,
                "submit_clicks": 0,
                "action_count": 72,
            }

        result = build_result(head="abc", runner=runner)
        self.assertEqual(result["classification"], "EXACT_RESIDUAL")
        self.assertEqual(calls, [1])
        self.assertEqual(result["target_writes"], 0)

    def test_build_result_replays_only_a_progressing_candidate_twice(self):
        calls = []

        def runner():
            calls.append(1)
            return {
                "status": "CANDIDATE",
                "semantic_id": "same",
                "progressed": True,
                "terminal": [6, "GameState.NOT_FINISHED"],
                "columns": [[1, 0, 0, 0, 0, 0]] * 6,
                "target_writes": 6,
                "submit_clicks": 1,
                "action_count": 91,
            }

        result = build_result(head="abc", runner=runner)
        self.assertEqual(result["classification"], "WARRANTED_POSITIVE")
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(result["verification"]), 2)

    def test_progress_replay_action_drift_is_non_evidence(self):
        counts = iter((91, 92, 91))

        def runner():
            return {
                "status": "CANDIDATE",
                "semantic_id": "same",
                "progressed": True,
                "terminal": [6, "GameState.NOT_FINISHED"],
                "columns": [[1, 0, 0, 0, 0, 0]] * 6,
                "target_writes": 6,
                "submit_clicks": 1,
                "action_count": next(counts),
            }

        result = build_result(head="abc", runner=runner)
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(result["residual"]["reason"], "verification_identity_drift")

    def test_build_result_does_not_replay_nonprogress(self):
        calls = []

        def runner():
            calls.append(1)
            return {
                "status": "CANDIDATE",
                "semantic_id": "same",
                "progressed": False,
                "terminal": [5, "GameState.NOT_FINISHED"],
                "columns": [[1, 0, 0, 0, 0, 0]] * 6,
                "target_writes": 6,
                "submit_clicks": 1,
                "action_count": 91,
            }

        result = build_result(head="abc", runner=runner)
        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")
        self.assertEqual(calls, [1])

    def test_validate_result_rejects_stale_head_and_action_budget_drift(self):
        residual = {
            "schema": "arc3.g3-g6-source-port-mode@1",
            "head": "abc",
            "status": "RESIDUAL",
            "classification": "EXACT_RESIDUAL",
            "candidate": {
                "status": "UNKNOWN",
                "target_writes": 0,
                "submit_clicks": 0,
                "action_count": 72,
            },
            "verification": [],
            "target_writes": 0,
            "model_calls": 0,
            "source_inspection": False,
            "action_budget_per_candidate": 180,
            "residual": {"reason": "collision"},
        }
        with self.assertRaisesRegex(ValueError, "stale_evidence_head"):
            validate_result(residual, executing_head="different")
        residual["head"] = "different"
        residual["action_budget_per_candidate"] = 181
        with self.assertRaisesRegex(ValueError, "scientific_boundary"):
            validate_result(residual, executing_head="different")

    def test_validate_result_rejects_candidate_without_one_submit(self):
        with self.assertRaisesRegex(ValueError, "candidate_boundary"):
            build_result(
                head="abc",
                runner=lambda: {
                    "status": "CANDIDATE",
                    "semantic_id": "same",
                    "progressed": False,
                    "terminal": [5, "GameState.NOT_FINISHED"],
                    "columns": [[1, 0, 0, 0, 0, 0]] * 6,
                    "target_writes": 6,
                    "submit_clicks": 0,
                    "action_count": 90,
                },
            )

    def test_hosted_workflow_seals_exact_public_gate(self):
        workflow = ROOT / ".github" / "workflows" / "arc3-public-g3-g5-local-role-supervision.yml"
        text = workflow.read_text()
        self.assertIn("branches: [arc3-public-g3-g6-source-port-mode-v1]", text)
        self.assertIn("GAME_ID: tn36-ef4dde99", text)
        self.assertIn("python -m unittest discover -s kaggle/tests -v", text)
        self.assertIn("ARC3_PUBLIC_G3_G6_SOURCE_PORT_MODE_SEAL=PASS", text)
        self.assertIn("assert result[\"classification\"] != \"NON_EVIDENCE\"", text)


if __name__ == "__main__":
    unittest.main()
