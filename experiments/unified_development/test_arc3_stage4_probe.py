"""Source-blind controls. The injected gate is a test double, never Lean."""
import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import arc3_stage4_probe as P
import arc3_shared_transfer as T
import closed_feedback_v2 as F
from test_arc3_multilevel_transfer import SequenceWorld, source_fixture
from test_arc3_archive_transfer import example_report


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,_,_,_,cls.multilevel=T.load_frozen(os.environ['MSI_FROZEN_DIR'])

    @staticmethod
    def approve(identity,outcomes,evidence_sha,output):
        return {'identity':identity,'source_sha256':evidence_sha,
                'marker':'TEST_ONLY_GATE='+identity}

    def test_real_archive_entry_and_generated_coordinates(self):
        source=json.loads(Path(os.environ['MSI_SOURCE_EVIDENCE']).read_text())
        report=json.loads(Path(os.environ['MSI_ARCHIVE_EVIDENCE']).read_text())
        transfer=json.loads(Path(os.environ['MSI_TRANSFER_EVIDENCE']).read_text())
        evidence=json.loads(Path(os.environ['MSI_STAGE_EVIDENCE']).read_text())
        stages=report['policies'][report['selected_policy']]['development']['stages']
        actions=tuple(dict.fromkeys(F.atom(a) for s in stages for a in s['suffix']))
        entry=P.verified_entry(source,report,transfer,evidence,actions)
        self.assertEqual(F.digest(entry),transfer['checkpoint_sha256'])
        candidates=P.component_actions(entry,entry['available_actions'])
        self.assertTrue(candidates)
        self.assertLessEqual(len(candidates),48)
        self.assertTrue(all(a[0]==6 and 0<=a[1]<64 and 0<=a[2]<64 for a in candidates))
        self.assertEqual(P.component_actions(entry,[]),())
        for mutation in ('checkpoint','promotion','proof'):
            bad=copy.deepcopy(transfer)
            altered=copy.deepcopy(evidence)
            if mutation=='checkpoint':bad['checkpoint_sha256']='forged'
            elif mutation=='promotion':bad['accepted'][-1]['promotion']='forged'
            else:altered['proof']['observations'][-1]['levels_completed']=99
            with self.assertRaises(ValueError):
                P.verified_entry(source,report,bad,altered,actions)

    def test_coordinate_grammar_uses_pixels_not_target_labels(self):
        frame={'frame':[[[0,0,0,0],[0,2,2,0],[0,2,2,0],[0,0,0,0]]],
               'available_actions':[6]}
        candidates=P.component_actions(frame,[6])
        self.assertTrue(candidates)
        self.assertTrue(all(0<=a[1]<4 and 0<=a[2]<4 for a in candidates))
        self.assertEqual(P.component_actions(frame,[1]),())
        self.assertEqual(P.component_actions({'frame':[]},[6]),())

    def test_observation_capture_and_repetition_repair(self):
        source=source_fixture()
        first=tuple(source['source_development']['prefix'])
        stage={'level':2,'prefix':first+(2,)*4,'suffix':(2,)*4}
        search=P.continuation_search([source['source_development']['stages'][0],stage],(0,),(0,1,2))
        s=search((0,1,2),[first],max_depth=16)
        self.assertEqual(s.propose(),(2,)*4)
        s=search((0,1,2),[first,(2,)*4],max_depth=16)
        self.assertEqual(s.propose(),(0,))
        execute=P.observed_stage(self.multilevel.execute_stage)
        result=execute(SequenceWorld(),first,(0,),1,120,source['source_development']['stages'][0]['checkpoint_sha256'])
        self.assertEqual(len(result['suffix_observations']),2)
        local=dict(result,executed=(0,),actions=1)
        self.assertEqual(s.retain((0,),local),'NONTERMINAL_PREFIX')
        self.assertEqual(s.propose(),(0,0))
        changed=dict(local,suffix_observations=[{'frame':[[0]],'state':'NOT_FINISHED'},
                                                 {'frame':[[1]],'state':'NOT_FINISHED'}])
        s=search((0,1,2),[first,(2,)*4],max_depth=16)
        self.assertEqual(s.retain((0,),changed),'NONTERMINAL_PREFIX')
        self.assertEqual(s.propose(),(0,0))
        self.assertEqual(s.propose(),(0,)*4)

    def test_actual_controller_acquires_fourth_capability(self):
        class FourLevelWorld:
            def __init__(self):
                self.level=0;self.run=0;self.observation_space=self.frame()
            def frame(self):
                return {'frame':[[[self.level,self.run]]], 'levels_completed':self.level,
                        'state':'WIN' if self.level==4 else 'NOT_FINISHED',
                        'available_actions':[0,1,2,3]}
            def reset(self):
                self.level=0;self.run=0;return self.frame()
            def step(self,a):
                self.run=self.run+1 if a==(self.level+1)%4 else 0
                if self.run==4:self.level+=1;self.run=0
                return self.frame()
            def close(self):return None
        first=(1,)*4
        source=source_fixture()
        stages=[];prefix=()
        for level,action in enumerate((1,2,3),1):
            suffix=(action,)*4;prefix+=suffix
            proof=F.replay(FourLevelWorld,prefix,None,120)
            stages.append({'level':level,'prefix':list(prefix),'suffix':list(suffix),
                           'checkpoint_sha256':proof['final_sha256']})
        source['initial_sha256']=F.replay(FourLevelWorld,(),None,120)['initial_sha256']
        source['source_development']['stages']=[stages[0]]
        source['source_development']['prefix']=stages[0]['prefix']
        report={'status':'COMPARABLE','model_calls':0,'competition_submission':False,
                'game':'bt33-a7c3f9d18b4e','initial_sha256':source['initial_sha256'],
                'selected_policy':'test','policies':{'test':{'status':'COMPARABLE',
                'development':{'initial_sha256':source['initial_sha256'],'stages':stages},
                'warm':{'executed':list(prefix),'final_sha256':stages[-1]['checkpoint_sha256'],
                        'levels_completed':3,'state':'NOT_FINISHED','actions':12}}}}
        transfer={'warm':report['policies']['test']['warm']}
        with patch.object(P,'verified_entry',return_value=FourLevelWorld().frame()),\
             patch.object(P,'component_actions',return_value=(0,)):
            r=P.run(FourLevelWorld,(0,1,2,3),source,report,transfer,{},
                    self.multilevel.execute_stage,Path(os.environ.get('RUNNER_TEMP','/tmp'))/'msi-stage4-tests',
                    max_training_actions=1200,gate=self.approve)
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['warm']['state'],'WIN')
        self.assertEqual(r['warm']['levels_completed'],4)
        self.assertEqual(r['accepted'][-1]['suffix'],(0,)*4)
        self.assertEqual(r['new_discoveries'],1)
        self.assertTrue(r['improved_over_archive'])


if __name__=='__main__':unittest.main(verbosity=2)
