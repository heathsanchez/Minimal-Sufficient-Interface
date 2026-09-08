import unittest
from dataclasses import dataclass
from compact_agent import Controller, run_episode

@dataclass
class Frame:
    levels_completed: int
    state: str

class HiddenEnvironment:
    # Test-only hidden world; the agent receives only Frame and step().
    def __init__(self, good, lengths, actions=(1,2,3,4)):
        self.good, self.lengths, self.action_space = good, lengths, actions
        self.level = self.progress = 0
        self.observation_space = Frame(0, 'NOT_PLAYED')
    def step(self, action):
        if action != self.good:
            self.progress = 0
        else:
            self.progress += 1
        if self.progress >= self.lengths[self.level]:
            self.level += 1
            self.progress = 0
        state = 'WIN' if self.level == len(self.lengths) else 'NOT_PLAYED'
        self.observation_space = Frame(self.level, state)
        return self.observation_space
    def reset(self):
        self.progress = 0
        return self.observation_space

class CompactTests(unittest.TestCase):
    def test_transfer_and_ablation(self):
        lengths = (3, 4, 5, 6)
        for good in (1,2,3,4):
            warm = run_episode(HiddenEnvironment(good,lengths), Controller((1,2,3,4),6))
            self.assertEqual(warm['state'],'WIN')
            self.assertEqual(warm['levels_completed'],4)
            self.assertEqual(warm['model_calls'],0)
            self.assertGreaterEqual(warm['promotions'],4)
            class Ablated(Controller):
                def observe(self, before, action, after, state='NOT_PLAYED'):
                    outcome = super().observe(before,action,after,state)
                    if after > before:
                        self.archive.clear()
                        self.rejected.clear()
                    return outcome
            cold = run_episode(HiddenEnvironment(good,lengths), Ablated((1,2,3,4),6))
            self.assertEqual(cold['state'],'WIN')
            self.assertLessEqual(warm['actions'],cold['actions'])
        print('TRANSFER: 4/4 hidden action assignments solved; model calls=0')
    def test_no_unearned_capability(self):
        c = Controller((1,2),2)
        c.select(0)
        c.observe(0,1,0)
        c.observe(0,1,0)
        self.assertEqual(c.archive,[])
        self.assertEqual(c.promotions,0)
    def test_identity_and_replay(self):
        c = Controller((1,),3)
        c.select(0)
        c.observe(0,1,0)
        c.observe(0,1,1)
        self.assertEqual(len(c.archive),1)
        self.assertEqual(c.archive[0].evidence,((0,1,0,'NOT_PLAYED'),(0,1,1,'NOT_PLAYED')))
    def test_revocation(self):
        c = Controller((1,2),2)
        c.select(0); c.observe(0,1,1)
        c.select(1); c.observe(1,1,1); c.observe(1,1,1)
        self.assertEqual(c.revocations,1)
        self.assertEqual(c.select(1),2)
    def test_invalid_bounds(self):
        with self.assertRaises(ValueError): Controller((),2)
        with self.assertRaises(ValueError): Controller((1,),0)

if __name__ == '__main__': unittest.main()
