import unittest

from metalogic_arc3.future_arc import (
    ArcTraceBuilder,
    align_marker_events,
    compress_observable_trace,
    observable_change_mask,
    project_route_after_waypoint,
    project_goal_phase_transitions,
    macro_effect,
    relational_signature,
)
from metalogic_arc3.protected_future import UnknownResidual, refine_partition


def object_frame(top=1, left=1, *, background=0, foreground=7):
    grid = [[background for _ in range(10)] for _ in range(8)]
    for dr, dc in ((0, 0), (1, 0), (1, 1), (2, 1)):
        grid[top + dr][left + dc] = foreground
    return grid


class ArrayLayer:
    def __init__(self, grid):
        self._grid = grid

    def tolist(self):
        return self._grid


class ArrayBackedFrame:
    def __init__(self, grid):
        self.frame = [ArrayLayer([[9]]), ArrayLayer(grid)]


class ArcFutureAdapterContracts(unittest.TestCase):
    def test_translation_and_color_relabel_preserve_effect_identity(self):
        left = macro_effect(
            (
                object_frame(1, 1, foreground=7),
                object_frame(1, 2, foreground=7),
            ),
            ("R",),
        )
        right = macro_effect(
            (
                object_frame(4, 6, background=4, foreground=2),
                object_frame(4, 7, background=4, foreground=2),
            ),
            ("R",),
        )

        self.assertEqual(left.effect.effect_id, right.effect.effect_id)

    def test_unique_waypoint_selects_route_suffix(self):
        actions = tuple("RRRRUULLUUUL")
        positions = tuple(range(13))

        projection = project_route_after_waypoint(
            actions,
            positions,
            waypoints={6},
            target_arity=6,
        )

        self.assertEqual(projection, tuple("LLUUUL"))

    def test_waypoint_projection_fails_closed_when_not_unique_on_route(self):
        result = project_route_after_waypoint(
            tuple("RRRR"),
            tuple(range(5)),
            waypoints={1, 3},
            target_arity=2,
        )

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.missing_interface, "target.projection@1")

    def test_observable_change_mask_preserves_only_coordinate_change(self):
        before = ("on", "on", "off", "off")
        after = ("off", "on", "off", "on")

        self.assertEqual(observable_change_mask(before, after), (1, 0, 0, 1))

    def test_observable_change_mask_rejects_mismatched_coordinates(self):
        result = observable_change_mask((1, 0), (1, 0, 1))

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.missing_interface, "observer.correspondence@1")

    def test_marker_event_positions_supply_spatial_column_order(self):
        chronological = (
            ((1, 61), "R"),
            ((1, 60), "R"),
            ((1, 59), "U"),
            ((1, 58), "L"),
            ((1, 57), "U"),
            ((1, 56), "L"),
        )

        projection = align_marker_events(chronological, target_arity=6)

        self.assertEqual(projection, ("L", "U", "L", "U", "R", "R"))

    def test_marker_event_alignment_is_translation_invariant(self):
        original = (((2, 8), "b"), ((2, 7), "a"))
        translated = (((12, 28), "b"), ((12, 27), "a"))

        self.assertEqual(
            align_marker_events(original, target_arity=2),
            align_marker_events(translated, target_arity=2),
        )

    def test_marker_event_alignment_fails_closed_on_duplicate_position(self):
        result = align_marker_events((((1, 1), "a"), ((1, 1), "b")), target_arity=2)

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.missing_interface, "target.projection@1")

    def test_observable_trace_quotients_idempotent_repetitions(self):
        down = (1, 1, 0, 0, 0, 0)
        right = (0, 1, 0, 0, 0, 0)
        up = (1, 0, 0, 0, 0, 1)
        left = (1, 0, 0, 0, 0, 0)

        projection = compress_observable_trace(
            down,
            (right,) * 4 + (up,) * 2 + (left,) * 2 + (up,) * 3 + (left,),
            target_arity=6,
        )

        self.assertEqual(projection, (down, right, up, left, up, left))

    def test_observable_trace_is_invariant_to_stutter_extension(self):
        initial = ("down",)
        compact = (("right",), ("up",), ("left",))
        stuttered = (("right",), ("right",), ("up",), ("left",), ("left",))

        self.assertEqual(
            compress_observable_trace(initial, compact, target_arity=4),
            compress_observable_trace(initial, stuttered, target_arity=4),
        )

    def test_observable_trace_fails_closed_on_wrong_arity(self):
        result = compress_observable_trace(0, (1, 1, 2), target_arity=5)

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.missing_interface, "target.projection@1")

    def test_goal_phase_projection_selects_ingress_controls_without_index_pairing(self):
        actions = ("R", "R", "R", "R", "U", "U", "L", "L", "U", "U", "U", "L")
        supports = (
            frozenset(("object", "goal-phase")),
            frozenset(("other-phase",)),
            frozenset(("goal-phase",)),
            frozenset(("other-phase",)),
            frozenset(("goal-phase",)),
            frozenset(("other-phase",)),
            frozenset(("goal-phase", "marker")),
            frozenset(("other-phase",)),
            frozenset(("goal-phase",)),
            frozenset(("other-phase",)),
            frozenset(("goal-phase",)),
            frozenset(("other-phase",)),
            frozenset(("goal-phase", "marker")),
        )

        projection = project_goal_phase_transitions(actions, supports, target_arity=6)

        self.assertEqual(projection, ("R", "R", "U", "L", "U", "L"))

    def test_goal_phase_projection_is_token_relabel_invariant(self):
        actions = ("east", "north", "west", "north")
        original = (
            frozenset((0, 2)),
            frozenset((1,)),
            frozenset((2,)),
            frozenset((1,)),
            frozenset((2, 3)),
        )
        relabeled = tuple(frozenset({9 - value for value in support}) for support in original)

        self.assertEqual(
            project_goal_phase_transitions(actions, original, target_arity=2),
            project_goal_phase_transitions(actions, relabeled, target_arity=2),
        )

    def test_goal_phase_projection_fails_closed_on_wrong_arity(self):
        result = project_goal_phase_transitions(
            ("R", "R"),
            (frozenset((0, 1)), frozenset((2,)), frozenset((1,))),
            target_arity=2,
        )

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.missing_interface, "target.projection@1")

    def test_array_backed_latest_frame_normalizes(self):
        trace = ArcTraceBuilder(actions=("U", "D", "L", "R"), max_depth=4, max_states=16)

        state = trace.observe(ArrayBackedFrame(object_frame()), level=5, terminal=False)

        self.assertEqual(state.signature, relational_signature(object_frame()))

    def test_translation_and_color_relabel_preserve_relational_signature(self):
        original = object_frame(1, 1, background=0, foreground=7)
        transformed = object_frame(4, 6, background=4, foreground=2)

        self.assertEqual(
            relational_signature(original),
            relational_signature(transformed),
        )

    def test_incompatible_repeated_response_is_typed_unknown(self):
        trace = ArcTraceBuilder(actions=("go",), max_depth=2, max_states=4)
        source = trace.observe(object_frame(), level=1, terminal=False, history=("root",))
        first = trace.observe(object_frame(2, 2), level=1, terminal=False, history=("first",))
        second = trace.observe(object_frame(3, 5), level=1, terminal=False, history=("second",))
        trace.record(source, "go", first, effect="move")
        trace.record(source, "go", second, effect="move")

        result = trace.machine()

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.missing_interface, "transition.nondeterministic@1")

    def test_required_control_splits_pixel_equivalent_histories(self):
        trace = ArcTraceBuilder(actions=("press",), max_depth=1, max_states=2)
        left = trace.observe(object_frame(), level=1, terminal=False, history=("left",))
        right = trace.observe(object_frame(), level=1, terminal=False, history=("right",))
        self.assertEqual(left.signature, right.signature)
        trace.record(left, "press", left, effect="select", required_control="L")
        trace.record(right, "press", right, effect="select", required_control="R")

        result = trace.machine()
        quotient = refine_partition(result)

        self.assertNotEqual(quotient.class_of(left.state_id), quotient.class_of(right.state_id))


if __name__ == "__main__":
    unittest.main()
