"""Constructed verifier tests; no ARC result is asserted here."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from agent import observation
from finite_consequence import digest
from terminal_confirmation import confirm

class Finalize:
    def __init__(self,win=True):
        self.level=0;self.done=False;self.win=win
    @property
    def observation_space(self):
        return {'frame':[[[self.level]]],'levels_completed':self.level,
                'state':'WIN' if self.done else 'NOT_FINISHED','available_actions':[0,1]}
    def reset(self):return self.observation_space
    def step(self,a):
        if self.level<3 and a==1:self.level+=1
        elif self.level==3 and a==1 and self.win:self.done=True
        return self.observation_space
    def close(self):return {'score':100.0 if self.level==3 else 0.0,'total_levels':3,'completed':self.done}


def checkpoint(prefix,win=True):
    e=Finalize(win)
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

    def test_not_final_level_does_not_trigger_confirmation(self):
        r=confirm(Finalize,(0,1),(1,1),2,checkpoint((1,1)),checkpoint(()),budget=10)
        self.assertEqual(r['status'],'NOT_CONFIRMED_FINAL_LEVEL')
        self.assertEqual(r['declared_levels'],3)

if __name__=='__main__':unittest.main()
