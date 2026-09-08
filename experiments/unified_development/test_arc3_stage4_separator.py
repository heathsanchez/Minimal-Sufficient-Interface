"""Regression controls. A test-double gate is never evidence of a Lean result."""
import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import arc3_stage4_separator as S
import arc3_stage4_probe as P
import arc3_shared_transfer as T
import closed_feedback_v2 as F
from test_arc3_multilevel_transfer import source_fixture


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, _, _, cls.multilevel = T.load_frozen(os.environ['MSI_FROZEN_DIR'])
        cls.source = json.loads(Path(os.environ['MSI_SOURCE_EVIDENCE']).read_text())
        cls.report = json.loads(Path(os.environ['MSI_ARCHIVE_EVIDENCE']).read_text())
        cls.transfer = json.loads(Path(os.environ['MSI_TRANSFER_EVIDENCE']).read_text())
        cls.evidence = json.loads(Path(os.environ['MSI_STAGE_EVIDENCE']).read_text())
        cls.residual = json.loads(Path(os.environ['MSI_RESIDUAL_EVIDENCE']).read_text())
        cls.actions = tuple(dict.fromkeys(F.atom(a) for s in cls.report['policies'][cls.report['selected_policy']]['development']['stages'] for a in s['suffix']))

    def selected(self, residual=None):
        return S.separator_programs(self.source, self.report, self.transfer, self.evidence,
                                    self.residual if residual is None else residual, self.actions)

    def test_real_residual_selects_distinct_effects(self):
        representatives, programs = self.selected()
        entry = P.verified_entry(self.source, self.report, self.transfer, self.evidence, self.actions)
        allowed = set(self.actions) | set(P.component_actions(entry, entry['available_actions']))
        self.assertGreaterEqual(len(representatives), 2)
        self.assertLessEqual(len(representatives), 4)
        self.assertTrue(all(len(p) == 1 and p[0] in allowed for p in representatives))
        self.assertTrue(all(0 < len(p) <= 16 for p in programs))
        self.assertEqual(len(programs), len(set(programs)))
        self.assertTrue(all(p in programs for p in representatives))
        groups = {row['observed_hashes'][-1] for row in self.residual['diagnostic_rows'] if len(row['program']) == 1}
        self.assertGreaterEqual(len(groups), 2)

    def test_forged_residuals_refuse(self):
        for mutation in ('checkpoint', 'promotion', 'observation', 'hash', 'action', 'status'):
            bad = copy.deepcopy(self.residual)
            if mutation == 'checkpoint': bad['checkpoint_sha256'] = 'forged'
            elif mutation == 'promotion': bad['accepted'][-1]['promotion'] = 'forged'
            elif mutation == 'observation': bad['diagnostic_rows'][0]['observations'][-1]['levels_completed'] = 99
            elif mutation == 'hash': bad['diagnostic_rows'][0]['observed_hashes'][-1] = 'forged'
            elif mutation == 'action': bad['diagnostic_rows'][0]['program'] = [[6, -1, -1]]
            else: bad['status'] = 'VERIFIED_WIN'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.selected(bad)

    def test_search_preserves_archive_and_changes_only_on_new_effect(self):
        stages = self.report['policies'][self.report['selected_policy']]['development']['stages']
        representatives, programs = self.selected()
        search = S.separator_search(stages, programs, representatives)
        first = tuple(map(F.atom, stages[0]['suffix']))
        second = tuple(map(F.atom, stages[1]['suffix']))
        third = tuple(map(F.atom, stages[2]['suffix']))
        self.assertEqual(search(self.actions, [], max_depth=16).propose(), first)
        self.assertEqual(search(self.actions, [first], max_depth=16).propose(), second)
        self.assertEqual(search(self.actions, [first, second], max_depth=16).propose(), third)
        s = search(self.actions, [first, second, third], max_depth=16)
        self.assertEqual(s.propose(), programs[0])
        before = {'frame': [[[0]]], 'state': 'NOT_FINISHED'}
        after = {'frame': [[[1]]], 'state': 'NOT_FINISHED'}
        row = {'progress': 0, 'terminal': False, 'executed': representatives[0],
               'suffix_observations': [before, after]}
        self.assertEqual(s.retain(representatives[0], row), 'NONTERMINAL_PREFIX')
        self.assertEqual(s.propose(), representatives[0]*2)
        n = len(s.frontier)
        self.assertEqual(s.retain(representatives[0], row), 'NONTERMINAL_PREFIX')
        self.assertEqual(len(s.frontier), n)
        unchanged = dict(row, suffix_observations=[before, before])
        self.assertEqual(s.retain(representatives[0], unchanged), 'NONTERMINAL_PREFIX')
        self.assertEqual(len(s.frontier), n)
        self.assertEqual(s.retain(representatives[0], {'progress':0,'terminal':False,'executed':representatives[0]}), 'INCONCLUSIVE')

    def test_synthetic_fourth_capability_uses_existing_gate(self):
        class World:
            def __init__(self):
                self.level=0; self.run=0; self.observation_space=self.frame()
            def frame(self):
                return {'frame':[[[self.level,self.run]]],'levels_completed':self.level,
                        'state':'WIN' if self.level==4 else 'NOT_FINISHED','available_actions':[0,1,2,3]}
            def reset(self):
                self.level=0;self.run=0;return self.frame()
            def step(self,a):
                self.run=self.run+1 if a==(self.level+1)%4 else 0
                if self.run==4:self.level+=1;self.run=0
                return self.frame()
            def close(self):return None
        source=source_fixture()
        stages=[];prefix=()
        for level,action in enumerate((1,2,3),1):
            suffix=(action,)*4;prefix+=suffix
            proof=F.replay(World,prefix,None,120)
            stages.append({'level':level,'prefix':list(prefix),'suffix':list(suffix),
                           'checkpoint_sha256':proof['final_sha256']})
        source['initial_sha256']=F.replay(World,(),None,120)['initial_sha256']
        source['source_development']['stages']=[stages[0]]
        source['source_development']['prefix']=stages[0]['prefix']
        report={'status':'COMPARABLE','model_calls':0,'competition_submission':False,
                'game':'bt33-a7c3f9d18b4e','initial_sha256':source['initial_sha256'],
                'selected_policy':'test','policies':{'test':{'status':'COMPARABLE',
                'development':{'initial_sha256':source['initial_sha256'],'stages':stages},
                'warm':{'executed':list(prefix),'final_sha256':stages[-1]['checkpoint_sha256'],
                        'levels_completed':3,'state':'NOT_FINISHED','actions':12}}}}
        transfer={'warm':report['policies']['test']['warm']}
        gate=lambda identity,outcomes,evidence_sha,output:{'identity':identity,'source_sha256':evidence_sha,'marker':'TEST_ONLY'}
        with patch.object(S,'separator_programs',return_value=(((0,),),((0,),(0,)*2,(0,)*4))):
            r=S.run(World,(0,1,2,3),source,report,transfer,{}, {},self.multilevel.execute_stage,
                    Path(os.environ.get('RUNNER_TEMP','/tmp'))/'msi-separator-tests',gate=gate)
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['warm']['levels_completed'],4)
        self.assertEqual(r['accepted'][-1]['suffix'],(0,)*4)
        self.assertEqual(r['new_discoveries'],1)
        self.assertTrue(r['improved_over_archive'])
        self.assertLessEqual(r['training_actions'],1200)


if __name__=='__main__':unittest.main(verbosity=2)
