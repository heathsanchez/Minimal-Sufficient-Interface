"""Public-interface regression controls. Injected gates are test doubles, not Lean."""
import copy
import json
import os
import unittest
from pathlib import Path

import arc3_level4_probe as P
import arc3_shared_transfer as T
import closed_feedback_v2 as F


class ThreeStageWorld:
    steps = 0

    def __init__(self, progress=True):
        self.level = 0
        self.tick = 0
        self.progress = progress
        self.observation_space = self.frame()

    def frame(self):
        return {"frame": [[[self.level, self.tick], [0, 0]]],
                "levels_completed": self.level,
                "state": "WIN" if self.level == 4 else "NOT_FINISHED",
                "available_actions": [0, 1, 2]}

    def reset(self):
        self.level = 0
        self.tick = 0
        return self.frame()

    def step(self, action):
        type(self).steps += 1
        if self.level < 3 and action == 1:
            self.level += 1
        elif self.level == 3 and action == 2 and self.progress:
            self.level = 4
        else:
            self.tick = (self.tick + 1) % 3
        return self.frame()

    def close(self):
        return None


def approve(identity, outcomes, evidence_sha, output):
    return {"identity": identity, "source_sha256": evidence_sha,
            "marker": "TEST_ONLY_GATE=" + identity}


def source_fixture(progress=True):
    factory = lambda: ThreeStageWorld(progress)
    prefix = (1, 1, 1)
    cold = F.replay(factory, (0,), None, 120)
    proof = F.replay(factory, prefix, None, 120)
    accepted = []
    for i in (1, 2, 3):
        full = prefix[:i]
        witness = F.replay(factory, full, None, 120)
        stage = {"level": i, "prefix": full,
                 "checkpoint_sha256": witness["final_sha256"]}
        approval = T.promote(factory, full, stage, cold, proof["initial_sha256"],
                             F.FeedbackArchive(), Path(os.environ.get("RUNNER_TEMP", "/tmp")) /
                             ("msi-level4-fixture-" + str(i)), gate=approve)
        assert approval["status"] == "REPLAY_GATED_PROMOTION_PASS"
        accepted.append({"level": i, "prefix": full, "suffix": (1,),
                         "checkpoint_sha256": witness["final_sha256"],
                         "promotion": approval["identity"],
                         "gate_source_sha256": approval["approval"]["source_sha256"]})
    return {"status": "ALL_LEVELS_WITNESSED", "source_commit": T.FROZEN,
            "archive_run": P.PRIOR_DISCOVERY_RUN,
            "archive_commit": "c65201683d0eccd8a03e07abb9ba35409419cf14",
            "new_discoveries": 0, "terminal_win": False,
            "initial_sha256": proof["initial_sha256"],
            "checkpoint_sha256": proof["final_sha256"], "prefix": prefix,
            "warm": proof, "cold": cold, "training_actions": 10,
            "training_episodes": 3, "installed_options": 3,
            "levels_witnessed": 3, "accepted": accepted}


class Tests(unittest.TestCase):
    def run_world(self, source=None, progress=True, gate=approve, **kwargs):
        return P.run(lambda: ThreeStageWorld(progress), (0, 1, 2),
                     source if source is not None else source_fixture(progress),
                     Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "msi-level4-tests",
                     gate=gate, **kwargs)

    def test_new_progress_is_replayed_and_promoted(self):
        r = self.run_world()
        self.assertEqual(r["status"], "VERIFIED_WIN")
        self.assertEqual(r["warm"]["executed"], (1, 1, 1, 2))
        self.assertEqual(r["levels_witnessed"], 4)
        self.assertEqual(r["new_discoveries"], 1)
        self.assertEqual(r["new_installed_options"], 2)
        self.assertEqual(r["installed_options"], 5)
        self.assertEqual(len(r["accepted"]), 4)

    def test_nonterminal_effect_is_not_a_new_policy(self):
        r = self.run_world(progress=False)
        self.assertEqual(r["status"], "OBSERVED_RESIDUAL")
        self.assertEqual(r["new_discoveries"], 0)
        self.assertEqual(r["installed_options"], 3)
        self.assertTrue(r["selected_probe"]["replay_confirmed"])

    def test_rejected_new_gate_preserves_source(self):
        calls = []
        def reject(identity, outcomes, evidence_sha, output):
            calls.append(identity)
            result = approve(identity, outcomes, evidence_sha, output)
            if len(calls) == 2:
                result["identity"] = "forged"
            return result
        r = self.run_world(gate=reject)
        self.assertEqual(r["status"], "INCONCLUSIVE_VERIFIER")
        self.assertEqual(r["levels_witnessed"], 3)
        self.assertEqual(r["new_discoveries"], 0)
        self.assertEqual(r["installed_options"], 3)

    def test_stale_source_identity_is_refused(self):
        source = source_fixture()
        source["accepted"][-1]["promotion"] = "forged"
        r = self.run_world(source=source)
        self.assertEqual(r["status"], "INCONCLUSIVE_SOURCE_IDENTITY")
        self.assertEqual(r["new_discoveries"], 0)

    def test_missing_budget_cannot_start_replay(self):
        r = self.run_world(max_training_actions=10)
        self.assertEqual(r["status"], "TRAINING_BOUND_EXHAUSTED")
        self.assertEqual(r["training_actions"], 10)
        self.assertEqual(r["installed_options"], 3)

    def test_actual_interactions_are_charged(self):
        source = source_fixture()
        before = ThreeStageWorld.steps
        r = self.run_world(source=source)
        self.assertEqual(r["training_actions"] - 10, ThreeStageWorld.steps - before)

    def test_public_component_probes_are_bounded(self):
        obs = {"frame": [[[0,0,0],[0,1,1],[0,1,1]]]}
        actions = tuple((6,x,y) for y in range(3) for x in range(3))
        chosen = P.image_representatives(obs, actions)
        self.assertTrue(chosen)
        self.assertTrue(set(chosen).issubset(set(actions)))
        self.assertEqual(chosen, P.image_representatives(obs, actions))
        self.assertLessEqual(len(P.probes(actions, obs, (), 4)), 4)

    def test_real_archive_metadata(self):
        source = json.loads(Path(os.environ["MSI_ARCHIVE_TRANSFER_EVIDENCE"]).read_text())
        prefix, checkpoint, level = P.validate_source(source)
        self.assertEqual(level, 3)
        self.assertEqual(len(prefix), 28)
        self.assertEqual(checkpoint, source["checkpoint_sha256"])
        bad = copy.deepcopy(source)
        bad["accepted"][-1]["checkpoint_sha256"] = "forged"
        with self.assertRaises(ValueError):
            P.validate_source(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
