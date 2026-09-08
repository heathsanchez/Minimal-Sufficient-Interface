"""Small public-interface controls; the injected gate is a test double, not Lean."""
import os
import unittest
from pathlib import Path

import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F


class SequenceWorld:
    def __init__(self):
        self.level = 0
        self.run = 0
        self.observation_space = self.frame()

    def frame(self):
        return {"frame": [[[self.level, self.run]]], "levels_completed": self.level,
                "state": "WIN" if self.level == 2 else "NOT_FINISHED",
                "available_actions": [0, 1, 2]}

    def reset(self):
        self.level = 0
        self.run = 0
        return self.frame()

    def step(self, action):
        if self.level < 2:
            expected = self.level + 1
            self.run = self.run + 1 if action == expected else 0
            if self.run == 4:
                self.level += 1
                self.run = 0
        return self.frame()

    def close(self):
        return None


def source_fixture():
    prefix = (1,) * 4
    proof = F.replay(SequenceWorld, prefix, None, 120)
    stage = {"level": 1, "prefix": list(prefix), "suffix": list(prefix),
             "checkpoint_sha256": proof["final_sha256"]}
    return {"status": "COMPARABLE", "source_commit": T.FROZEN,
            "initial_sha256": proof["initial_sha256"], "training_actions": 15,
            "promotion": {"status": "REPLAY_GATED_PROMOTION_PASS", "identity": M.SOURCE_IDENTITY},
            "source_development": {"prefix": list(prefix), "stages": [stage], "training_episodes": 0}}


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, _, cls.compositional, cls.multilevel = T.load_frozen(os.environ["MSI_FROZEN_DIR"])

    def run_world(self, source=None, gate=None, **kwargs):
        return M.continue_verified(SequenceWorld, (0, 1, 2),
            source if source is not None else source_fixture(),
            self.compositional.OptionSearch, self.multilevel.execute_stage,
            Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "msi-multilevel-tests",
            gate=gate if gate is not None else self.approve, **kwargs)

    @staticmethod
    def approve(identity, outcomes, evidence_sha, output):
        return {"identity": identity, "source_sha256": evidence_sha,
                "marker": "TEST_ONLY_GATE=" + identity}

    def test_second_capability_is_acquired_and_deployed(self):
        r = self.run_world()
        self.assertEqual(r["status"], "VERIFIED_WIN")
        self.assertEqual(r["warm"]["state"], "WIN")
        self.assertEqual(r["warm"]["levels_completed"], 2)
        self.assertEqual(r["warm"]["actions"], 8)
        self.assertEqual(len(r["accepted"]), 2)
        self.assertGreaterEqual(r["installed_options"], 2)
        self.assertLessEqual(r["training_actions"], 3000)
        self.assertEqual(r["accepted"][1]["suffix"], (2, 2, 2, 2))

    def test_rejected_second_promotion_preserves_first(self):
        calls = []
        def gate(identity, outcomes, evidence_sha, output):
            calls.append(identity)
            result = self.approve(identity, outcomes, evidence_sha, output)
            if len(calls) == 2:
                result["identity"] = "forged"
            return result
        r = self.run_world(gate=gate)
        self.assertEqual(r["status"], "INCONCLUSIVE_VERIFIER")
        self.assertEqual(r["warm"]["levels_completed"], 1)
        self.assertEqual(len(r["accepted"]), 1)
        self.assertFalse(r["terminal_win"])

    def test_missing_or_forged_source_cannot_promote(self):
        source = source_fixture()
        source["promotion"]["identity"] = "forged"
        with self.assertRaises(ValueError):
            self.run_world(source=source)
        source = source_fixture()
        source["promotion"]["status"] = "PENDING"
        with self.assertRaises(ValueError):
            self.run_world(source=source)

    def test_bound_refuses_unfunded_replay(self):
        r = self.run_world(max_training_actions=15)
        self.assertEqual(r["status"], "TRAINING_BOUND_EXHAUSTED")
        self.assertEqual(r["training_actions"], 15)
        self.assertEqual(r["installed_options"], 0)
        self.assertFalse(r["terminal_win"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
