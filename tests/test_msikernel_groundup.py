import unittest

from msikernel.continuation import Continuation, induced_equivalence
from msikernel.development import Admission, InterfaceRegistry, residual_against
from msikernel.interface import compile_interface
from msikernel.kernel import Equivalence, meet_equivalence
from msikernel.lean_bootstrap import (
    LEAN_STATES,
    SORT0,
    SORT1,
    SORT2,
    compiled_decision,
    compile_lean_sort_interface,
    generic_decision,
    lean_continuations,
    rediscovery_workload,
)


class GroundUpMSIKernel(unittest.TestCase):
    def test_meet_is_exact_intersection_of_future_distinctions(self):
        states = (0, 1, 2, 3)
        a = induced_equivalence(states, (Continuation("parity", lambda x: x % 2),))
        b = induced_equivalence(states, (Continuation("half", lambda x: x // 2),))
        both = induced_equivalence(
            states,
            (
                Continuation("parity", lambda x: x % 2),
                Continuation("half", lambda x: x // 2),
            ),
        )
        self.assertEqual(meet_equivalence(a, b).classes, both.classes)
        self.assertTrue(both.refines(a))
        self.assertTrue(both.refines(b))

    def test_outcome_names_do_not_define_the_interface_ontology(self):
        states = (0, 1, 2, 3)
        left = (
            Continuation("c0", lambda x: "A" if x < 2 else "B"),
            Continuation("c1", lambda x: "X" if x % 2 else "Y"),
        )
        right = (
            Continuation("anonymous0", lambda x: 91 if x < 2 else -7),
            Continuation("anonymous1", lambda x: (3, 4) if x % 2 else (8, 9)),
        )
        self.assertEqual(
            induced_equivalence(states, left).classes,
            induced_equivalence(states, right).classes,
        )

    def test_lean_interface_is_induced_by_futures_not_hand_named_classes(self):
        interface = compile_lean_sort_interface()
        self.assertNotEqual(interface.ref(SORT0), interface.ref(SORT1))
        self.assertNotEqual(interface.ref(SORT1), interface.ref(SORT2))
        nonsorts = [s for s in LEAN_STATES if s.tag != "sort"]
        self.assertEqual(len({interface.ref(s) for s in nonsorts}), 1)

    def test_compiled_lean_interface_is_extensionally_exact(self):
        interface = compile_lean_sort_interface()
        for state in LEAN_STATES:
            for continuation in lean_continuations():
                self.assertEqual(
                    compiled_decision(interface, state, continuation.name),
                    generic_decision(state, continuation.name),
                    (state, continuation.name),
                )

    def test_shared_interface_removes_repeated_semantic_rediscovery(self):
        consumers = tuple(c.name for c in lean_continuations())
        local, shared, ablate = rediscovery_workload(LEAN_STATES * 100, consumers)
        self.assertLess(shared, local)
        self.assertLess(shared, ablate)
        self.assertEqual(ablate, local + shared)

    def test_residual_forces_missing_future_distinction(self):
        current = Equivalence.indiscrete(LEAN_STATES)
        residual = residual_against(LEAN_STATES, current, lean_continuations())
        self.assertIsNotNone(residual)
        repaired = compile_interface("repair", LEAN_STATES, lean_continuations())
        self.assertIsNone(residual_against(LEAN_STATES, repaired.equivalence, lean_continuations()))

    def test_interface_admission_requires_cost_ablation_and_transfer(self):
        registry = InterfaceRegistry()
        registry.install_candidate(
            "lean-sort",
            LEAN_STATES,
            lean_continuations(),
            provenance=("V31", "V33", "V37"),
        )
        status = registry.promote(
            "lean-sort",
            cost_delta=-1,
            ablation_restores_residual=True,
            transferred=True,
        )
        self.assertEqual(status, Admission.ADMITTED)
        self.assertEqual(len(registry.active()), 1)
        registry.revoke("lean-sort")
        self.assertEqual(registry.active(), ())


if __name__ == "__main__":
    unittest.main()
