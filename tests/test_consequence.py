import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments/convergence'))
sys.path.insert(0,str(ROOT/'experiments/arc3_consequence'))
from finite_consequence import *
from agent import Development,SensorGrammar,Transition,run_episode,observation

class FiniteKernelTests(unittest.TestCase):
    def test_required_refinement_and_minimal_realization(self):
        rows=[{'x':x,'y':y,'out':x} for x in range(2) for y in range(2)]
        q=lambda r:0;f=lambda r:r['out']
        self.assertEqual(len(witnesses(rows,q,f)),4)
        self.assertEqual(conflict_count(rows,necessary_refinement(q,f),f),0)
        cs=[Candidate('x',1,lambda r:r['x']),Candidate('y',1,lambda r:r['y'])]
        r=synthesize(rows,q,f,cs)
        self.assertEqual(r.status,'FINITE_ADEQUATE')
        self.assertEqual(tuple(c.name for c in r.features),('x',))
        self.assertEqual(replay(rows,q,f,r),0)
        self.assertIn('AdequacyTester.adequacyWitnesses',lean_certificate(rows,q,f,r))
    def test_no_grammar_and_no_false_proof(self):
        rows=[{'x':0,'out':0},{'x':1,'out':1}]
        q=lambda r:0;f=lambda r:r['out']
        r=synthesize(rows,q,f,[Candidate('constant',0,lambda r:0)])
        self.assertEqual(r.status,'NO_REPAIR_IN_GRAMMAR')
        with self.assertRaises(ValueError):lean_certificate(rows,q,f,r)
    def test_ambiguity_is_retained(self):
        rows=[{'x':0,'y':0,'out':0},{'x':1,'y':1,'out':1}]
        r=synthesize(rows,lambda r:0,lambda r:r['out'],[
            Candidate('x',1,lambda r:r['x']),Candidate('y',1,lambda r:r['y'])])
        self.assertEqual(r.status,'FINITE_ADEQUATE')
        # Extentionally indistinguishable candidates remain one equivalence class.
        self.assertEqual(r.candidate_count,1)
        self.assertEqual(r.before,1)
    def test_bound_is_not_impossibility(self):
        rows=[{'x':0,'out':0},{'x':1,'out':1}]
        r=synthesize(rows,lambda r:0,lambda r:r['out'],[
            Candidate('x',1,lambda r:r['x'])],max_combinations=0)
        self.assertEqual(r.status,'BOUND_EXHAUSTED')

class Frame:
    def __init__(self,obs):
        self.frame=obs['frame'];self.levels_completed=obs['levels_completed'];self.state=obs['state'];self.available_actions=[1,2]

class HiddenPhase:
    """Test-only hidden state: current pixels do not reveal the required phase."""
    def __init__(self,levels=3,palette=7):
        self.phase=0;self.level=0;self.limit=levels;self.palette=palette;self.observation_space=self.render()
    def render(self):
        return Frame({'frame':[[[self.palette]]],'levels_completed':self.level,
                      'state':'WIN' if self.level==self.limit else 'NOT_FINISHED'})
    def step(self,a):
        if a==1:self.phase=1
        elif a==2 and self.phase==1:
            self.level+=1;self.phase=0
        self.observation_space=self.render();return self.observation_space

