"""Constructed verifier tests; no ARC result is asserted here."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from agent import observation
from finite_consequence import digest
from terminal_confirmation import confirm

class Finalize:
    def __init__(self,win=True,actual_levels=3,reported_levels=3):
        self.level=0;self.done=False;self.win=win
        self.actual_levels=actual_levels;self.reported_levels=reported_levels
    @property
    def observation_space(self):
        return {'frame':[[[self.level]]],'levels_completed':self.level,
                'state':'WIN' if self.done else 'NOT_FINISHED','available_actions':[0,1]}
    def reset(self):return self.observation_space
    def step(self,a):
        if self.level<self.actual_levels and a==1:self.level+=1
        elif self.level==self.actual_levels and a==1 and self.win:self.done=True
        return self.observation_space
    def close(self):return {'score':100.0 if self.level>=self.reported_levels else 0.0,
                            'total_levels':self.reported_levels,'completed':self.done}


def checkpoint(prefix,win=True,actual_levels=3,reported_levels=3):
    e=Finalize(win,actual_levels,reported_levels)
    for a in prefix:e.step(a)
    return digest(observation(e.observation_space))

class TerminalConfirmationTests(unittest.TestCase):
    def test_progress_is_not_a_terminal_certificate(self):
        r=confirm(Finalize,(0,1),(1,)*3,3,checkpoint((1,)*3),checkpoint(()),
                  budget=10,max_training_actions=100,max_episodes=10,max_depth=2)
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['program'],(1,)*4)
        self.assertEqual(r['result']['state'],'WIN')
        self.assertEqual(r['result']['actions'],4)
        self.assertGreater(r['training_actions'],4)

    def test_score_without_terminal_is_not_promoted(self):
        r=confirm(lambda:Finalize(False),(0,1),(1,)*3,3,checkpoint((1,)*3,False),checkpoint((),False),
                  budget=10,max_training_actions=100,max_episodes=10,max_depth=2)
        self.assertEqual(r['status'],'NO_TERMINAL_WITHIN_BOUND')
        self.assertEqual(r['retained_prefix'],(1,)*3)

    def test_wrong_checkpoint_is_inconclusive(self):
        r=confirm(Finalize,(0,1),(1,)*3,3,'wrong',checkpoint(()),budget=10)
        self.assertEqual(r['status'],'INCONCLUSIVE_PREFIX_MISMATCH')

    def test_nonfinal_prefix_continues_to_win(self):
        r=confirm(Finalize,(0,1),(1,1),2,checkpoint((1,1)),checkpoint(()),budget=10)
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['program'],(1,)*4)
        self.assertEqual(r['levels_witnessed'],3)

    def test_reported_level_count_is_not_a_stopping_rule(self):
        factory=lambda:Finalize(actual_levels=5,reported_levels=3)
        r=confirm(factory,(0,1),(1,)*3,3,checkpoint((1,)*3,actual_levels=5),
                  checkpoint((),actual_levels=5),budget=12,max_training_actions=100,
                  max_episodes=20,max_depth=4,options=((1,1),))
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['program'],(1,)*6)
        self.assertEqual(r['result']['levels_completed'],5)
        self.assertEqual(r['result']['state'],'WIN')
        self.assertTrue(any(s['level']>3 for s in r['stages']))

    def test_new_progress_is_retained_without_claiming_win(self):
        factory=lambda:Finalize(False,actual_levels=5,reported_levels=3)
        r=confirm(factory,(0,1),(1,)*3,3,checkpoint((1,)*3,False,5),
                  checkpoint((),False,5),budget=12,max_training_actions=100,
                  max_episodes=20,max_depth=4,options=((1,1),))
        self.assertEqual(r['status'],'NO_TERMINAL_WITHIN_BOUND')
        self.assertEqual(r['levels_witnessed'],5)
        self.assertEqual(r['retained_prefix'],(1,)*5)

if __name__=='__main__':unittest.main()
