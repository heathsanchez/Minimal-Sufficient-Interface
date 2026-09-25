from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from arc3_public_g6_conditional_motion_composition import (
    COMPOSITIONS,
    _compile_columns,
    _fit_conditional_motion,
    build_result,
)
from metalogic_arc3.protected_future import UnknownResidual


CARDINAL = {
    (-1, 0): (1, 0, 0, 0, 0, 1),
    (0, -1): (0, 1, 0, 0, 0, 1),
    (0, 1): (0, 1, 0, 0, 0, 0),
    (1, 0): (1, 1, 0, 0, 0, 0),
}


def supervised_slots():
    motions = [(-1, 0), (0, 1), (0, 1), (0, 1), (-1, 0), (0, 1)]
    motions += [(0, 0), (0, -1), (1, 0), (1, 0), (1, 0), (1, 0)]
    motions += [(0, 0), (1, 0), (1, 0), (1, 0), (0, 0), (0, 0)]
    stationary = iter(((1, 0, 0, 1, 0, 0), (1, 0, 1, 0, 0, 0),
                       (1, 1, 1, 1, 1, 1), (0, 0, 0, 1, 0, 0)))
    rows = []
    for index, motion in enumerate(motions):
        rows.append({
            "level": 3 + index // 6,
            "slot_index": index % 6,
            "terminal_consequence": "PROGRESS",
            "features": {"primitive_motion": motion},
            "output": list(CARDINAL[motion] if motion != (0, 0) else next(stationary)),
        })
    return rows


def g6_events():
    motions = [(-1, -1), (-1, 0), (0, -1), (-1, 0), (0, 1), (0, 1)]
    return [{"features": {"primitive_motion": motion}} for motion in motions]


class ConditionalMotionCompositionTests(unittest.TestCase):
    def test_nonstationary_motion_is_functional_while_stationary_may_vary(self):
        fitted = _fit_conditional_motion(supervised_slots(), g6_events())
        self.assertNotIsInstance(fitted, UnknownResidual)
        self.assertEqual(fitted["cardinal_codebook"], CARDINAL)
        self.assertEqual(fitted["uncovered"], ((-1, -1),))
        self.assertEqual(fitted["directly_covered"], 5)

    def test_conflicting_nonstationary_motion_fails_closed(self):
        slots = supervised_slots()
        slots[5]["output"] = [1, 1, 1, 1, 1, 1]
        residual = _fit_conditional_motion(slots, g6_events())
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "nonfunctional_nonstationary_motion")

    def test_only_one_diagonal_residual_is_admitted(self):
        events = g6_events()
        events[-1]["features"]["primitive_motion"] = (1, 1)
        residual = _fit_conditional_motion(supervised_slots(), events)
        self.assertIsInstance(residual, UnknownResidual)
        self.assertEqual(residual.reason, "g6_motion_residual_census")

    def test_diagonal_compositions_leave_five_columns_fixed(self):
        fitted = _fit_conditional_motion(supervised_slots(), g6_events())
        expected = {
            "or": (1, 1, 0, 0, 0, 1),
            "and": (0, 0, 0, 0, 0, 1),
            "xor": (1, 1, 0, 0, 0, 0),
        }
        for name in COMPOSITIONS:
            columns = _compile_columns(fitted, name)
            self.assertEqual(columns[0], expected[name])
            self.assertEqual(columns[1:], (
                CARDINAL[(-1, 0)], CARDINAL[(0, -1)], CARDINAL[(-1, 0)],
                CARDINAL[(0, 1)], CARDINAL[(0, 1)],
            ))

    def test_gate_preserves_failures_and_replays_only_progress(self):
        attempts = []

        def runner(name):
            attempts.append(name)
            return {
                "status": "CANDIDATE",
                "semantic_id": name,
                "composition": name,
                "columns": [[1, 0, 0, 0, 0, 0]] * 6,
                "progressed": name == "and",
                "terminal": [6 if name == "and" else 5, "GameState.NOT_FINISHED"],
                "target_writes": 6,
                "submit_clicks": 1,
                "action_count": 90,
            }

        result = build_result(head="abc", runner=runner)
        self.assertEqual(result["classification"], "WARRANTED_POSITIVE")
        self.assertEqual(attempts, ["or", "and", "and", "and"])
        self.assertEqual([row["composition"] for row in result["attempts"]], ["or", "and"])
        self.assertEqual(len(result["verification"]), 2)

    def test_gate_classifies_exhausted_family_as_warranted_negative(self):
        result = build_result(
            head="abc",
            runner=lambda name: {
                "status": "CANDIDATE",
                "semantic_id": name,
                "composition": name,
                "columns": [[0, 0, 0, 0, 0, 0]] * 6,
                "progressed": False,
                "terminal": [5, "GameState.NOT_FINISHED"],
                "target_writes": 0,
                "submit_clicks": 1,
                "action_count": 90,
            },
        )
        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")
        self.assertEqual(len(result["attempts"]), 3)
        self.assertEqual(result["verification"], [])

    def test_hosted_workflow_is_branch_scoped(self):
        workflow = ROOT / ".github" / "workflows" / "arc3-public-g6-conditional-motion-composition.yml"
        text = workflow.read_text()
        self.assertIn("branches: [arc3-public-g6-conditional-motion-composition-v1]", text)
        self.assertIn("GAME_ID: tn36-ef4dde99", text)
        self.assertIn("CONDITIONAL_MOTION_COMPOSITION_SEAL=PASS", text)


if __name__ == "__main__":
    unittest.main()
