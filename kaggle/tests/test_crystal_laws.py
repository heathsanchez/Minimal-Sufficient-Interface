from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.crystal_laws import (
    ArcCrystalLawBridge,
    ArcLawBinding,
    LawStatus,
    VerifiedLawStore,
    Prediction,
)


def apply_cycle(state: int, steps: int, period: int) -> int:
    for _ in range(steps):
        state = (state + 1) % period
    return state


class ArcCrystalLawContracts(unittest.TestCase):
    def test_one_global_cycle_law_reuses_across_two_distinct_contexts(self):
        store = VerifiedLawStore.default()
        bridge = ArcCrystalLawBridge(store)
        action = (3, None, None)

        bridge.admit_binding(ArcLawBinding(
            context=("game-a", "level-2"),
            action=action,
            period=2,
            protected_orbit=("a0", "a1", "a0"),
            support_refs=("obs:a",),
        ))
        bridge.admit_binding(ArcLawBinding(
            context=("game-b", "level-7"),
            action=action,
            period=3,
            protected_orbit=("b0", "b1", "b2", "b0"),
            support_refs=("obs:b",),
        ))

        a = bridge.normalize_repetition(
            ("game-a", "level-2"), action, 8, live_supports=("obs:a",)
        )
        b = bridge.normalize_repetition(
            ("game-b", "level-7"), action, 8, live_supports=("obs:b",)
        )

        self.assertEqual(a.status, LawStatus.WARRANTED)
        self.assertEqual(b.status, LawStatus.WARRANTED)
        self.assertEqual(a.law_id, b.law_id)
        self.assertEqual(a.reduced_count, 0)
        self.assertEqual(b.reduced_count, 2)
        self.assertEqual(apply_cycle(0, 8, 2), apply_cycle(0, a.reduced_count, 2))
        self.assertEqual(apply_cycle(0, 8, 3), apply_cycle(0, b.reduced_count, 3))

    def test_missing_binding_returns_unknown_and_does_not_rewrite(self):
        bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
        answer = bridge.normalize_repetition(
            ("unseen-game", "level-1"), (3, None, None), 8
        )
        self.assertEqual(answer.status, LawStatus.UNKNOWN)
        self.assertEqual(answer.reason, "missing_applicability_binding")
        self.assertEqual(answer.reduced_count, 8)
        self.assertIsNotNone(answer.residual)
        self.assertEqual(answer.residual["needed"], "finite-cycle-binding")

    def test_revoked_binding_support_returns_unknown(self):
        bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
        binding = ArcLawBinding(
            context=("game-a", "level-2"),
            action=(3, None, None),
            period=2,
            protected_orbit=("a0", "a1", "a0"),
            support_refs=("obs:a",),
        )
        bridge.admit_binding(binding)
        answer = bridge.normalize_repetition(
            binding.context, binding.action, 8, live_supports=()
        )
        self.assertEqual(answer.status, LawStatus.UNKNOWN)
        self.assertEqual(answer.reason, "missing_live_support")
        self.assertEqual(answer.reduced_count, 8)

    def test_bad_cycle_binding_is_rejected(self):
        with self.assertRaises(ValueError):
            ArcLawBinding(
                context=("bad",),
                action=(3, None, None),
                period=3,
                protected_orbit=("x0", "x1", "x2", "different"),
                support_refs=("obs:bad",),
            )

    def test_transfer_ablation_measures_action_savings_without_semantic_change(self):
        store = VerifiedLawStore.default()
        bridge = ArcCrystalLawBridge(store)
        action = (3, None, None)
        fixtures = (
            (("situation-1",), 2, ("a0", "a1", "a0"), "s1"),
            (("situation-2",), 3, ("b0", "b1", "b2", "b0"), "s2"),
        )
        baseline_actions = 0
        crystal_actions = 0
        for context, period, orbit, support in fixtures:
            bridge.admit_binding(ArcLawBinding(
                context=context, action=action, period=period,
                protected_orbit=orbit, support_refs=(support,),
            ))
            baseline_actions += 8
            answer = bridge.normalize_repetition(
                context, action, 8, live_supports=(support,)
            )
            crystal_actions += answer.reduced_count
            self.assertEqual(
                apply_cycle(0, 8, period),
                apply_cycle(0, answer.reduced_count, period),
            )

        self.assertEqual(baseline_actions, 16)
        self.assertEqual(crystal_actions, 2)
        self.assertEqual(baseline_actions - crystal_actions, 14)

        # Ablation: without the shared law, both bindings remain inert.
        empty = ArcCrystalLawBridge(VerifiedLawStore(()))
        for context, period, orbit, support in fixtures:
            empty.admit_binding(ArcLawBinding(
                context=context, action=action, period=period,
                protected_orbit=orbit, support_refs=(support,),
            ))
            answer = empty.normalize_repetition(
                context, action, 8, live_supports=(support,)
            )
            self.assertEqual(answer.status, LawStatus.UNKNOWN)
            self.assertEqual(answer.reduced_count, 8)

    def test_separator_law_reuses_across_distinct_hypothesis_spaces(self):
        bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
        a = (1, None, None)
        b = (2, None, None)

        first = bridge.choose_separator(
            hypotheses=("h1", "h2", "h3"),
            actions=(a, b),
            predictions=(
                Prediction("h1", a, "red"), Prediction("h2", a, "green"), Prediction("h3", a, "blue"),
                Prediction("h1", b, "same"), Prediction("h2", b, "same"), Prediction("h3", b, "same"),
            ),
            support_refs=("model:first",),
            live_supports=("model:first",),
        )
        second = bridge.choose_separator(
            hypotheses=("k1", "k2", "k3", "k4"),
            actions=(a, b),
            predictions=(
                Prediction("k1", a, "same"), Prediction("k2", a, "same"),
                Prediction("k3", a, "same"), Prediction("k4", a, "same"),
                Prediction("k1", b, "left"), Prediction("k2", b, "left"),
                Prediction("k3", b, "right"), Prediction("k4", b, "right"),
            ),
            support_refs=("model:second",),
            live_supports=("model:second",),
        )
        self.assertEqual(first.status, LawStatus.WARRANTED)
        self.assertEqual(first.chosen_action, a)
        self.assertEqual(first.worst_case_survivors, 1)
        self.assertEqual(second.status, LawStatus.WARRANTED)
        self.assertEqual(second.chosen_action, b)
        self.assertEqual(second.worst_case_survivors, 2)
        self.assertEqual(first.law_id, second.law_id)

    def test_separator_missing_prediction_or_support_fails_closed(self):
        bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
        a = (1, None, None)
        incomplete = bridge.choose_separator(
            hypotheses=("h1", "h2"),
            actions=(a,),
            predictions=(Prediction("h1", a, "x"),),
            support_refs=("model:x",),
            live_supports=("model:x",),
        )
        self.assertEqual(incomplete.status, LawStatus.UNKNOWN)
        self.assertEqual(incomplete.reason, "incomplete_prediction_table")
        self.assertEqual(incomplete.residual["needed"], "prediction")

        revoked = bridge.choose_separator(
            hypotheses=("h1", "h2"),
            actions=(a,),
            predictions=(Prediction("h1", a, "x"), Prediction("h2", a, "y")),
            support_refs=("model:x",),
            live_supports=(),
        )
        self.assertEqual(revoked.status, LawStatus.UNKNOWN)
        self.assertEqual(revoked.reason, "missing_live_support")

    def test_separator_law_reduces_probe_count_under_frozen_predictions(self):
        bridge = ArcCrystalLawBridge(VerifiedLawStore.default())
        a = (1, None, None)
        b = (2, None, None)
        hypotheses = ("h1", "h2", "h3")
        table = {
            (h, a): "same" for h in hypotheses
        }
        table.update({("h1", b): "x", ("h2", b): "y", ("h3", b): "z"})
        predictions = tuple(
            Prediction(h, action, table[(h, action)])
            for h in hypotheses for action in (a, b)
        )
        answer = bridge.choose_separator(
            hypotheses=hypotheses,
            actions=(a, b),
            predictions=predictions,
            support_refs=("model:frozen",),
            live_supports=("model:frozen",),
        )
        self.assertEqual(answer.chosen_action, b)

        # True world h2: alphabetical baseline spends a useless probe on a,
        # then b identifies h2. Crystal chooses b first.
        true_h = "h2"
        baseline = [a, b]
        survivors = set(hypotheses)
        baseline_probes = 0
        for action in baseline:
            baseline_probes += 1
            observed = table[(true_h, action)]
            survivors = {h for h in survivors if table[(h, action)] == observed}
            if len(survivors) == 1:
                break
        observed = table[(true_h, answer.chosen_action)]
        crystal_survivors = {
            h for h in hypotheses if table[(h, answer.chosen_action)] == observed
        }
        self.assertEqual(baseline_probes, 2)
        self.assertEqual(crystal_survivors, {"h2"})

        empty = ArcCrystalLawBridge(VerifiedLawStore(()))
        ablated = empty.choose_separator(
            hypotheses=hypotheses,
            actions=(a, b),
            predictions=predictions,
            support_refs=("model:frozen",),
            live_supports=("model:frozen",),
        )
        self.assertEqual(ablated.status, LawStatus.UNKNOWN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
