from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.runtime import ActionToken, OnlineController, normalize_frame


def frame(value: int = 0, *, level: int = 0, state: str = "NOT_FINISHED", actions=(1, 2, 3), h=4, w=6):
    grid = [[value for _ in range(w)] for _ in range(h)]
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": state,
        "available_actions": list(actions),
    }


class RuntimeContracts(unittest.TestCase):
    def test_normalize_frame_is_canonical_and_public_only(self):
        obs = normalize_frame(frame(7, level=2, actions=(3, 1)))
        self.assertEqual(obs.levels_completed, 2)
        self.assertEqual(obs.state, "NOT_FINISHED")
        self.assertEqual(obs.available_actions, (1, 3))
        self.assertEqual(obs.height, 4)
        self.assertEqual(obs.width, 6)
        self.assertTrue(obs.frame_digest)

    def test_exploration_is_deterministic_and_least_tested(self):
        c = OnlineController((1, 2, 3))
        f = frame()
        a1 = c.observe_and_choose(f)
        a2 = c.observe_and_choose(f)
        a3 = c.observe_and_choose(f)
        self.assertEqual((a1.action_id, a2.action_id, a3.action_id), (1, 2, 3))

    def test_progress_suffix_is_retained_and_reused_only_at_matching_guard(self):
        c = OnlineController((1, 2))
        start = frame(0, level=0)
        first = c.observe_and_choose(start)
        self.assertEqual(first.action_id, 1)
        second = c.observe_and_choose(frame(1, level=0))
        self.assertEqual(second.action_id, 2)
        # The second action is witnessed to complete the level on the next call.
        c.observe_and_choose(frame(9, level=1))
        self.assertEqual(c.retained_option_count, 1)

        c.reset_episode()
        reused = c.observe_and_choose(start)
        self.assertEqual(reused.action_id, 1)
        self.assertEqual(reused.source, "retained")

        c.reset_episode()
        different = c.observe_and_choose(frame(8, level=0))
        self.assertNotEqual(different.source, "retained")

    def test_reset_clears_local_history_but_preserves_retained_options(self):
        c = OnlineController((1,))
        c.observe_and_choose(frame(0, level=0, actions=(1,)))
        c.observe_and_choose(frame(9, level=1, actions=(1,)))
        self.assertEqual(c.retained_option_count, 1)
        self.assertGreater(c.local_history_length, 0)
        c.reset_episode()
        self.assertEqual(c.local_history_length, 0)
        self.assertEqual(c.retained_option_count, 1)

    def test_complex_grounding_starts_with_public_coarse_lattice(self):
        c = OnlineController((6,), grounding_stride=8, max_grounded_actions=256)
        token = c.observe_and_choose(frame(actions=(6,), h=64, w=64))
        self.assertIsInstance(token, ActionToken)
        self.assertEqual(token.action_id, 6)
        # Exact first donor token: half-stride offset on public dimensions.
        self.assertEqual((token.x, token.y), (4, 4))

    def test_complex_grounding_is_deterministic_diverse_and_bounded(self):
        f = frame(actions=(6,), h=64, w=64)
        a = OnlineController((6,), grounding_stride=8, max_grounded_actions=256)
        b = OnlineController((6,), grounding_stride=8, max_grounded_actions=256)

        seq_a = [a.observe_and_choose(f) for _ in range(80)]
        seq_b = [b.observe_and_choose(f) for _ in range(80)]
        coords_a = [(t.x, t.y) for t in seq_a]
        coords_b = [(t.x, t.y) for t in seq_b]

        self.assertEqual(coords_a, coords_b)
        self.assertEqual(len(set(coords_a)), 80)
        self.assertEqual(coords_a[:3], [(4, 4), (12, 4), (20, 4)])
        for x, y in coords_a:
            self.assertGreaterEqual(x, 0)
            self.assertLess(x, 64)
            self.assertGreaterEqual(y, 0)
            self.assertLess(y, 64)

    def test_complex_grounding_moves_from_coarse_to_finer_scale(self):
        f = frame(actions=(6,), h=64, w=64)
        c = OnlineController((6,), grounding_stride=8, max_grounded_actions=256)
        coords = [(c.observe_and_choose(f).x, c._last_action.y) for _ in range(66)]
        # First 64 probes are the 8x8 stride-8 lattice; the next probe begins
        # the stride-4 refinement and is not a duplicate of the coarse set.
        self.assertEqual(coords[63], (60, 60))
        self.assertEqual(coords[64], (2, 2))
        self.assertNotIn(coords[64], coords[:64])

    def test_unavailable_actions_are_not_selected(self):
        c = OnlineController((1, 2, 6))
        token = c.observe_and_choose(frame(actions=(2,)))
        self.assertEqual(token.action_id, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
