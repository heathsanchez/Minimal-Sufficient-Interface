"""Small, source-blind regression tests for the corrected feedback loop."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "arc3_consequence"))
from closed_feedback_v2 import FeedbackArchive, develop, replay, digest


class CounterWorld:
    def __init__(self, goal=4, log=None):
        self.n = 0
        self.goal = goal
        self.log = log
        self.observation_space = self.frame()
    def frame(self):
        return {"frame": [[[self.n]]], "levels_completed": int(self.n >= self.goal),
                "state": "WIN" if self.n >= self.goal else "NOT_FINISHED",
                "available_actions": [0, 1]}
    def reset(self):
        self.n = 0
        return self.frame()
    def step(self, action):
        if self.log is not None:
            self.log.append((self.n, action))
        if action == 1:
            self.n += 1
        return self.frame()
    def close(self):
        pass


class HiddenWorld:
    def __init__(self):
        self.phase = 0
        self.won = False
        self.observation_space = self.frame()
    def frame(self):
        return {"frame": [[[0]]], "levels_completed": int(self.won),
                "state": "WIN" if self.won else "NOT_FINISHED",
                "available_actions": [0, 1, 2]}
    def reset(self):
        self.phase = 0
        self.won = False
        return self.frame()
    def step(self, action):
        if action == 1:
            self.phase = 1
        elif action == 2 and self.phase == 1:
            self.won = True
        return self.frame()
    def close(self):
        pass


class Tests(unittest.TestCase):
    def test_terminal_clipping_preserves_actual_winning_prefix(self):
        r = replay(lambda: CounterWorld(2), (1, 1, 1), None, 3)
        self.assertEqual(r["status"], "OBSERVED_TERMINAL_PREFIX")
        self.assertEqual(r["executed"], (1, 1))
        self.assertEqual(r["state"], "WIN")
        d = develop(lambda: CounterWorld(2), (0, 1), budget=3, max_depth=3,
                    max_training_actions=30, max_episodes=30,
                    seed_programs=((1, 1, 1),))
        self.assertEqual(d["status"], "VERIFIED_WIN")
        self.assertEqual(d["result"]["executed"], (1, 1))

    def test_visible_nonterminal_effect_is_installed_and_reused(self):
        d = develop(lambda: CounterWorld(4), (0, 1), budget=4, max_depth=4,
                    max_training_actions=12, max_episodes=12)
        self.assertGreater(d["development"]["options"], 0)
        self.assertTrue(all(o["proof_sha256"] for o in d["development"]["installed_options"]))

    def test_reuse_at_new_entry_is_reverified(self):
        initial = replay(lambda: CounterWorld(5), (1,), None, 4)
        d = develop(lambda: CounterWorld(5), (0, 1), prefix=(1,),
                    checkpoint=initial["final_sha256"], budget=4, max_depth=4,
                    max_training_actions=5, max_episodes=5)
        options = d["development"]["installed_options"]
        self.assertEqual(options[0]["source"], ("retained_prefix",))
        self.assertTrue(any(o["entry_path"] == (1,) and o["source"] == ("option", 0)
                            and o["dependencies"] == (0,) for o in options))
        self.assertNotEqual(d["status"], "VERIFIED_WIN")

    def test_repetition_changes_reachability_under_matched_bound(self):
        kwargs = dict(budget=4, max_depth=4, max_training_actions=25, max_episodes=25)
        cold = develop(lambda: CounterWorld(4), (0, 1), feedback=False, **kwargs)
        warm = develop(lambda: CounterWorld(4), (0, 1), feedback=True, **kwargs)
        self.assertNotEqual(cold["status"], "VERIFIED_WIN")
        self.assertEqual(warm["status"], "VERIFIED_WIN")
        self.assertEqual(warm["result"]["executed"], (1, 1, 1, 1))
        self.assertLess(warm["training_actions"], cold["training_actions"])
        self.assertTrue(any(o["source"][0] == "repeat" for o in warm["development"]["installed_options"]))

    def test_hidden_histories_are_not_dropped(self):
        d = develop(HiddenWorld, (0, 1, 2), budget=2, max_depth=2,
                    max_training_actions=30, max_episodes=30)
        self.assertEqual(d["status"], "VERIFIED_WIN")
        self.assertEqual(d["result"]["executed"], (1, 2))

    def test_forged_entry_effect_and_dependencies_are_rejected(self):
        a = FeedbackArchive()
        r = replay(lambda: CounterWorld(4), (1,), None, 4)
        entry = digest(r["observations"][0])
        first = a.install(entry, (1,), r["final_sha256"], r)
        self.assertEqual(first["program"], (1,))
        with self.assertRaises(ValueError):
            a.install(r["final_sha256"], (1,), r["final_sha256"], r)
        with self.assertRaises(ValueError):
            a.install(entry, (1,), entry, r)
        with self.assertRaises(ValueError):
            a.install(entry, (1,), r["final_sha256"], r, (1,))
        with self.assertRaises(ValueError):
            a.install(entry, (1,), r["final_sha256"], r, (), ("option", 99), (99,))
        r2 = replay(lambda: CounterWorld(4), (1, 1), None, 4)
        with self.assertRaises(ValueError):
            a.install(entry, (1, 1), r2["final_sha256"], r2, (),
                      ("repeat", 0, 3), (0,))
        a.install(entry, (1, 1), r2["final_sha256"], r2, (),
                  ("repeat", 0, 2), (0,))

    def test_wrong_checkpoint_is_not_progress(self):
        d = develop(lambda: CounterWorld(4), (0, 1), prefix=(1,),
                    checkpoint="incorrect", budget=4, max_training_actions=20)
        self.assertEqual(d["status"], "INCONCLUSIVE_PREFIX_MISMATCH")
        self.assertEqual(d["development"]["options"], 0)

    def test_bound_does_not_promote_unconfirmed_win(self):
        d = develop(lambda: CounterWorld(4), (0, 1), budget=4, max_depth=4,
                    max_training_actions=6, max_episodes=6)
        self.assertNotEqual(d["status"], "VERIFIED_WIN")
        self.assertLessEqual(d["training_actions"], 6)
        self.assertLessEqual(d["training_episodes"], 6)

    def test_initial_win_is_preserved(self):
        d = develop(lambda: CounterWorld(0), (0, 1), budget=3)
        self.assertEqual(d["status"], "VERIFIED_WIN")
        self.assertEqual(d["result"]["state"], "WIN")

    def test_unsolved_bound_is_not_an_impossibility_claim(self):
        d = develop(lambda: CounterWorld(10), (0, 1), budget=4, max_depth=4,
                    max_training_actions=25, max_episodes=25)
        self.assertIn(d["status"], ("TRAINING_BOUND_EXHAUSTED", "NO_TERMINAL_WITHIN_BOUND"))
        self.assertLessEqual(d["training_actions"], 25)
        self.assertNotEqual(d["status"], "VERIFIED_WIN")


if __name__ == "__main__":
    unittest.main()
