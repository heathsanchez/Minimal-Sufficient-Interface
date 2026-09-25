from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from arc3_public_g6_hierarchical_program_lift import (
    _compile_hierarchical_columns,
    _extract_g5_program,
    build_result,
)
from metalogic_arc3.protected_future import UnknownResidual


CODES = {
    "X": (1, 0, 1, 0, 0, 0),
    "D": (1, 1, 0, 0, 0, 0),
    "T": (1, 1, 1, 1, 1, 1),
    "S": (0, 0, 0, 1, 0, 0),
}


def training():
    return {
        "levels": [
            {"level": 3, "terminal_warrant": {"consequence": "PROGRESS"}, "examples": []},
            {"level": 4, "terminal_warrant": {"consequence": "PROGRESS"}, "examples": []},
            {
                "level": 5,
                "terminal_warrant": {"consequence": "PROGRESS"},
                "examples": [
                    {"action": {"controls": [label]}, "output": list(CODES[label])}
                    for label in "XDDDTS"
                ],
            },
        ]
    }


def roles():
    names = (
        "endpoint.depart", "plain.before", "checker.enter",
        "checker.exit", "plain.after", "endpoint.arrive",
    )
    return tuple({"role": role, "marker_rank": 5 - index} for index, role in enumerate(names))


class HierarchicalProgramLiftTests(unittest.TestCase):
    def test_extracts_exact_warranted_g5_program(self):
        program = _extract_g5_program(training())
        self.assertNotIsInstance(program, UnknownResidual)
        self.assertEqual(tuple(row["control"] for row in program), tuple("XDDDTS"))

    def test_rejects_curriculum_or_warrant_drift(self):
        changed = training()
        changed["levels"][2]["examples"][-1]["action"]["controls"] = ["T"]
        residual = _extract_g5_program(changed)
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "g5_program_census")

    def test_compiles_chronological_program_into_spatial_order(self):
        columns = _compile_hierarchical_columns(_extract_g5_program(training()), roles())
        self.assertEqual(columns, (
            CODES["S"], CODES["T"], CODES["D"],
            CODES["D"], CODES["D"], CODES["X"],
        ))

    def test_role_census_fails_closed(self):
        changed = list(roles())
        changed[0] = {**changed[0], "role": "plain.before"}
        residual = _compile_hierarchical_columns(_extract_g5_program(training()), changed)
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "g6_lifecycle_census")

    def test_replays_only_a_progressing_candidate(self):
        calls = []

        def runner():
            calls.append(1)
            return {
                "status": "CANDIDATE",
                "semantic_id": "same",
                "progressed": True,
                "terminal": [6, "GameState.NOT_FINISHED"],
                "columns": [list(CODES["D"])] * 6,
                "target_writes": 12,
                "submit_clicks": 1,
                "action_count": 25,
            }

        result = build_result(head="abc", runner=runner)
        self.assertEqual(result["classification"], "WARRANTED_POSITIVE")
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(result["verification"]), 2)

    def test_hosted_workflow_is_branch_scoped(self):
        workflow = ROOT / ".github" / "workflows" / "arc3-public-g6-hierarchical-program-lift.yml"
        text = workflow.read_text()
        self.assertIn("branches: [arc3-public-g6-hierarchical-program-lift-v1]", text)
        self.assertIn("GAME_ID: tn36-ef4dde99", text)
        self.assertIn("HIERARCHICAL_PROGRAM_LIFT_SEAL=PASS", text)


if __name__ == "__main__":
    unittest.main()
