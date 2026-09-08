import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from consequence_quotient import measure, discover, compare

class HiddenPhase:
    """Constructed adversary: one-step equivalence hides a useful sequence."""
    def __init__(self): self.phase=0; self.level=0
    @property
    def observation_space(self):
        return {'frame':[[[0]]], 'levels_completed':self.level,
                'state':'NOT_FINISHED', 'available_actions':[0,1,2]}
    def reset(self):return self.observation_space
    def step(self,a):
        if a==1:self.phase=1
        elif a==2 and self.phase==1:self.level=1
        return self.observation_space
    def close(self):return {'score':self.level}

class TwoLevels:
    def __init__(self):self.level=0
    @property
    def observation_space(self):
        return {'frame':[[[self.level]]], 'levels_completed':self.level,
                'state':'NOT_FINISHED', 'available_actions':[0,1]}
    def reset(self):return self.observation_space
    def step(self,a):
        if self.level==a:self.level+=1
        return self.observation_space
    def close(self):return {'score':self.level}

class QuotientTests(unittest.TestCase):
    def test_observed_equivalence_not_universal(self):
        q=measure(HiddenPhase,(0,1,2),(),0,None,10,horizon=1)
        self.assertEqual(q['status'],'OBSERVED_QUOTIENT')
        self.assertEqual(len(q['classes']),1)
    def test_full_alphabet_reopens_hidden_distinction(self):
        d,qs=discover(HiddenPhase,(0,1,2),budget=10,max_depth=2,
                      max_training_actions=100,max_episodes=100,max_levels=1,horizon=1)
        self.assertEqual(d.status,'ALL_LEVELS_WITNESSED')
        self.assertEqual(d.prefix,(1,2))
        self.assertTrue(any(e['alphabet']=='full' for e in d.evidence))
        self.assertEqual(len(qs[0]['classes']),1)
    def test_new_checkpoint_gets_new_quotient(self):
        d,qs=discover(TwoLevels,(0,1),budget=10,max_depth=2,
                      max_training_actions=100,max_episodes=100,max_levels=2,horizon=1)
        self.assertEqual(d.status,'ALL_LEVELS_WITNESSED')
        self.assertEqual(d.prefix,(0,1))
        self.assertEqual(len(qs),2)
        self.assertNotEqual(qs[0]['evidence_sha256'],qs[1]['evidence_sha256'])
    def test_bound_cannot_promote(self):
        d,qs=discover(HiddenPhase,(0,1,2),budget=10,max_depth=2,
                      max_training_actions=2,max_episodes=2,max_levels=1,horizon=1)
        self.assertEqual(d.status,'TRAINING_BOUND_EXHAUSTED')
        self.assertFalse(d.stages)
        self.assertEqual(qs,[])
    def test_fresh_deployment(self):
        r=compare(HiddenPhase,(0,1,2),budget=10,max_depth=2,
                  max_training_actions=100,max_episodes=100,max_levels=1,horizon=1)
        self.assertEqual(r['status'],'COMPARABLE')
        self.assertEqual(r['warm']['levels_completed'],1)
        self.assertTrue(r['improved'])

if __name__=='__main__':unittest.main()
