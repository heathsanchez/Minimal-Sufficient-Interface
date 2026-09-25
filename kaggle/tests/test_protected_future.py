import unittest
from dataclasses import dataclass
from itertools import product

from metalogic_arc3.protected_future import (
    ExplorationBoundary,
    FiniteMachine,
    Transition,
    canonical_digest,
    check_congruence,
    compile_capability,
    refine_partition,
    shortest_separator,
)


def machine(
    states,
    actions,
    table,
    observations,
    *,
    accepting=(),
    controls=None,
    transition_observations=None,
    max_depth=8,
):
    controls = controls or {}
    transition_observations = transition_observations or {}
    transitions = tuple(
        Transition(
            source,
            action,
            table[(source, action)],
            transition_observations.get(
                (source, action), observations[table[(source, action)]]
            ),
            "terminal" if table[(source, action)] in accepting else "move",
            controls.get((source, action)),
        )
        for source in states
        for action in actions
        if (source, action) in table
    )
    return FiniteMachine.build(
        states=states,
        actions=actions,
        transitions=transitions,
        observations=observations,
        accepting=accepting,
        boundary=ExplorationBoundary(tuple(actions), max_depth, len(states)),
    )


def binary_counter_machine():
    states = ("dead0", "dead1", "live0", "live1")
    return machine(
        states,
        ("tick",),
        {
            ("dead0", "tick"): "dead0",
            ("dead1", "tick"): "dead1",
            ("live0", "tick"): "dead0",
            ("live1", "tick"): "live1",
        },
        {"dead0": "dead", "dead1": "dead", "live0": "live", "live1": "live"},
    )


def control_counterexample_machine():
    states = ("left", "right")
    return machine(
        states,
        ("press",),
        {("left", "press"): "left", ("right", "press"): "right"},
        {"left": "same", "right": "same"},
        controls={("left", "press"): "L", ("right", "press"): "R"},
    )


def partial_machine():
    return machine(
        ("s0", "s1"),
        ("a",),
        {("s0", "a"): "s1"},
        {"s0": 0, "s1": 0},
    )


def cyclic_success_machine():
    states = ("start", "ready", "win")
    actions = ("right", "submit")
    return machine(
        states,
        actions,
        {
            ("start", "right"): "ready",
            ("start", "submit"): "start",
            ("ready", "right"): "ready",
            ("ready", "submit"): "win",
            ("win", "right"): "win",
            ("win", "submit"): "win",
        },
        {"start": "open", "ready": "open", "win": "won"},
        accepting=("win",),
    )


def unreachable_machine():
    states = ("start", "win")
    return machine(
        states,
        ("wait",),
        {("start", "wait"): "start", ("win", "wait"): "win"},
        {"start": "open", "win": "won"},
        accepting=("win",),
    )


class ProtectedFutureObjects(unittest.TestCase):
    def test_nested_dataclass_type_identity_is_preserved(self):
        @dataclass(frozen=True)
        class Foo:
            value: int

        @dataclass(frozen=True)
        class Bar:
            value: int

        @dataclass(frozen=True)
        class Envelope:
            payload: object

        self.assertNotEqual(
            canonical_digest(Envelope(Foo(1))),
            canonical_digest(Envelope(Bar(1))),
        )

    def test_transition_insertion_order_is_identity_neutral(self):
        transitions = (
            Transition("s0", "a", "s1", "open", "move"),
            Transition("s1", "a", "s1", "win", "terminal"),
        )
        left = FiniteMachine.build(
            states=("s1", "s0"),
            actions=("a",),
            transitions=transitions,
            observations={"s0": "open", "s1": "win"},
            accepting={"s1"},
            boundary=ExplorationBoundary(("a",), 2, 2),
        )
        right = FiniteMachine.build(
            states=("s0", "s1"),
            actions=("a",),
            transitions=tuple(reversed(transitions)),
            observations={"s1": "win", "s0": "open"},
            accepting={"s1"},
            boundary=ExplorationBoundary(("a",), 2, 2),
        )
        self.assertEqual(left.content_id, right.content_id)

    def test_conflicting_duplicate_transition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "nondeterministic_transition"):
            FiniteMachine.build(
                states=("s0", "s1", "s2"),
                actions=("a",),
                transitions=(
                    Transition("s0", "a", "s1", 0, "move"),
                    Transition("s0", "a", "s2", 0, "move"),
                ),
                observations={"s0": 0, "s1": 0, "s2": 0},
                accepting=set(),
                boundary=ExplorationBoundary(("a",), 1, 3),
            )


