"""Source-blind regression worlds for the shared continuation boundary."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

class Archive:
    def __init__(self): self.options=[]
    def install(self,entry,program,target,proof,entry_path=(),source=None,dependencies=()):
        if (proof['final_sha256']!=target or proof['observations'][len(entry_path)]['id']!=entry
                or tuple(proof['executed'])!=tuple(entry_path)+tuple(program)):
            raise ValueError('Unverified operation')
        item=dict(entry_sha256=entry,program=tuple(program),target_sha256=target,
                  entry_path=tuple(entry_path),source=source,dependencies=dependencies)
        self.options.append(item)
        return item
    def snapshot(self): return {'options':len(self.options),'installed_options':self.options}

class World:
    def __init__(self,n=3):
        self.n=n;self.position=0;self.observation_space=self.observe()
    def observe(self):
        return {'id':str(self.position),'levels_completed':self.position,
                'state':'WIN' if self.position==self.n else 'NOT_FINISHED'}
    def close(self): pass

def replay(factory,path,expected,budget):
    world=factory();observations=[world.observe()];executed=[]
    for a in path:
        if len(executed)>=budget or world.position==world.n:break
        world.position+=1 if a==0 else 0
        executed.append(a);observations.append(world.observe())
    final=observations[-1]
    return dict(status='OBSERVED' if expected is None or expected==final['id'] else 'INCONCLUSIVE_PREFIX_MISMATCH',
                initial_sha256='0',final_sha256=final['id'],observations=observations,
                executed=tuple(executed),actions=len(executed),
                levels_completed=final['levels_completed'],state=final['state'])

def execute_stage(world,prefix,suffix,target,budget,checkpoint=None,stop_at_progress=True):
    r=replay(lambda:world,tuple(prefix)+tuple(suffix),None,budget)
    if checkpoint is not None and r['observations'][len(prefix)]['id']!=checkpoint:
        r['status']='INCONCLUSIVE_PREFIX_MISMATCH'
    else:r['status']='PROGRESS_WITNESSED' if r['levels_completed']>target else 'OBSERVED'
    r.update(progress=max(0,r['levels_completed']-target),terminal=r['state']=='WIN',
             trace_sha256='trace-'+r['final_sha256'])
    return r

class Search:
    observed_options=[]
    def __init__(self,actions,options=(),max_depth=32):
        self.observed_options.append(tuple(options))
        self.queue=list(options)+[(a,) for a in actions]
    def propose(self):return self.queue.pop(0) if self.queue else None
    def retain(self,program,result):return 'PROGRESS_WITNESSED' if result['progress'] else 'NONTERMINAL_PREFIX'

class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake=types.ModuleType('arc3_shared_transfer')
        cls.fake.FROZEN='frozen';cls.fake.UPSTREAM='upstream';cls.fake.SOURCE_BLOBS={'source':'pin'}
        cls.fake.digest=lambda x:x['id'] if isinstance(x,dict) and 'id' in x else json.dumps(x,sort_keys=True,default=str)
        cls.fake.F=types.SimpleNamespace(atom=lambda x:tuple(x) if isinstance(x,list) else x,
                                         FeedbackArchive=Archive,replay=replay)
        cls.fake.quality=lambda r:(r['state']=='WIN',r['levels_completed'],-r['actions'])
        cls.fake.run_lean_gate=lambda identity,outcomes,evidence_sha,output:{'identity':identity}
        def promote(factory,prefix,stage,cold,initial,archive,output,gate):
            first=replay(factory,prefix,None,120);proof=replay(factory,prefix,first['final_sha256'],120)
            if (proof['initial_sha256']!=initial or proof['final_sha256']!=stage['checkpoint_sha256']
                    or tuple(prefix)!=tuple(stage['prefix']) or proof['levels_completed']!=stage['level']):
                return {'status':'INCONCLUSIVE_REPLAY'}
            if proof['levels_completed']<=cold['levels_completed']:return {'status':'NO_MEASURED_IMPROVEMENT'}
            evidence=dict(initial_sha256=initial,program=tuple(prefix),cold=cold,replay=first,proof=proof,source_commit='frozen')
            es=cls.fake.digest(evidence)
            identity=cls.fake.digest(dict(kind='arc3_witnessed_policy',evidence_sha256=es,program=tuple(prefix),source_commit='frozen'))
            approval=gate(identity,[cold,proof],es,output)
            if approval['identity']!=identity:raise ValueError('Gate identity mismatch')
            archive.install(initial,tuple(prefix),proof['final_sha256'],proof,source=('policy',identity))
            return dict(status='REPLAY_GATED_PROMOTION_PASS',identity=identity,evidence_sha256=es,
                        evidence=evidence,approval=approval,replay_actions=2*len(prefix))
        cls.fake.promote=promote
        with patch.dict(sys.modules,{'arc3_shared_transfer':cls.fake}):
            spec=importlib.util.spec_from_file_location('arc3_shared_continuation',Path(__file__).with_name('arc3_shared_continuation.py'))
            cls.C=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.C)
    def setUp(self):
        Search.observed_options=[];self.factory=lambda:World(3)
        cold={'initial_sha256':'0','final_sha256':'0','levels_completed':0,'state':'GAME_OVER','actions':1}
        stage={'level':1,'prefix':(0,),'checkpoint_sha256':'1'}
        p=self.fake.promote(self.factory,(0,),stage,cold,'0',Archive(),Path('.'),self.fake.run_lean_gate)
        self.source=dict(status='COMPARABLE',game='test',source_commit='frozen',upstream_commit='upstream',
                         source_blobs={'source':'pin'},initial_sha256='0',cold=cold,promotion=p,
                         source_development={'prefix':(0,),'stages':[stage]})
        self.identity=p['identity']
    def run_cycle(self,**kw):
        with tempfile.TemporaryDirectory() as d:
            return self.C.continue_run(self.factory,(0,),self.source,'test',self.identity,d,
                    search_class=Search,execute_stage=execute_stage,gate=kw.pop('gate',self.fake.run_lean_gate),**kw)
    def test_reuse_is_certified_before_next_search(self):
        calls=[]
        def gate(identity,outcomes,evidence_sha,output):
            calls.append(identity);return {'identity':identity}
        r=self.run_cycle(gate=gate,max_levels=3)
        self.assertEqual(r['status'],'VERIFIED_WIN');self.assertEqual(len(r['stages']),3)
        self.assertEqual(r['archive']['options'],3);self.assertEqual(len(calls),3)
        self.assertEqual(Search.observed_options[0],((0,),))
        self.assertEqual(Search.observed_options[1],((0,),(0,)))
        self.assertEqual(r['archive']['installed_options'][1]['entry_path'],(0,))
        self.assertEqual(r['archive']['installed_options'][2]['entry_path'],(0,0))
    def test_rejected_gate_cannot_install_or_advance(self):
        calls=[]
        def gate(identity,outcomes,evidence_sha,output):
            calls.append(identity)
            if len(calls)==2:raise ValueError('Rejected')
            return {'identity':identity}
        r=self.run_cycle(gate=gate)
        self.assertEqual(r['status'],'INCONCLUSIVE_VERIFIER')
        self.assertEqual(r['archive']['options'],1);self.assertEqual(r['prefix'],(0,))
    def test_source_tampering_is_rejected(self):
        self.source['promotion']['identity']='forged'
        with self.assertRaises(ValueError):self.run_cycle()
    def test_budget_preserves_last_certified_capability(self):
        r=self.run_cycle(max_training_actions=6)
        self.assertEqual(r['status'],'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(r['archive']['options'],1);self.assertEqual(r['prefix'],(0,))
        self.assertLessEqual(r['training_actions'],6)
    def test_unmatched_initial_state_is_not_promoted(self):
        self.source['initial_sha256']='other';self.source['promotion']['evidence']['initial_sha256']='other'
        with self.assertRaises(ValueError):self.run_cycle()

if __name__=='__main__':unittest.main()
