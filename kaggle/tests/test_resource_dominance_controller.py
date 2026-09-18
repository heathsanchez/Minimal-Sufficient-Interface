from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.border_scalar import BorderScalarFactor
from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import ActionToken, normalize_frame


def frame(grid, level=0):
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


def world(marker, remaining, width=16, height=10):
    g = [[4 for _ in range(width)] for _ in range(height)]
    g[4][marker] = 8
    for x in range(width):
        g[-1][x] = 12 if x < remaining else 11
    return tuple(tuple(r) for r in g)


class ResourceDominanceControllerContracts(unittest.TestCase):
    def _controller(self):
        c = ConsequenceController((3, 4), archived_capabilities=())
        c.border_factor = BorderScalarFactor(
            activation_transitions=6,
            min_changes=4,
            min_action_classes=2,
            min_sign_consistency=0.75,
            min_projection_compression=1.5,
        )
        # Admit bottom scalar while visiting root/target world states.
        frames = [
            world(2,16), world(2,15), world(3,14), world(2,13),
            world(3,12), world(2,11), world(3,10),
        ]
        for i, (before, after) in enumerate(zip(frames, frames[1:])):
            c.border_factor.observe(
                0, before, after, (3 + i % 2, None, None),
                descriptor=f"primitive:{3+i%2}", history=str(i), terminal=False,
            )
        self.assertTrue(c.border_factor.active(0, 10, 16))
        c._ensure_border_replay(0, 10, 16)
        return c

    def test_dominated_untried_world_edge_requests_reset(self):
        c = self._controller()
        high = world(3, 12)
        low = world(3, 6)
        obs_high = normalize_frame(frame(high))
        obs_low = normalize_frame(frame(low))
        target = c._consequence_context(obs_high, high)
        c.resource_dominance.observe(target, c._resource_signature(obs_high, high))

        c._grid = low
        c.world_effects.note_catalog(
            target, ((3, None, None), (4, None, None))
        )
        c.world_effects.record(
            target, (3, None, None), target,
            "primitive:3", 0, "h", False,
        )
        c._primary = (ActionToken(3), ActionToken(4))
        c._decision_tick = 1
        token = c._select_probe(obs_low, c._primary)
        self.assertEqual(token.action_id, 0)
        self.assertEqual(token.source, "resource_reset")
        self.assertIsNotNone(c._resource_replay_plan)

    def test_reset_preserves_replay_plan_and_replays_shortest_world_route(self):
        c = self._controller()
        root_grid = world(2, 16)
        target_grid = world(3, 12)
        root_obs = normalize_frame(frame(root_grid))
        target_obs = normalize_frame(frame(target_grid))
        root = c._consequence_context(root_obs, root_grid)
        target = c._consequence_context(target_obs, target_grid)

        c.world_effects.record(
            root, (3, None, None), target,
            "primitive:3", 1, "h", False,
        )
        c._resource_replay_plan = {
            "root": root,
            "target": target,
            "route": (((3, None, None), target),),
            "index": 0,
        }
        c.reset_episode()
        self.assertIsNotNone(c._resource_replay_plan)

        c._grid = root_grid
        token = c._next_resource_replay(root_obs)
        self.assertEqual(token.action_id, 3)
        self.assertEqual(token.source, "resource_replay")

        c._grid = target_grid
        self.assertIsNone(c._next_resource_replay(target_obs))
        self.assertIsNone(c._resource_replay_plan)

    def test_terminal_failure_cancels_resource_replay(self):
        c = self._controller()
        c._resource_replay_plan = {"root": "a", "target": "b", "route": (), "index": 0}
        c.record_terminal_failure("GAME_OVER")
        self.assertIsNone(c._resource_replay_plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
