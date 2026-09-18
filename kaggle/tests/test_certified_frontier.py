from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.contextual_quotient import ContextualQuotient
from metalogic_arc3.runtime import ActionToken, normalize_frame


def grid(world: int, resource: int, width: int = 8, height: int = 8):
    rows = [[0 for _ in range(width)] for _ in range(height)]
    rows[2][1 if world == 0 else 5] = 7
    for x in range(width):
        rows[-1][x] = 12 if x < resource else 11
    return tuple(tuple(row) for row in rows)


def frame(g):
    return {
        "frame": [g],
        "levels_completed": 0,
        "state": "NOT_FINISHED",
        "available_actions": [3, 4],
    }


def activate_quotient(c: ConsequenceController) -> tuple[tuple[int, ...], ...]:
    c.contextual_quotient = ContextualQuotient(
        activation_transitions=8,
        min_compression=2.0,
        min_repeated_events=6,
        depths=(1,),
    )
    world = 0
    resource = 8
    for _ in range(8):
        before = grid(world, resource)
        action = (3 if world == 0 else 4, None, None)
        world = 1 - world
        resource -= 1
        after = grid(world, resource)
        c.contextual_quotient.observe(
            0, before, after, action, "CONTINUE"
        )
    current = grid(0, 4)
    assert c.contextual_quotient.active_candidate(0, 8, 8) is not None
    return current


class CertifiedFrontierContracts(unittest.TestCase):
    def _controller_with_frontier(self, *, certified: bool) -> tuple[ConsequenceController, object, tuple[ActionToken, ...]]:
        c = ConsequenceController((3, 4), archived_capabilities=())
        current = activate_quotient(c) if certified else grid(0, 4)
        obs = normalize_frame(frame(current))
        c._grid = current
        catalog = (ActionToken(3), ActionToken(4))
        c._primary = catalog
        c._decision_tick = 1

        context = c._consequence_context(obs, current)
        target = "learned-target"
        c.effects.record(
            context,
            (3, None, None),
            target,
            "primitive:3",
            1,
            "h",
            False,
        )
        c.effects.note_catalog(target, ((4, None, None),))

        # Make action 4 the generic affordance favorite. A certified graph
        # frontier should still choose action 3, which reaches an unexplored
        # successor state.
        for i in range(3):
            c.affordances.record(
                f"a{i}",
                (4, None, None),
                "primitive:4",
                (1, 1, 1, 0, 0, 1),
                directness=1.0,
                target=f"b{i}",
            )
        return c, obs, catalog

    def test_certified_graph_frontier_outranks_generic_affordance(self):
        c, obs, catalog = self._controller_with_frontier(certified=True)
        token = c._select_probe(obs, catalog)
        self.assertEqual(token.action_id, 3)
        self.assertEqual(token.source, "consequence_frontier")

    def test_exact_context_keeps_existing_affordance_priority(self):
        c, obs, catalog = self._controller_with_frontier(certified=False)
        token = c._select_probe(obs, catalog)
        self.assertEqual(token.action_id, 4)
        self.assertEqual(token.source, "affordance")

    def test_delayed_probe_still_outranks_certified_frontier(self):
        c, obs, catalog = self._controller_with_frontier(certified=True)
        c._decision_tick = 8
        token = c._select_probe(obs, catalog)
        self.assertEqual(token.source, "consequence_delayed_probe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
