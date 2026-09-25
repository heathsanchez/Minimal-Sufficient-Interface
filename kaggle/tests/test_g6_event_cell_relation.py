import copy
import unittest

from arc3_public_g6_event_cell_relation import (
    EVENT_STEPS,
    ROUTE,
    build_event_records,
    build_result,
    canonical_patch_trace,
    classify_replays,
    component_relation_descriptors,
    extract_cell_patch,
    event_relation_signature,
    route_positions,
    run_replay,
    validate_result,
)


def recolor(grid, mapping):
    return [[mapping[value] for value in row] for row in grid]


def translated(grid, *, top=2, left=3, fill=8):
    width = len(grid[0]) + left + 2
    result = [[fill for _ in range(width)] for _ in range(len(grid) + top + 2)]
    for row, line in enumerate(grid):
        for column, value in enumerate(line):
            result[top + row][left + column] = value
    return result


def event(step, controls, signature):
    return {
        "route_step": step,
        "controls": controls,
        "cells": [[0, 0], [0, 1], [0, 2]],
        "marker_position": [1, step],
        "marker_rank": EVENT_STEPS.index(step),
        "relation_signature": signature,
    }


def replay(signatures):
    controls = ("RR", "RR", "UU", "LL", "UU", "UL")
    return {
        "events": [
            event(step, control, signature)
            for step, control, signature in zip(EVENT_STEPS, controls, signatures)
        ],
        "route": ROUTE,
        "event_steps": list(EVENT_STEPS),
        "target_writes": 0,
        "submit_clicks": 0,
        "action_count": 12,
    }


class EventCellCanonicalization(unittest.TestCase):
    def test_extract_cell_patch_uses_declared_board_geometry(self):
        grid = [[10 * row + column for column in range(8)] for row in range(8)]

        self.assertEqual(
            extract_cell_patch(
                grid,
                board_top=2,
                board_left=2,
                cell=(1, 1),
                cell_size=2,
            ),
            ((44, 45), (54, 55)),
        )

    def test_patch_trace_is_palette_invariant(self):
        patches = (
            ((1, 1), (1, 2)),
            ((1, 3), (3, 2)),
            ((4, 4), (3, 2)),
        )
        renamed = tuple(
            tuple(tuple({1: 9, 2: 7, 3: 5, 4: 6}[value] for value in row) for row in patch)
            for patch in patches
        )

        self.assertEqual(canonical_patch_trace(patches), canonical_patch_trace(renamed))

    def test_component_relations_ignore_translation_and_palette(self):
        grid = [
            [1, 1, 2, 2, 1, 1],
            [1, 9, 2, 2, 1, 1],
            [2, 2, 1, 1, 2, 2],
            [2, 2, 1, 1, 2, 7],
        ]
        cells = ((0, 0), (0, 1), (0, 2))
        original = component_relation_descriptors(
            grid,
            board_top=0,
            board_left=0,
            board_rows=2,
            board_columns=3,
            cell_size=2,
            trace_cells=cells,
        )
        shifted = translated(recolor(grid, {1: 6, 2: 4, 9: 3, 7: 5}))
        transported = component_relation_descriptors(
            shifted,
            board_top=2,
            board_left=3,
            board_rows=2,
            board_columns=3,
            cell_size=2,
            trace_cells=cells,
        )

        self.assertEqual(original, transported)

    def test_board_relation_separates_same_control_macro(self):
        plain = event_relation_signature(
            "RR",
            (((1, 1), (1, 1)),) * 3,
            (("component", ((0, 0),), ((0, 2), (1, 0), (2, 0))),),
        )
        port = event_relation_signature(
            "RR",
            (((1, 1), (1, 1)),) * 3,
            (("component", ((0, 0), (0, 1)), ((0, 2), (1, 0), (1, 0))),),
        )

        self.assertNotEqual(plain, port)


