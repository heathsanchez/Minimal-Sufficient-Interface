"""Constructed-domain tests, not ARC scores."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from restart_development import RestartDevelopment, discover, execute, compare

class Environment:
    def __init__(self, success=(2,1), mismatch=False):
        self.success=success;self.history=();self.mismatch=mismatch
        self.observation_space=self.obs()
    def obs(self):
        return {'frame':[[[0]]],'levels_completed':int(self.history==self.success),
                'state':'WIN' if self.history==self.success else 'GAME_OVER' if self.history and self.history[0]==1 else 'NOT_FINISHED',
                'available_actions':[1,2]}
    def reset(self):
        self.history=();return self.obs()
    def step(self,a):
        self.history+=(a,);self.observation_space=self.obs();return self.observation_space

class RestartTests(unittest.TestCase):
    def test_terminal_prefix_is_not_expanded(self):
        d=RestartDevelopment((1,2),max_depth=3)
        p=d.propose();self.assertEqual(p,(1,))
        d.retain(p,execute(Environment(),p,3))
        self.assertIn((1,),d.rejected)
        self.assertEqual(d.propose(),(2,))
        self.assertNotIn((1,1),d.frontier)

    def test_retained_prefix_discovers_unseen_success(self):
        result=discover(Environment,(1,2),max_episodes=8,max_depth=3)
        self.assertEqual(result['status'],'PROGRESS_WITNESSED')
        self.assertEqual(result['program'],(2,1))
        self.assertGreater(result['training_actions'],0)
        self.assertEqual(execute(Environment(),result['program'],3)['progress'],1)

    def test_bound_is_not_success(self):
        result=discover(lambda:Environment(success=(2,2,2,2)),(1,2),max_episodes=2,max_depth=2)
        self.assertEqual(result['status'],'NO_PROGRESS_WITHIN_BOUND')
        self.assertNotIn('program',result)
        self.assertFalse(compare(lambda:Environment(success=(2,2,2,2)),(1,2),max_episodes=2,max_depth=2)['improved'])

    def test_fresh_start_qualification(self):
        result=compare(Environment,(1,2),budget=4,max_episodes=8,max_depth=3)
        self.assertEqual(result['status'],'COMPARABLE')
        self.assertTrue(result['improved'])
        self.assertEqual(result['proposed']['progress'],1)
        self.assertEqual(result['baseline']['progress'],0)
        self.assertEqual(result['candidate'],(2,1))

    def test_no_unverified_promotion(self):
        d=RestartDevelopment((1,2))
        result=execute(Environment(),(2,),3)
        self.assertEqual(d.retain((2,),result),'NONTERMINAL_PREFIX')
        self.assertEqual(d.successful,[])
        self.assertEqual(d.retain((1,),execute(Environment(),(1,),3)),'TERMINAL_PREFIX')
        self.assertEqual(d.successful,[])

if __name__=='__main__':unittest.main()
