"""Synthetic controls only; these tests do not establish a real-game result."""
import unittest
from unittest.mock import patch
import arc3_delayed_separator as D
import closed_feedback_v2 as F

class World:
    def __init__(self, distinguish=True):
        self.distinguish=distinguish; self.phase=0; self.hidden=None
        self.observation_space=self.observe()
    def observe(self):
        value=(0,1,1,2,3 if self.hidden==1 or not self.distinguish else 4)[self.phase]
        return {'frame':[[[value]]], 'levels_completed':3 if self.phase else 0,
                'state':'NOT_FINISHED','available_actions':[0,1,2,3]}
    def reset(self):
        self.phase=0; self.hidden=None; return self.observe()
    def step(self,action):
        if self.phase<2:
            if action!=0: raise ValueError('Bad prefix')
            self.phase+=1
        elif self.phase==2:
            if action not in (1,2): raise ValueError('Bad probe')
            self.hidden=action; self.phase=3
        elif self.phase==3:
            if action!=3: raise ValueError('Bad continuation')
            self.phase=4
        else: raise ValueError('Unexpected extra action')
        return self.observe()
    def close(self): pass

class Tests(unittest.TestCase):
    def setUp(self):
        self.initial=F.digest(World().observe())
        self.checkpoint=F.digest({'frame':[[[1]]],'levels_completed':3,
                                  'state':'NOT_FINISHED','available_actions':[0,1,2,3]})
        self.immediate=F.digest({'frame':[[[2]]],'levels_completed':3,
                                 'state':'NOT_FINISHED','available_actions':[0,1,2,3]})
        self.kw=dict(prefix=(0,0),checkpoint=self.checkpoint,
                     groups=((self.immediate,(1,2)),),contexts=((3,),),
                     initial_sha256=self.initial,max_actions=40,max_episodes=10)
    def test_delayed_collision_requires_common_context(self):
        r=D.experiment(World,**self.kw)
        self.assertEqual(r['status'],'REPLAY_CONFIRMED_SEPARATOR')
        self.assertEqual(r['witnesses'][0]['first_divergence'],2)
        self.assertEqual((r['training_actions'],r['training_episodes']),(16,4))
    def test_same_future_is_only_bounded_negative(self):
        r=D.experiment(lambda:World(False),**self.kw)
        self.assertEqual(r['status'],'NO_SEPARATOR_WITHIN_BOUND')
        self.assertEqual(r['witnesses'],[])
        self.assertEqual(r['training_actions'],8)
    def test_initial_hash_is_protected(self):
        r=D.experiment(World,**dict(self.kw,initial_sha256='forged'))
        self.assertEqual(r['status'],'INCONCLUSIVE_REPLAY')
        self.assertEqual(r['training_actions'],4)
    def test_incomplete_pair_is_not_started(self):
        r=D.experiment(World,**dict(self.kw,max_actions=15))
        self.assertEqual(r['status'],'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual((r['training_actions'],r['attempted_pairs']),(0,0))
    def test_historical_budget_is_charged(self):
        r=D.experiment(World,**dict(self.kw,initial_actions=5,initial_episodes=1,
                                     max_actions=21,max_episodes=5))
        self.assertEqual(r['status'],'REPLAY_CONFIRMED_SEPARATOR')
        self.assertEqual((r['training_actions'],r['diagnostic_actions']),(21,16))
    def test_confirmation_mismatch_is_inconclusive(self):
        calls=[0]; original=F.replay
        def replay(factory,path,expected,budget):
            calls[0]+=1; world=factory()
            if calls[0]==4: world.distinguish=False
            return original(lambda:world,path,expected,budget)
        with patch.object(D.F,'replay',side_effect=replay):
            r=D.experiment(World,**self.kw)
        self.assertEqual(r['status'],'INCONCLUSIVE_CONFIRMATION')
        self.assertEqual(r['witnesses'],[])
        self.assertEqual(r['training_actions'],16)
    def test_empty_context_is_not_evidence(self):
        r=D.experiment(World,**dict(self.kw,contexts=()))
        self.assertEqual((r['status'],r['attempted_pairs']),('NO_SEPARATOR_WITHIN_BOUND',0))
    def test_forged_residual_refused(self):
        before={'frame':[[[1]]],'levels_completed':3,'state':'NOT_FINISHED','available_actions':[0,1,2,3]}
        after={'frame':[[[2]]],'levels_completed':3,'state':'NOT_FINISHED','available_actions':[0,1,2,3]}
        row={'program':[1],'observations':[before,after],
             'observed_hashes':['forged',F.digest(after)],'changed':True}
        with self.assertRaises(ValueError):
            D.collision_groups({'diagnostic_rows':[row]},set((1,2,3)),self.checkpoint)

if __name__=='__main__': unittest.main(verbosity=2)