class EventCellClassification(unittest.TestCase):
    def test_route_positions_have_thirteen_states_and_six_event_boundaries(self):
        positions = route_positions((4, 0), ROUTE)

        self.assertEqual(len(positions), 13)
        self.assertEqual(positions[0], (4, 0))
        self.assertEqual(positions[-1], (-1, 1))
        self.assertEqual(
            [(positions[step - 2], positions[step - 1], positions[step]) for step in EVENT_STEPS],
            [
                ((4, 0), (4, 1), (4, 2)),
                ((4, 2), (4, 3), (4, 4)),
                ((4, 4), (3, 4), (2, 4)),
                ((2, 4), (2, 3), (2, 2)),
                ((2, 2), (1, 2), (0, 2)),
                ((0, 2), (-1, 2), (-1, 1)),
            ],
        )

    def test_event_records_align_spatial_marker_rank_without_using_it_as_meaning(self):
        frames = []
        for phase in range(13):
            frames.append(
                [
                    [phase * 100 + 10 * row + column for column in range(7)]
                    for row in range(7)
                ]
            )
        positions = route_positions((6, 1), ROUTE)
        markers = tuple(
            zip(EVENT_STEPS, ((5, 5), (1, 9), (7, 2), (3, 3), (4, 8), (0, 4)))
        )

        rows = build_event_records(
            frames,
            positions=positions,
            marker_events=markers,
            board_top=0,
            board_left=0,
            board_rows=7,
            board_columns=7,
            cell_size=1,
        )

        self.assertEqual([row["marker_rank"] for row in rows], [4, 1, 5, 2, 3, 0])
        self.assertEqual(rows[0]["cells"], [[6, 1], [6, 2], [6, 3]])
        self.assertEqual(rows[0]["trace_patches"], [[[61]], [[162]], [[263]]])
        self.assertNotIn("marker_rank", rows[0]["signature_inputs"])

    def test_event_records_reject_noncanonical_event_steps(self):
        frames = [[[0 for _ in range(7)] for _ in range(7)] for _ in range(13)]
        markers = tuple(zip((1, 4, 6, 8, 10, 12), ((row, 0) for row in range(6))))

        with self.assertRaisesRegex(ValueError, "marker_event_steps"):
            build_event_records(
                frames,
                positions=route_positions((4, 0), ROUTE),
                marker_events=markers,
                board_top=0,
                board_left=0,
                board_rows=7,
                board_columns=7,
                cell_size=1,
            )

    def test_repeated_rr_relation_is_a_response_separator(self):
        left = replay(("rr-a", "rr-b", "uu", "ll", "uu", "ul"))
        right = copy.deepcopy(left)

        result = classify_replays((left, right))

        self.assertEqual(result["status"], "SEPARATED")
        self.assertEqual(result["classification"], "RESPONSE_SEPARATOR_ONLY")
        self.assertEqual(result["separated_control_pairs"], ["RR"])

    def test_collapsed_repeated_pairs_are_warranted_negative(self):
        first = replay(("rr", "rr", "uu", "ll", "uu", "ul"))
        second = copy.deepcopy(first)

        result = classify_replays((first, second))

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["classification"], "WARRANTED_NEGATIVE")
        self.assertEqual(result["separated_control_pairs"], [])

    def test_replay_drift_is_non_evidence(self):
        first = replay(("rr", "rr", "uu", "ll", "uu", "ul"))
        second = copy.deepcopy(first)
        second["events"][1]["relation_signature"] = "drift"

        result = classify_replays((first, second))

        self.assertEqual(result["status"], "RESIDUAL")
        self.assertEqual(result["classification"], "NON_EVIDENCE")
        self.assertEqual(result["residual"]["reason"], "independent_replay_drift")