class ProtectedFutureRefinement(unittest.TestCase):
    def test_transition_observation_is_future_semantics(self):
        current = machine(
            ("left", "right"),
            ("press",),
            {("left", "press"): "left", ("right", "press"): "right"},
            {"left": "same", "right": "same"},
            transition_observations={
                ("left", "press"): "flash-left",
                ("right", "press"): "flash-right",
            },
        )

        quotient = refine_partition(current)

        self.assertNotEqual(quotient.class_of("left"), quotient.class_of("right"))
        self.assertEqual(shortest_separator(current, "left", "right"), ("press",))
        self.assertFalse(check_congruence(current, (("left", "right"),)))

    def test_separator_and_refinement_respect_depth_boundary(self):
        current = machine(
            ("l0", "l1", "win", "r0", "r1", "dead"),
            ("tick",),
            {
                ("l0", "tick"): "l1",
                ("l1", "tick"): "win",
                ("win", "tick"): "win",
                ("r0", "tick"): "r1",
                ("r1", "tick"): "dead",
                ("dead", "tick"): "dead",
            },
            {
                "l0": "open",
                "l1": "open",
                "win": "won",
                "r0": "open",
                "r1": "open",
                "dead": "open",
            },
            accepting=("win",),
            max_depth=1,
        )

        self.assertIsNone(shortest_separator(current, "l0", "r0"))
        quotient = refine_partition(current)
        self.assertEqual(quotient.residual.missing_interface, "exploration.depth-bound@1")

    def test_refinement_finds_coarsest_future_classes_and_shortest_witness(self):
        quotient = refine_partition(binary_counter_machine())

        self.assertEqual(
            quotient.classes,
            (("dead0", "dead1"), ("live0",), ("live1",)),
        )
        self.assertEqual(
            shortest_separator(binary_counter_machine(), "live0", "live1"),
            ("tick",),
        )
        self.assertTrue(quotient.congruent)

    def test_required_control_prevents_output_only_merge(self):
        quotient = refine_partition(control_counterexample_machine())

        self.assertNotEqual(quotient.class_of("left"), quotient.class_of("right"))

    def test_partial_machine_returns_incomplete_residual(self):
        result = refine_partition(partial_machine())

        self.assertEqual(result.residual.missing_interface, "exploration.incomplete@1")

    def test_three_state_two_action_census_matches_full_transition_monoid(self):
        states = (0, 1, 2)
        actions = ("a", "b")
        nonconstant_observations = tuple(
            bits for bits in product((0, 1), repeat=3) if len(set(bits)) == 2
        )
        machines_checked = 0
        pairs_checked = 0
        maximum_separator_depth = 0

        for targets in product(states, repeat=6):
            table = {
                (state, action): targets[2 * state + action_index]
                for state in states
                for action_index, action in enumerate(actions)
            }
            generators = tuple(
                tuple(table[(state, action)] for state in states) for action in actions
            )
            monoid = {(0, 1, 2)}
            frontier = [(0, 1, 2)]
            while frontier:
                current = frontier.pop()
                for generator in generators:
                    composed = tuple(generator[current[state]] for state in states)
                    if composed not in monoid:
                        monoid.add(composed)
                        frontier.append(composed)

            for bits in nonconstant_observations:
                current_machine = machine(
                    states,
                    actions,
                    table,
                    dict(enumerate(bits)),
                )
                machines_checked += 1
                for left in states:
                    for right in range(left + 1, len(states)):
                        expected_equivalent = all(
                            bits[context[left]] == bits[context[right]]
                            for context in monoid
                        )
                        separator = shortest_separator(current_machine, left, right)
                        self.assertEqual(expected_equivalent, separator is None)
                        if separator is not None:
                            actual_left, actual_right = left, right
                            for action in separator:
                                actual_left = table[(actual_left, action)]
                                actual_right = table[(actual_right, action)]
                            self.assertNotEqual(bits[actual_left], bits[actual_right])
                            maximum_separator_depth = max(
                                maximum_separator_depth,
                                len(separator),
                            )
                        pairs_checked += 1

        self.assertEqual(machines_checked, 4374)
        self.assertEqual(pairs_checked, 13122)
        self.assertGreater(maximum_separator_depth, 0)
        print(
            "PROTECTED_FUTURE_CENSUS "
            f"machines_checked={machines_checked} "
            f"pairs_checked={pairs_checked} "
            f"max_separator_depth={maximum_separator_depth}"
        )


class ProtectedFutureCompilation(unittest.TestCase):
    def test_shortest_program_terminates_on_cycles(self):
        capability = compile_capability(
            cyclic_success_machine(),
            "start",
            ("obs@1", "control@1"),
        )

        self.assertEqual(capability.program, ("right", "submit"))

    def test_compiled_program_retains_required_physical_controls(self):
        current = cyclic_success_machine()
        controlled = machine(
            current.states,
            current.actions,
            {
                (transition.source, transition.action): transition.target
                for transition in current.transitions
            },
            dict(current.observations),
            accepting=current.accepting,
            controls={
                (transition.source, transition.action): f"button:{transition.action}"
                for transition in current.transitions
            },
        )

        capability = compile_capability(controlled, "start", ("control@1",))

        self.assertEqual(
            capability.control_program,
            ("button:right", "button:submit"),
        )

    def test_unreachable_terminal_is_unknown(self):
        result = compile_capability(unreachable_machine(), "start", ("obs@1",))

        self.assertEqual(result.missing_interface, "terminal.oracle@1")

    def test_parenthesization_metadata_does_not_change_identity(self):
        left = compile_capability(
            cyclic_success_machine(),
            "start",
            ("a@1", "b@1"),
            lineage=(("A", "B"), "C"),
        )
        right = compile_capability(
            cyclic_success_machine(),
            "start",
            ("a@1", "b@1"),
            lineage=("A", ("B", "C")),
        )

        self.assertEqual(left.capability_id, right.capability_id)


if __name__ == "__main__":
    unittest.main()
