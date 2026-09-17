from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import ActionToken, normalize_frame
from metalogic_arc3.stable_state import StableStateQuotient


def frame(grid, *, level=0, actions=(3, 4), state="NOT_FINISHED"):
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": state,
        "available_actions": list(actions),
    }


class ConsequenceAffordanceControllerContracts(unittest.TestCase):
    def test_nonterminal_effect_is_recorded_as_affordance_evidence(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        before = frame([[0, 0], [0, 0]])
        after = frame([[0, 1], [0, 0]])
        token = c.observe_and_choose(before)
        self.assertIsNotNone(token)
        c.observe_and_choose(after)
        self.assertGreater(c.effects.total_observations, 0)
        self.assertGreater(c.affordances.affordance_score(f"primitive:{token.action_id}"), 0.0)

    def test_affordance_score_breaks_raw_novelty_tie_toward_control(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        obs = normalize_frame(frame([[0, 0], [0, 0]]))
        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 1

        # Raw effect frequency alone prefers action 4.
        for i in range(4):
            c.effects.record("ctx", (4, None, None), f"o{i}", "primitive:4", 1, "h", False)
        c.effects.record("ctx", (3, None, None), "o", "primitive:3", 1, "h", False)

        # But repeated action-aligned structure makes action 3 the stronger
        # controllable affordance; action 4's novelty is weakly attributed.
        for i in range(3):
            c.affordances.record(
                f"a{i}", (3, None, None), "primitive:3", (1, 1, 1, 0, 0, 1), directness=1.0
            )
            c.affordances.record(
                f"b{i}", (4, None, None), "primitive:4", (4, 2, 2, 0, 0, 2), directness=0.1
            )

        selected = c._select_probe(obs, catalog)
        self.assertEqual(selected.action_id, 3)
        self.assertEqual(selected.source, "affordance")

    def test_delayed_probe_survives_affordance_ranking(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        obs = normalize_frame(frame([[0, 0], [0, 0]]))
        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 8
        first = c._select_probe(obs, catalog)
        second = c._select_probe(obs, catalog)
        self.assertEqual(first.source, "consequence_delayed_probe")
        self.assertEqual(second.action_id, first.action_id)
        self.assertEqual(second.source, "consequence_delayed_probe")

    def test_consequence_context_is_exact_until_quotient_activates(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        raw = frame([[0, 0], [0, 0]])
        obs = normalize_frame(raw)
        grid = ((0, 0), (0, 0))
        self.assertEqual(c._consequence_context(obs, grid), obs.evidence_sha256)

    def test_effect_recording_switches_only_learned_graph_to_stable_context(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.state_quotient = StableStateQuotient(
            activation_transitions=2,
            min_change_rate=1.0,
            min_action_classes=2,
        )
        before = ((0, 0), (0, 0))
        middle = ((1, 0), (0, 0))
        after = ((2, 0), (0, 0))
        obs0 = normalize_frame(frame(before))
        obs1 = normalize_frame(frame(middle))
        obs2 = normalize_frame(frame(after))

        c._previous = obs0
        c._pending_effect = (
            obs0.evidence_sha256, (3, None, None), before, "primitive:3", "h0"
        )
        c._record_effect(frame(middle), obs1)
        self.assertFalse(c.state_quotient.active(0, 2, 2))

        c._previous = obs1
        c._pending_effect = (
            obs1.evidence_sha256, (4, None, None), middle, "primitive:4", "h1"
        )
        c._record_effect(frame(after), obs2)
        self.assertTrue(c.state_quotient.active(0, 2, 2))

        stable = c._consequence_context(obs2, after)
        self.assertTrue(stable.startswith("q:"))
        self.assertNotEqual(stable, obs2.evidence_sha256)

        baseline = ConsequenceController((3, 4), archived_capabilities=())
        self.assertEqual(c._memory_context(obs2), baseline._memory_context(obs2))

        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 1
        c._select_probe(obs2, catalog)
        self.assertIn(stable, c.effects.catalogs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
