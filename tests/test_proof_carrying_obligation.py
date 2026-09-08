"""Frozen, bounded integration and negative-certificate qualification."""
from dataclasses import replace
from itertools import product
import unittest
from experiments.mathgraph import recursive_obligation_synthesis as core
from experiments.mathgraph import proof_carrying_obligation as pc
from experiments.mathgraph.proof_carrying_lean import source_text


def state(law): return pc.State(law,('x','y','z'),core.SEED)

def value(t,env,table):
    if isinstance(t,str): return env[t]
    return table[2*value(t[1],env,table)+value(t[2],env,table)]

def holds(e,env,table): return value(e[0],env,table)==value(e[1],env,table)

def law_holds(law,table):
    return all(holds(law,dict(zip(('x','y','z'),values)),table) for values in product(range(2),repeat=3))

class ProofCarryingObligation(unittest.TestCase):
    def test_two_source_laws_and_recursive_reuse(self):
        for law in (core.LAW_40909,core.LAW_11116):
            s=state(law); previous=None
            for n in range(3):
                s,c=pc.next_branch(s,previous,f'u{n}')
                self.assertTrue(pc.check_state(s))
                self.assertEqual(c.dependencies,() if n==0 else (previous,))
                previous=c.identity
            self.assertEqual(len(s.archive),3)
            self.assertEqual(source_text(s),source_text(s))
            self.assertNotIn('sorry',source_text(s))

    def test_holdout_law_not_in_original_selection_policy(self):
        # (x◇y)◇z=x; the forced q◇F=A is not a named arithmetic/Austin target.
        law=(core.op(core.op('x','y'),'z'),'x')
        s=state(law)
        candidates=core.synthesize(law,s.source_variables,branch_left=s.seed[0],branch_right=s.seed[1],atoms=('A','p','F'))
        expected=(core.op('q','F'),'A')
        c=next(c for c in candidates if c.equation==expected)
        after,cert=pc.compile_candidate(s,c)
        self.assertEqual(cert.equation,expected)
        self.assertTrue(pc.check_state(after))
        self.assertEqual(len(after.archive),1)

    def test_reject_forged_claim_and_hash(self):
        s,c=pc.next_branch(state(core.LAW_40909),None,'u0')
        with self.assertRaises(pc.Rejected): pc.install(s,('A','p'),c.proof)
        with self.assertRaises(pc.Rejected): pc.check_state(replace(s,archive=(replace(c,identity='forged'),)))
        with self.assertRaises(pc.Rejected): pc.check_state(replace(s,archive=(replace(c,equation=('A','p')),)))

    def test_reject_missing_and_forward_dependency(self):
        s,c=pc.next_branch(state(core.LAW_40909),None,'u0')
        s,d=pc.next_branch(s,c.identity,'u1')
        with self.assertRaises(pc.Rejected): pc.check_state(replace(s,archive=(d,)))
        with self.assertRaises(pc.Rejected): pc.check_state(replace(s,archive=(d,c)))
        with self.assertRaises(pc.Rejected): pc.install(state(core.LAW_40909),c.equation,pc.Proof('use',(c.identity,)))

    def test_reject_wrong_rewrite_and_inference(self):
        s=state(core.LAW_40909)
        c=core.synthesize(s.source,s.source_variables,branch_left=s.seed[0],branch_right=s.seed[1],atoms=('A','p','F'))[0]
        with self.assertRaises(pc.Rejected): pc.compile_candidate(s,replace(c,equation=('A','p')))
        with self.assertRaises(pc.Rejected): pc.install(s,('A','p'),pc.Proof('magic'))
        with self.assertRaises(pc.Rejected): pc.install(s,('A','p'),pc.Proof('trans',(pc.Proof('refl',('A',)),pc.Proof('refl',('p',)))))
        with self.assertRaises(pc.Rejected): pc.rewrite_at(core.op('A','p'),(0,),'missing','q')

    def test_source_and_premise_are_distinct(self):
        s=state(core.LAW_40909)
        with self.assertRaises(pc.Rejected): pc.install(s,core.SEED,pc.Proof('source',((('x','A'),('y','p'),('z','q')),)))
        with self.assertRaises(pc.Rejected): pc.install(s,core.SEED,pc.Proof('source',((('x','A'),),)))
        with self.assertRaises(pc.Rejected): pc.check_state(replace(s,source_variables=('x','x','z')))

    def test_finite_semantic_replay_of_conditional_claims(self):
        for law in (core.LAW_40909,core.LAW_11116,(core.op(core.op('x','y'),'z'),'x')):
            s=state(law)
            if law in (core.LAW_40909,core.LAW_11116):
                s,c=pc.next_branch(s,None,'u0')
            else:
                target=(core.op('q','F'),'A')
                candidate=next(c for c in core.synthesize(law,s.source_variables,branch_left=s.seed[0],branch_right=s.seed[1],atoms=('A','p','F')) if c.equation==target)
                s,c=pc.compile_candidate(s,candidate)
            for table in product(range(2),repeat=4):
                if not law_holds(law,table): continue
                for values in product(range(2),repeat=4):
                    env=dict(zip(('A','p','q','F'),values)); env['u0']=env['F']
                    if holds(s.seed,env,table):
                        self.assertTrue(holds(c.equation,env,table))

    def test_archive_ablation_and_source_replay(self):
        s,c=pc.next_branch(state(core.LAW_40909),None,'u0')
        s,d=pc.next_branch(s,c.identity,'u1')
        with self.assertRaises(pc.Rejected): pc.check_state(replace(s,archive=(d,)))
        self.assertEqual(source_text(s).encode(),source_text(s).encode())
        self.assertIn('Derivation.sound',source_text(s))
        self.assertIn('hSeed : Holds',source_text(s))

if __name__=='__main__': unittest.main(verbosity=2)
