import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

class Ranked:
    def __init__(self, actions, options=(), max_depth=32):
        self.rank={a:i for i,a in enumerate(actions)}
        self.max_depth=max_depth
        self.options=tuple(options)
        self.frontier=[]
    def _add(self, program, cost):
        self.frontier.append((cost,tuple(program)))
    def propose(self):
        if not self.frontier:return None
        self.frontier.sort(key=lambda x:(x[0],len(x[1])))
        return self.frontier.pop(0)[1]

class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_c=types.ModuleType('arc3_shared_continuation')
        fake_c.atoms=lambda p:tuple(tuple(a) if isinstance(a,list) else a for a in p)
        fake_t=types.ModuleType('arc3_shared_transfer')
        fake_t.run_lean_gate=lambda *args:None
        with patch.dict(sys.modules,{'arc3_shared_continuation':fake_c,'arc3_shared_transfer':fake_t}):
            spec=importlib.util.spec_from_file_location('arc3_shared_recovery',Path(__file__).with_name('arc3_shared_recovery.py'))
            cls.R=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.R)
    def setUp(self):
        self.a=(0,);self.b=(1,);self.c=(2,)
        self.witnesses=((self.a,), (self.a,self.b), (self.a,self.b,self.c))
    def source(self):
        stages=[];previous=()
        for i,p in enumerate(self.witnesses,1):
            stages.append({'level':i,'prefix':p,'suffix':p[len(previous):],'actions':len(p)})
            previous=p
        return {'status':'COMPARABLE','game':'test','initial_sha256':'initial',
                'selected_policy':'ranked-factor-v1','model_calls':0,'competition_submission':False,
                'policies':{'ranked-factor-v1':{'development':{'initial_sha256':'initial',
                'stages':stages,'prefix':previous,'levels_witnessed':len(stages)}}}}
    def load(self,source,game='test',initial='initial',actions=None):
        if actions is None:actions=self.witnesses[-1]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'evidence.json';raw=json.dumps(source).encode();p.write_bytes(raw)
            with patch.object(self.R,'SOURCE_SHA256',hashlib.sha256(raw).hexdigest()):
                return self.R.load_witnesses(p,game,initial,actions)
    def test_pinned_source_and_initial_identity(self):
        self.assertEqual(self.load(self.source()),self.witnesses)
        with self.assertRaises(ValueError):self.load(self.source(),initial='wrong')
        s=self.source();s['policies']['ranked-factor-v1']['development']['initial_sha256']='wrong'
        with self.assertRaises(ValueError):self.load(s)
    def test_rejects_unpermitted_and_malformed_witnesses(self):
        with self.assertRaises(ValueError):self.load(self.source(),actions=(self.a,self.b))
        s=self.source();s['policies']['ranked-factor-v1']['development']['stages'][1]['suffix']=(self.c,)
        with self.assertRaises(ValueError):self.load(s)
    def test_wrong_source_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{}')
            with self.assertRaises(ValueError):self.R.load_witnesses(p,'test','initial',())
    def test_matching_entry_is_prioritized_then_fallback_remains(self):
        Search=self.R.make_search_class(self.witnesses,Ranked,lambda p,b:(p,) if len(p)>1 else ())
        s=Search((self.a,self.b,self.c),(self.a,),max_depth=3)
        self.assertEqual(s.recovery_candidates,[(self.b,),(self.b,self.c)])
        self.assertEqual(s.propose(),(self.b,))
        self.assertEqual(s.propose(),(self.b,self.c))
        s2=Search((self.a,self.b,self.c),((self.a,),(self.b,)),max_depth=3)
        self.assertEqual(s2.recovery_candidates,[(self.c,)])
        self.assertEqual(s2.propose(),(self.c,))
        s3=Search((self.a,self.b,self.c),((self.c,),),max_depth=3)
        self.assertEqual(s3.recovery_candidates,[])
        self.assertEqual(s3.options,((self.c,),))
    def test_recovery_does_not_install_or_claim_effects(self):
        Search=self.R.make_search_class(self.witnesses,Ranked,lambda p,b:())
        s=Search((self.a,self.b,self.c),(self.a,),max_depth=3)
        self.assertFalse(hasattr(s,'archive'))
        self.assertTrue(all(a in s.rank for _,p in s.frontier for a in p))
        self.assertEqual(s.max_depth,3)

if __name__=='__main__':unittest.main()
