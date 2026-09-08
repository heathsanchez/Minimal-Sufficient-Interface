"""Public-interface controls for the scheduling-only repair."""
import json
import os
import unittest
from collections import deque
from pathlib import Path

import arc3_priority_probe as P
import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F
from test_arc3_multilevel_transfer import SequenceWorld, source_fixture


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, _, cls.compositional, cls.multilevel = T.load_frozen(os.environ['MSI_FROZEN_DIR'])

    @staticmethod
    def approve(identity, outcomes, evidence_sha, output):
        return {'identity': identity, 'source_sha256': evidence_sha,
                'marker': 'TEST_ONLY_GATE=' + identity}

    def run_world(self, gate=None, **kwargs):
        return P.run(SequenceWorld, (0, 1, 2), source_fixture(),
                     self.compositional.OptionSearch, self.multilevel.execute_stage,
                     Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'msi-priority-tests',
                     gate=gate if gate is not None else self.approve, **kwargs)

    def test_previous_residual_is_search_starvation_not_impossibility(self):
        path = os.environ.get('MSI_PREVIOUS_EVIDENCE')
        if not path:
            self.skipTest('Previous artifact not supplied')
        r = json.loads(Path(path).read_text())
        self.assertEqual(r['status'], 'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(r['levels_witnessed'], 1)
        self.assertEqual(len(r['evidence']), 505)
        self.assertEqual({len(e['suffix']) for e in r['evidence']}, {1, 2})
        self.assertTrue(all(e['progress'] == 0 for e in r['evidence']))

    def test_existing_options_precede_primitives_without_removing_them(self):
        option = (9, 9, 9)
        class Search:
            max_depth = 12
            options = (option,)
            frontier = deque([(0,), (1,), option, option * 2, (2,), option * 4])
        s = Search()
        before = list(s.frontier)
        P.option_priority(s)
        self.assertEqual(list(s.frontier)[:3], [option, option * 2, option * 4])
        self.assertEqual(list(s.frontier)[3:], [(0,), (1,), (2,)])
        self.assertEqual(set(s.frontier), set(before))
        self.assertEqual(len(s.frontier), len(before))

    def test_second_capability_is_acquired_and_deployed(self):
        r = self.run_world()
        self.assertEqual(r['status'], 'VERIFIED_WIN')
        self.assertEqual(r['warm']['state'], 'WIN')
        self.assertEqual(r['warm']['levels_completed'], 2)
        self.assertEqual(r['warm']['actions'], 8)
        self.assertEqual(len(r['accepted']), 2)
        self.assertEqual(r['accepted'][1]['suffix'], (2, 2, 2, 2))
        self.assertLessEqual(r['training_actions'], 3000)
        self.assertGreaterEqual(r['installed_options'], 2)

    def test_rejected_promotion_preserves_prior_capability(self):
        calls = []
        def reject(identity, outcomes, evidence_sha, output):
            calls.append(identity)
            result = self.approve(identity, outcomes, evidence_sha, output)
            if len(calls) == 2:
                result['identity'] = 'forged'
            return result
        r = self.run_world(gate=reject)
        self.assertEqual(r['status'], 'INCONCLUSIVE_VERIFIER')
        self.assertEqual(r['warm']['levels_completed'], 1)
        self.assertEqual(len(r['accepted']), 1)
        self.assertEqual(r['installed_options'], 1)
        self.assertFalse(r['terminal_win'])

    def test_unfunded_replay_is_refused(self):
        r = self.run_world(max_training_actions=15)
        self.assertEqual(r['status'], 'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(r['training_actions'], 15)
        self.assertEqual(r['installed_options'], 0)
        self.assertFalse(r['terminal_win'])

    def test_original_scheduler_is_restored(self):
        original = M.order_frontier
        self.run_world(max_training_actions=15)
        self.assertIs(M.order_frontier, original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