class InteractionTests(unittest.TestCase):
    def test_history_is_discovered_from_a_real_residual(self):
        obs={'frame':[[[7]]],'levels_completed':0,'state':'NOT_FINISHED'}
        target=dict(obs)
        rows=[Transition(obs,(),2,target,(0,'NOT_FINISHED')),
              Transition(obs,(2,1),2,target,(1,'NOT_FINISHED'))]
        d=Development((2,1),SensorGrammar(history_bound=3))
        d.records=rows
        repair=d.refresh()
        self.assertEqual(repair.status,'FINITE_ADEQUATE')
        self.assertEqual([c.name for c in repair.features],['history:1'])
        self.assertEqual(replay(rows,d.base,lambda r:r.outcome,
                                type('R',(),{'features':d.features})()),0)
    def test_hidden_phase_reaches_goal_without_semantic_labels(self):
        d=Development((2,1),SensorGrammar(history_bound=3),repair_interval=2)
        result=run_episode(HiddenPhase(),(2,1),40,d)
        self.assertEqual(result['state'],'WIN',result)
        self.assertEqual(result['model_calls'],0)
        self.assertGreater(result['version'],0)
        self.assertTrue(any('history:' in n for n in result['features']))
        print('HIDDEN_PHASE',result['actions'],result['features'],result['script_successes'])
    def test_recorded_public_trace_is_not_a_competition_score(self):
        import os
        p=Path(os.environ.get('ARC3_TRACE_PATH','/mnt/data/arc3_compact/results/motion/arc3-motion-observations.json'))
        if not p.exists():self.skipTest('Public observation artifact not mounted')
        import json
        trace=json.loads(p.read_text())
        d=Development((1,2,3,4),SensorGrammar(feature_bound=32),repair_interval=10000)
        for i in range(1,len(trace)):
            d.observe(trace[i-1],trace[i]['action'],trace[i])
        self.assertEqual(len(d.records),179)
        self.assertEqual(max(r.target['levels_completed'] for r in d.records),1)
        self.assertTrue(any(r.outcome[0]>0 for r in d.records))
        print('PUBLIC_REPLAY',d.snapshot()['version'],d.snapshot()['features'])

class RecursiveProcedureTests(unittest.TestCase):
    def test_same_kernel_refines_a_generated_program_guard(self):
        obs={'frame':[[[7]]],'levels_completed':0,'state':'NOT_FINISHED'}
        d=Development((2,1),SensorGrammar(history_bound=3))
        program=('program',(2,))
        d.policy_records=[Transition(obs,(1,),program,obs,(1,'NOT_FINISHED')),
                          Transition(obs,(2,),program,obs,(0,'NOT_FINISHED'))]
        r=d.refresh_policy()
        self.assertEqual(r.status,'FINITE_ADEQUATE')
        self.assertEqual([c.name for c in d.policy_features],['history:1'])
        d.scripts=[{'actions':(2,),'source':obs,'history':(1,),'evidence':'test'}]
        d.approved_scripts[(2,)]={'status':'VERIFIED_IMPROVEMENT'}
        d.global_history=(2,)
        self.assertEqual(d._script_candidates(obs),())
        d.global_history=(1,)
        self.assertEqual(d._script_candidates(obs),((2,),))
        print('POLICY_REFINEMENT',d.policy_repairs)

    def test_procedure_transfer_and_ablation(self):
        from qualification import qualify_programs
        d=Development((2,1),SensorGrammar(history_bound=3),repair_interval=2)
        training=run_episode(HiddenPhase(1),(2,1),20,d)
        self.assertEqual(training['state'],'WIN')
        self.assertTrue(d.scripts)
        evidence=qualify_programs(d,[lambda:HiddenPhase(1,7)],
                                  [lambda:HiddenPhase(1,9)],budget=12)
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence['status'],'VERIFIED_IMPROVEMENT')
        self.assertEqual(evidence['script'],(1,2))
        warm=run_episode(HiddenPhase(10,9),(2,1),100,d)
        cold=run_episode(HiddenPhase(10,9),(2,1),100,
                         Development((2,1),SensorGrammar(history_bound=3),repair_interval=2,retain_scripts=False))
        self.assertEqual(warm['state'],'WIN')
        self.assertEqual(cold['state'],'WIN')
        self.assertGreater(warm['script_successes'],0)
        self.assertLess(warm['actions'],cold['actions'])
        print('PROCEDURE_ABLATION',warm['actions'],cold['actions'])
        print('QUALIFIED_PROGRAM',evidence['script'])

    def test_no_unverified_policy_promotion(self):
        from qualification import qualify_programs
        d=Development((2,1),SensorGrammar(history_bound=3),repair_interval=2)
        run_episode(HiddenPhase(1),(2,1),20,d)
        self.assertEqual(d.approved_scripts,{})
        self.assertEqual(d._script_candidates({'frame':[[[7]]],'levels_completed':0,'state':'NOT_FINISHED'}),())
        result=qualify_programs(d,[lambda:HiddenPhase(1,7)],
                                [lambda:HiddenPhase(1,9)],budget=1)
        self.assertIsNone(result)
        self.assertEqual(d.approved_scripts,{})
        self.assertTrue(d.qualification_log)

if __name__=='__main__':unittest.main()
