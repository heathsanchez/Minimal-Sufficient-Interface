"""Constructed-domain tests, not ARC scores."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from compositional_development import OptionSearch, discover_levels, compare_levels
from test_multi_level_development import Environment

class CompositionTests(unittest.TestCase):
    def test_witnessed_option_is_composed_before_primitive_breadth(self):
        s=OptionSearch((1,2),((2,1),),max_depth=4)
        self.assertEqual(s.propose(),(2,1))
        s.retain((2,1),{'progress':0,'terminal':False,'actions':2,
                        'executed':(2,1),'initial_sha256':'x','trace_sha256':'y'})
        self.assertEqual(s.propose(),(2,1,2,1))

    def test_composition_respects_primitive_depth(self):
        s=OptionSearch((1,2),((2,1),),max_depth=2)
        self.assertEqual(s.propose(),(2,1))
        s.retain((2,1),{'progress':0,'terminal':False,'actions':2,
                        'executed':(2,1),'initial_sha256':'x','trace_sha256':'y'})
        self.assertNotIn((2,1,2,1),s.frontier)

    def test_duplicate_programs_are_not_retried(self):
        s=OptionSearch((1,2),((2,1),),max_depth=4)
        seen=[]
        for _ in range(20):
            p=s.propose()
            if p is None:break
            seen.append(p)
            s.retain(p,{'progress':0,'terminal':False,'actions':len(p),
                        'executed':p,'initial_sha256':'x','trace_sha256':'y'})
        self.assertEqual(len(seen),len(set(seen)))

    def test_compositional_full_game_and_ablation(self):
        r=compare_levels(Environment,(1,2),budget=20,max_episodes=30,
                         max_depth=4,max_training_actions=200,max_levels=5)
        self.assertEqual(r['status'],'COMPARABLE')
        self.assertTrue(r['improved'])
        self.assertEqual(r['warm']['levels_completed'],5)
        self.assertEqual(r['cold']['levels_completed'],0)
        self.assertEqual(r['development']['levels_witnessed'],5)

    def test_no_progress_is_not_promoted(self):
        d=discover_levels(Environment,(1,2),budget=2,max_episodes=1,
                          max_depth=2,max_training_actions=20)
        self.assertEqual(d.status,'NO_PROGRESS_WITHIN_BOUND')
        self.assertEqual(d.prefix,())
        self.assertEqual(d.options,[])

if __name__=='__main__':unittest.main()
