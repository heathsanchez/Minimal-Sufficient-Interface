"""Constructed-domain tests, not ARC scores."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from consequence_search import ordered_actions, factors, RankedSearch, discover, compare
from test_consequence_quotient import HiddenPhase
from test_multi_level_development import Environment


def result(program, progress=0, terminal=False):
    return {'progress':progress,'terminal':terminal,'actions':len(program),
            'executed':tuple(program),'initial_sha256':'x','trace_sha256':'y'}


class ConsequenceSearchTests(unittest.TestCase):
    def test_quotient_never_discards_members(self):
        classes=[{'members':[(6,4,4),(6,8,8),(6,12,12)]},
                 {'members':[(6,2,2)]},{'members':[(6,60,4),(6,62,4)]}]
        actions=ordered_actions(classes)
        self.assertEqual(len(actions),6)
        self.assertEqual(set(actions),{tuple(a) for c in classes for a in c['members']})
        self.assertEqual(actions[0],(6,2,2))

    def test_mixed_tokens_and_factors(self):
        self.assertEqual(set(ordered_actions([{'members':[1,(6,2,2)]}])),{1,(6,2,2)})
        p=((6,2,2),)*2+((6,4,4),)*4+((6,2,2),)*2
        fs=factors(p,32)
        self.assertIn(((6,2,2),)*2,fs)
        self.assertIn(((6,4,4),)*4,fs)
        self.assertIn(((6,4,4),)*2,fs)
        self.assertTrue(all(len(f)<=32 for f in fs))

    def test_ranked_frontier_and_duplicate_suppression(self):
        s=RankedSearch((0,1,2,3,4,5,6,7),max_depth=4)
        seen=[]
        for _ in range(30):
            p=s.propose()
            if p is None:break
            seen.append(p)
            s.retain(p,result(p))
        self.assertEqual(len(seen),len(set(seen)))
        self.assertIn((0,0,0,0),seen)
        self.assertNotIn((7,),seen)
        self.assertTrue(all(len(p)<=4 for p in seen))

    def test_terminal_prefix_is_not_expanded(self):
        s=RankedSearch((0,1),max_depth=3)
        p=s.propose()
        self.assertEqual(s.retain(p,result(p,terminal=True)),'TERMINAL_PREFIX')
        self.assertNotIn(p,s.expanded)
        self.assertFalse(any(x[-1]==p+(0,) for x in s.frontier))

    def test_prior_success_is_a_candidate_not_an_assumed_rule(self):
        s=RankedSearch((1,2),((2,1),),max_depth=4)
        self.assertEqual(s.propose(),(2,1))
        self.assertEqual(s.retain((2,1),result((2,1))),'NONTERMINAL_PREFIX')
        self.assertIn((2,1,2,1),s.best)
        self.assertEqual(s.successful,[])

    def test_hidden_distinction_is_reopened_by_full_actions(self):
        d,qs,ops=discover(HiddenPhase,(0,1,2),budget=10,max_depth=2,
                          max_training_actions=100,max_episodes=100,max_levels=1,horizon=1)
        self.assertEqual(d.status,'ALL_LEVELS_WITNESSED')
        self.assertEqual(d.prefix,(1,2))
        self.assertEqual(len(qs[0]['classes']),1)
        self.assertEqual(ops[0]['alphabet_size'],3)

    def test_fresh_deployment_and_reused_options(self):
        r=compare(Environment,(1,2),budget=20,max_depth=4,
                  max_training_actions=300,max_episodes=100,max_levels=5,horizon=1)
        self.assertEqual(r['status'],'COMPARABLE')
        self.assertEqual(r['warm']['levels_completed'],5)
        self.assertEqual(r['cold']['levels_completed'],0)
        self.assertTrue(r['improved'])
        self.assertEqual(r['development']['levels_witnessed'],5)

    def test_bound_never_promotes_unseen_progress(self):
        d,qs,ops=discover(HiddenPhase,(0,1,2),budget=10,max_depth=2,
                          max_training_actions=2,max_episodes=2,max_levels=1,horizon=1)
        self.assertEqual(d.status,'TRAINING_BOUND_EXHAUSTED')
        self.assertEqual(d.prefix,())
        self.assertEqual(qs,[])

if __name__=='__main__':unittest.main()