class EventCellEvidenceSeal(unittest.TestCase):
    def test_build_result_requires_two_independent_replays(self):
        template = replay(("rr-a", "rr-b", "uu", "ll", "uu", "ul"))

        result = build_result(
            head="abc123",
            runner=lambda enter_g6=None: copy.deepcopy(template),
        )

        self.assertEqual(result["status"], "SEPARATED")
        self.assertEqual(result["classification"], "RESPONSE_SEPARATOR_ONLY")
        self.assertEqual(result["independent_replay_count"], 2)
        self.assertEqual(result["target_writes"], 0)

    def test_public_replay_collects_exact_six_marker_events(self):
        class Frame:
            def __init__(self, grid):
                self.frame = grid
                self.levels_completed = 5
                self.state = "GameState.NOT_FINISHED"

        class Environment:
            def __init__(self):
                self.step = 0
                self.grid = [[0 for _ in range(35)] for _ in range(35)]

        environment = Environment()

        def enter_g6():
            return environment, Frame(copy.deepcopy(environment.grid))

        def clicker(env, _coordinate):
            env.step += 1
            if env.step in EVENT_STEPS:
                env.grid[0][env.step // 2] = 1
            return Frame(copy.deepcopy(env.grid))

        controls = [((index, 33), label) for index, label in enumerate("UDLR")]
        mover = {(2 + 6 * 4, 2 + 1 * 4)}

        result = run_replay(
            enter_g6=enter_g6,
            clicker=clicker,
            find_board=lambda _grid: (2, 2),
            find_translation=lambda _grid, _top, _left: (mover, {(2, 2)}, -20, 4),
            selector_controls=lambda _grid: controls,
        )

        self.assertEqual(result["action_count"], 12)
        self.assertEqual([row["route_step"] for row in result["events"]], list(EVENT_STEPS))
        self.assertEqual([row["marker_rank"] for row in result["events"]], list(range(6)))
        self.assertEqual(result["route_positions"][0], [6, 1])

    def test_zero_write_result_seals(self):
        rows = (
            replay(("rr", "rr", "uu", "ll", "uu", "ul")),
            replay(("rr", "rr", "uu", "ll", "uu", "ul")),
        )
        result = {
            "schema": "arc3.g6-event-cell-relation@1",
            "head": "abc123",
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "route": ROUTE,
            "event_steps": list(EVENT_STEPS),
            "replays": list(rows),
            "independent_replay_count": 2,
            "action_budget_per_replay": 12,
            "separated_control_pairs": [],
            "target_writes": 0,
            "submit_clicks": 0,
            "model_calls": 0,
            "source_inspection": False,
        }

        self.assertEqual(validate_result(result, executing_head="abc123"), result)

    def test_target_write_cannot_seal(self):
        rows = (
            replay(("rr", "rr", "uu", "ll", "uu", "ul")),
            replay(("rr", "rr", "uu", "ll", "uu", "ul")),
        )
        result = {
            "schema": "arc3.g6-event-cell-relation@1",
            "head": "abc123",
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "route": ROUTE,
            "event_steps": list(EVENT_STEPS),
            "replays": list(rows),
            "independent_replay_count": 2,
            "action_budget_per_replay": 12,
            "separated_control_pairs": [],
            "target_writes": 1,
            "submit_clicks": 0,
            "model_calls": 0,
            "source_inspection": False,
        }

        with self.assertRaisesRegex(ValueError, "scientific_boundary"):
            validate_result(result, executing_head="abc123")

    def test_marker_ranks_must_be_spatial_permutation(self):
        rows = [
            replay(("rr", "rr", "uu", "ll", "uu", "ul")),
            replay(("rr", "rr", "uu", "ll", "uu", "ul")),
        ]
        for row in rows:
            row["events"][1]["marker_rank"] = 0

        result = {
            "schema": "arc3.g6-event-cell-relation@1",
            "head": "abc123",
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "route": ROUTE,
            "event_steps": list(EVENT_STEPS),
            "replays": rows,
            "independent_replay_count": 2,
            "action_budget_per_replay": 12,
            "separated_control_pairs": [],
            "target_writes": 0,
            "submit_clicks": 0,
            "model_calls": 0,
            "source_inspection": False,
        }

        with self.assertRaisesRegex(ValueError, "classification_mismatch"):
            validate_result(result, executing_head="abc123")


if __name__ == "__main__":
    unittest.main()
