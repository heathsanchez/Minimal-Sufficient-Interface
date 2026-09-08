"""Source-blind closed-loop qualification; no ARC game rules or solution paths."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'arc3_consequence'))
from closed_feedback import FeedbackArchive, develop, replay, digest

class World:
    def __init__(self, goal=2, log=None):
        self.n=0; self.goal=goal; self.log=log
        self.observation_space=self.frame()
    def frame(self):
        return {'frame':[[[self.n]]], 'levels_completed':self.n,
                'state':'WIN' if self.n>=self.goal else 'NOT_FINISHED',
                'available_actions':[0,1]}
    def reset(self):
        self.n=0; return self.frame()
    def step(self,a):
        if self.log is not None:self.log.append((self.n,a))
        if a==1:self.n+=1
        return self.frame()
    def close(self):return None

class Tests(unittest.TestCase):
    def test_replay(self):
        r=replay(World,(1,),None,3)
        self.assertEqual(r['levels_completed'],1)
        self.assertEqual(replay(World,(1,),digest(r['observations'][-1]),3)['status'],'OBSERVED')
        self.assertEqual(replay(World,(0,),digest(r['observations'][-1]),3)['status'],'INCONCLUSIVE_PREFIX_MISMATCH')
    def test_conflicting_observations_are_not_universal_laws(self):
        a=FeedbackArchive();b=World().frame();c=World().frame();c['frame']=[[[1]]]
        a.retain((),b,0,b);a.retain((),b,0,c)
        self.assertEqual(len(a.conflicts),1)
    def test_feedback_reaches_terminal(self):
        r=develop(World,(0,1),budget=5,max_depth=4,max_training_actions=100,max_episodes=100)
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['result']['state'],'WIN')
    def test_bounds(self):
        r=develop(World,(0,1),budget=5,max_depth=4,max_training_actions=2,max_episodes=2)
        self.assertNotEqual(r['status'],'VERIFIED_WIN')
        self.assertLessEqual(r['training_actions'],2)
        self.assertLessEqual(r['training_episodes'],2)
    def test_install_requires_matching_entry_and_result(self):
        a=FeedbackArchive();r=replay(World,(1,),None,3)
        start=digest(r['observations'][0]);end=r['final_sha256']
        a.install(start,(1,),end,r)
        self.assertEqual(len(a.options),1)
        with self.assertRaises(ValueError):a.install(end,(1,),end,r)
        with self.assertRaises(ValueError):a.install(start,(1,),start,r)
    def test_initial_win_is_not_lost(self):
        result=develop(lambda:World(0),(0,1),budget=3)
        self.assertEqual(result['status'],'VERIFIED_WIN')
        self.assertEqual(result['result']['state'],'WIN')
    def test_unconfirmed_progress_is_not_installed_as_a_win(self):
        r=develop(World,(0,1),budget=3,max_depth=2,max_training_actions=6,max_episodes=10)
        self.assertNotEqual(r['status'],'VERIFIED_WIN')
        self.assertTrue(all(x['target_sha256'] for x in r['development']['installed_options']))
    def test_ablation_still_has_the_same_external_verifier(self):
        r=develop(World,(0,1),budget=5,max_depth=4,max_training_actions=100,max_episodes=100,feedback=False)
        self.assertEqual(r['status'],'VERIFIED_WIN')
        self.assertEqual(r['result']['state'],'WIN')
    def test_feedback_changes_the_next_action(self):
        warm_log=[];cold_log=[]
        develop(lambda:World(log=warm_log),(0,1),budget=5,max_depth=3,max_training_actions=100,max_episodes=100)
        develop(lambda:World(log=cold_log),(0,1),budget=5,max_depth=3,max_training_actions=100,max_episodes=100,feedback=False)
        self.assertEqual(next(a for n,a in warm_log if n==1),1)
        self.assertEqual(next(a for n,a in cold_log if n==1),0)

if __name__=='__main__':unittest.main()
