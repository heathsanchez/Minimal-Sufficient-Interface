"""Archive transfer controls use the actual frozen controller and a test gate."""
import copy
import json
import os
import unittest
from pathlib import Path

import arc3_archive_transfer as A
import arc3_shared_transfer as T
import closed_feedback_v2 as F
from test_arc3_multilevel_transfer import SequenceWorld, source_fixture


def example_report(source):
    first = (1,) * 4
    full = first + (2,) * 4
    proof = F.replay(SequenceWorld, full, None, 120)
    stages = [source['source_development']['stages'][0],
              {'level': 2, 'prefix': list(full), 'suffix': [2]*4,
               'checkpoint_sha256': proof['final_sha256']}]
    return {'status':'COMPARABLE','model_calls':0,'competition_submission':False,
            'game':'bt33-a7c3f9d18b4e','initial_sha256':source['initial_sha256'],
            'selected_policy':'test','policies':{'test':{'status':'COMPARABLE',
            'development':{'initial_sha256':source['initial_sha256'],'stages':stages,
                           'training_actions':12,'training_episodes':2},
            'warm':{'executed':list(full),'final_sha256':proof['final_sha256'],
                    'levels_completed':2,'state':'WIN','actions':8}}}}


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, _, cls.compositional, cls.multilevel = T.load_frozen(os.environ['MSI_FROZEN_DIR'])

    @staticmethod
    def approve(identity, outcomes, evidence_sha, output):
        return {'identity':identity,'source_sha256':evidence_sha,
                'marker':'TEST_ONLY_GATE='+identity}

    def run_world(self, source=None, report=None, gate=None, **kwargs):
        source = source if source is not None else source_fixture()
        report = report if report is not None else example_report(source)
        return A.run(SequenceWorld,(0,1,2),source,report,self.multilevel.execute_stage,
                     Path(os.environ.get('RUNNER_TEMP','/tmp'))/'msi-archive-tests',
                     gate=gate if gate is not None else self.approve,**kwargs)

    def test_archive_acquires_second_capability_through_existing_gate(self):
        r=self.run_world()
        self.assertEqual(r['status'],'ALL_LEVELS_WITNESSED')
        self.assertEqual(r['warm']['state'],'WIN')
        self.assertEqual(r['warm']['actions'],8)
        self.assertEqual(len(r['accepted']),2)
        self.assertEqual(r['accepted'][1]['suffix'],(2,2,2,2))
        self.assertGreaterEqual(r['installed_options'],2)
        self.assertLessEqual(r['training_actions'],160)
        self.assertEqual(r['new_discoveries'],0)

    def test_rejected_second_promotion_preserves_first(self):
        calls=[]
        def gate(identity,outcomes,evidence_sha,output):
            calls.append(identity)
            result=self.approve(identity,outcomes,evidence_sha,output)
            if len(calls)==2:result['identity']='forged'
            return result
        r=self.run_world(gate=gate)
        self.assertEqual(r['status'],'INCONCLUSIVE_VERIFIER')
        self.assertEqual(r['warm']['levels_completed'],1)
        self.assertEqual(len(r['accepted']),1)
        self.assertFalse(r['terminal_win'])

    def test_malformed_archive_and_missing_source_refused(self):
        source=source_fixture(); report=example_report(source)
        bad=copy.deepcopy(report);bad['initial_sha256']='forged'
        with self.assertRaises(ValueError):A.select_archive(bad,source,(0,1,2))
        bad=copy.deepcopy(report);bad['policies']['test']['development']['stages'][1]['prefix']=[2]*4
        with self.assertRaises(ValueError):A.select_archive(bad,source,(0,1,2))
        bad=copy.deepcopy(report);bad['policies']['test']['development']['stages'][1]['suffix']=[9]*4
        with self.assertRaises(ValueError):A.select_archive(bad,source,(0,1,2))
        bad=copy.deepcopy(report);bad['policies']['test']['warm']['final_sha256']='forged'
        with self.assertRaises(ValueError):A.select_archive(bad,source,(0,1,2))
        bad=copy.deepcopy(report);bad['status']='PENDING'
        with self.assertRaises(ValueError):A.select_archive(bad,source,(0,1,2))

    def test_bound_refuses_unfunded_replay(self):
        r=self.run_world(max_training_actions=15)
        self.assertEqual(r['status'],'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(r['training_actions'],15)
        self.assertEqual(r['installed_options'],0)

    def test_pinned_real_archive_is_structurally_consistent(self):
        source=json.loads(Path(os.environ['MSI_SOURCE_EVIDENCE']).read_text())
        report=json.loads(Path(os.environ['MSI_ARCHIVE_EVIDENCE']).read_text())
        stages=report['policies'][report['selected_policy']]['development']['stages']
        alphabet=tuple(dict.fromkeys(F.atom(a) for s in stages for a in s['suffix']))
        selected=A.select_archive(report,source,alphabet)
        self.assertEqual(len(selected),3)
        self.assertEqual([len(s['prefix']) for s in selected],[4,12,28])
        self.assertEqual(report['policies'][report['selected_policy']]['warm']['state'],'NOT_FINISHED')

if __name__=='__main__':
    unittest.main(verbosity=2)
