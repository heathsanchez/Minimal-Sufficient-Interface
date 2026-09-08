"""Public-interface tests. The injected gate is a test double, not Lean."""
import unittest
from pathlib import Path
import os
import numpy as np

import arc3_observation_probe as P
import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F
from test_arc3_multilevel_transfer import SequenceWorld, source_fixture


class RepeatWorld(SequenceWorld):
    steps = 0
    def step(self, action):
        type(self).steps += 1
        if self.level < 2:
            self.run = self.run + 1 if action == 1 else 0
            if self.run == 4:
                self.level += 1
                self.run = 0
        return self.frame()


def source():
    s = source_fixture()
    s['cold'] = F.replay(SequenceWorld, (0,) * 8, None, 120)
    return s


class Tests(unittest.TestCase):
    @staticmethod
    def approve(identity, outcomes, evidence_sha, output):
        return {'identity': identity, 'source_sha256': evidence_sha,
                'marker': 'TEST_ONLY_GATE=' + identity}

    def run_world(self, factory=SequenceWorld, gate=None, **kwargs):
        return P.run(factory, (0, 1, 2), source(),
                     Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'msi-observation-tests',
                     gate=gate if gate is not None else self.approve, **kwargs)

    def test_source_derived_probes_are_bounded_and_deduplicated(self):
        option = (1,) * 4
        candidates = P.probes(tuple(range(256)), option)
        self.assertEqual(candidates[0], option)
        self.assertEqual(candidates[1], option * 2)
        self.assertEqual(candidates[2], option * 4)
        self.assertEqual(candidates[3], option * 8)
        self.assertEqual(len(candidates), 16)
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertLessEqual(max(map(len, candidates)), 32)
        self.assertEqual(len([p for p in candidates if len(p) == 1]), 8)

    def test_exact_frame_delta(self):
        a = {'frame': [[[0, 0], [0, 0]]]}
        b = {'frame': [[[0, 1], [0, 0]]]}
        d = P.frame_delta(a, b)
        self.assertEqual(d[0]['changed_elements'], 1)
        self.assertEqual(d[0]['bounds'], [[0, 0], [1, 1]])
        self.assertEqual(P.frame_delta(a, a)[0]['changed_elements'], 0)

    def test_nonterminal_effect_is_replayed_not_promoted(self):
        r = self.run_world()
        self.assertEqual(r['status'], 'OBSERVED_RESIDUAL')
        self.assertEqual(r['levels_witnessed'], 1)
        self.assertEqual(r['installed_options'], 1)
        self.assertEqual(len(r['accepted']), 1)
        self.assertFalse(r['terminal_win'])
        self.assertTrue(r['selected_probe']['replay_confirmed'])
        self.assertGreater(r['selected_probe']['novel_observations'], 0)
        self.assertTrue(all(len(t['observations']) == len(t['executed']) + 1 for t in r['traces']))
        self.assertLessEqual(r['training_actions'], 320)
        self.assertLessEqual(r['training_episodes'], 32)

    def test_second_capability_uses_actual_gate_and_counts_all_actions(self):
        s = source()
        RepeatWorld.steps = 0
        r = P.run(RepeatWorld, (0, 1, 2), s,
                  Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'msi-observation-win',
                  gate=self.approve)
        self.assertEqual(r['status'], 'VERIFIED_WIN')
        self.assertEqual(r['warm']['state'], 'WIN')
        self.assertEqual(r['warm']['levels_completed'], 2)
        self.assertEqual(r['warm']['actions'], 8)
        self.assertEqual(len(r['accepted']), 2)
        self.assertEqual(r['installed_options'], 2)
        self.assertEqual(r['training_actions'] - s['training_actions'], RepeatWorld.steps)
        self.assertTrue(r['selected_probe']['replay_confirmed'])

    def test_rejected_new_gate_preserves_first(self):
        calls = []
        def reject(identity, outcomes, evidence_sha, output):
            calls.append(identity)
            answer = self.approve(identity, outcomes, evidence_sha, output)
            if len(calls) == 2:
                answer['identity'] = 'forged'
            return answer
        r = self.run_world(RepeatWorld, gate=reject)
        self.assertEqual(r['status'], 'INCONCLUSIVE_VERIFIER')
        self.assertEqual(r['levels_witnessed'], 1)
        self.assertEqual(r['installed_options'], 1)
        self.assertEqual(len(r['accepted']), 1)
        self.assertEqual(r['warm']['levels_completed'], 1)
        self.assertFalse(r['terminal_win'])

    def test_unfunded_replay_and_forged_source_refuse(self):
        r = self.run_world(max_training_actions=15)
        self.assertEqual(r['status'], 'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(r['training_actions'], 15)
        self.assertEqual(r['installed_options'], 0)
        s = source()
        s['promotion']['identity'] = 'forged'
        with self.assertRaises(ValueError):
            P.run(SequenceWorld, (0, 1, 2), s,
                  Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'msi-observation-forged',
                  gate=self.approve)


if __name__ == '__main__':
    unittest.main(verbosity=2)
