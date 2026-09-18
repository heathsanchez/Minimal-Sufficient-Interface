from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import ActionToken, normalize_frame
from metalogic_arc3.border_scalar import BorderScalarFactor


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

    def test_earned_world_factor_prioritizes_untried_world_action_over_affordance(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.border_factor = BorderScalarFactor(
            activation_transitions=4,
            min_changes=3,
            min_action_classes=2,
            min_sign_consistency=0.75,
            min_projection_compression=1.5,
        )

        def g(remaining):
            rows = [[4] * 8 for _ in range(8)]
            for x in range(8):
                rows[-1][x] = 12 if x < remaining else 11
            rows[3][3] = 8
            return tuple(tuple(row) for row in rows)

        frames = [g(v) for v in (8, 7, 6, 5, 8)]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            c.border_factor.observe(
                0, before, after, (3 + i % 2, None, None),
                descriptor=f"primitive:{3+i%2}", history=str(i), terminal=False,
            )
        self.assertTrue(c.border_factor.active(0, 8, 8))
        c._ensure_border_replay(0, 8, 8)

        c._grid = g(6)
        obs = normalize_frame(frame(c._grid))
        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 1
        context = c._consequence_context(obs, c._grid)

        for i in range(4):
            c.world_affordances.record(
                f"x{i}", (3, None, None), "primitive:3",
                (1, 1, 1, 0, 0, 1), directness=1.0,
            )
        c.world_effects.record(
            context, (3, None, None), context,
            "primitive:3", 1, "h", False,
        )

        selected = c._select_probe(obs, catalog)
        self.assertEqual(selected.action_id, 4)
        self.assertEqual(selected.source, "consequence_frontier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
