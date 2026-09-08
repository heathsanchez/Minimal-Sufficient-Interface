"""Constructed-domain tests; these are not ARC scores."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'arc3_consequence'))
from multi_level_development import execute_stage, discover_levels, compare_levels

class Environment:
    def __init__(self, levels=5, mismatch=False):
        self.levels=levels; self.mismatch=mismatch; self.history=();self.lost=False
        self.observation_space=self.obs()
    def obs(self):
        completed=min(self.levels,sum(self.history[i:i+2]==(2,1) for i in range(0,len(self.history),2)))
        return {'frame':[[[int(self.mismatch)]]], 'levels_completed':completed,
                'state':'WIN' if completed==self.levels else 'GAME_OVER' if self.lost else 'NOT_FINISHED',
                'available_actions':[1,2]}
    def reset(self):
        self.history=();self.lost=False;self.observation_space=self.obs();return self.observation_space
    def step(self,a):
        self.history+=(a,)
        if self.history[-2:] not in ((2,1),) and (len(self.history)%2==1 and a!=2 or len(self.history)%2==0 and a!=1):
            self.lost=True
        self.observation_space=self.obs();return self.observation_space

class MultiLevelTests(unittest.TestCase):
    def test_full_deployment_does_not_stop_at_first_progress(self):
        r=execute_stage(Environment(),(),(2,1)*5,0,20,stop_at_progress=False)
        self.assertEqual(r['levels_completed'],5)
        self.assertEqual(r['actions'],10)

    def test_prefix_checkpoint_and_target_are_checked(self):
        r=execute_stage(Environment(),(2,1),(2,1),1,20,checkpoint='wrong')
        self.assertEqual(r['status'],'INCONCLUSIVE_PREFIX_MISMATCH')
        self.assertEqual(r['actions'],2)
        self.assertEqual(r['progress'],0)
        r=execute_stage(Environment(),(2,1),(2,1),2,20)
        self.assertEqual(r['status'],'INCONCLUSIVE_PREFIX_MISMATCH')

    def test_prior_success_is_retested_not_assumed(self):
        d=discover_levels(Environment,(1,2),budget=20,max_episodes=30,max_depth=3,max_training_actions=200)
        self.assertEqual(d.status,'ALL_LEVELS_WITNESSED')
        self.assertEqual(d.prefix,(2,1)*5)
        self.assertEqual(len(d.options),1)
        self.assertEqual(len(d.stages),5)
        self.assertEqual(d.stages[1]['suffix'],(2,1))
        self.assertEqual(d.stages[-1]['actions'],10)
        self.assertEqual(d.stages[-1]['checkpoint_sha256'],d.checkpoint)
        self.assertGreater(d.training_actions,10)

    def test_fresh_start_ablation(self):
        r=compare_levels(Environment,(1,2),budget=20,max_episodes=30,max_depth=3,max_training_actions=200)
        self.assertEqual(r['status'],'COMPARABLE')
        self.assertTrue(r['improved'])
        self.assertEqual(r['cold']['levels_completed'],0)
        self.assertEqual(r['warm']['levels_completed'],5)
        self.assertEqual(r['warm']['actions'],10)

    def test_bound_does_not_promote_unseen_levels(self):
        d=discover_levels(Environment,(1,2),budget=20,max_episodes=3,max_depth=3,max_training_actions=200)
        self.assertEqual(d.status,'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(d.prefix,(2,1))
        self.assertEqual(len(d.stages),1)
        self.assertNotEqual(d.status,'ALL_LEVELS_WITNESSED')

    def test_no_progress_is_not_success(self):
        d=discover_levels(lambda:Environment(levels=5),(1,2),budget=2,max_episodes=1,max_depth=1,max_training_actions=20)
        self.assertEqual(d.status,'NO_PROGRESS_WITHIN_BOUND')
        self.assertEqual(d.prefix,())
        self.assertEqual(d.options,[])

if __name__=='__main__':unittest.main()
