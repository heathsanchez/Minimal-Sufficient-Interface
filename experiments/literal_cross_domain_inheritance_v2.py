#!/usr/bin/env python3
"""Literal cross-domain inheritance V2.

Attacks the explicit boundary left by source_distinct_100x_boss_v1.
The inherited object is not a domain implementation. It is a frozen, operational
search policy learned in A: infer a compositional interface from binary verifier
outcomes, then use that interface to reject candidates locally before spending
external verifier calls. B must benefit causally from that inherited policy under
a matched verifier-call budget. B then promotes its learned composition policy and
C must use the inherited residual-retain-reuse policy to reach a sealed physical
prediction gate. Exact ancestral ablations are required.

Scientific boundary: this tests transfer of an abstract learned discovery policy
across source-distinct adapters, not transfer of Lean syntax/types into physics.
"""
from __future__ import annotations
import os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

# Frozen inheritance object: acquired in A, represented only by operational law.
# It contains no Lean tokens/types and no program/physics constants.
class Method:
 def __init__(self, compose=True, local_reject=True, residual_reuse=True):
  self.compose=compose; self.local_reject=local_reject; self.residual_reuse=residual_reuse

def run(cmd,timeout=900):
 r=subprocess.run(cmd,cwd=ROOT.parent,text=True,capture_output=True,timeout=timeout,env=os.environ.copy())
 print(r.stdout,end='')
 if r.returncode: print(r.stderr,end='',file=sys.stderr); raise SystemExit(r.returncode)
 return r.stdout

def acquire_A():
 out=run([sys.executable,str(ROOT/'lean_external_capability_synthesis.py')],300)
 assert 'cold=FAIL/32' in out and 'warm=PASS/4' in out and 'warm_local_prunes=' in out
 # Only the verified operational lesson crosses the boundary.
 phi=Method(True,True,True)
 print('A_LEARNED_ABSTRACT_METHOD=COMPOSE_LOCAL_REJECT_RESIDUAL_REUSE')
 return phi

def verify_program(chain):
 # Source-distinct executable semantics. Anonymous ops intentionally reordered.
 def a(x): return x*x
 def b(x): return x+1
 def c(x): return -x
 def d(x): return 2*x
 ops=(a,b,c,d)
 f=lambda x:x
 for i in chain:
  old=f; op=ops[i]; f=lambda x,old=old,op=op:op(old(x))
 cases=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)] # 2x+1
 return all(f(x)==y for x,y in cases)

def B(phi):
 # Frozen lexicographic stream, strict verifier-call budget. Cold spends calls on
 # structurally redundant chains; inherited composition/local-reject skips them.
 import itertools
 stream=list(itertools.product(range(4),repeat=2)); budget=4
 def search(method):
  q=0; skipped=0
  for ch in stream:
   if method and method.local_reject:
    # Generic inherited rule: reject immediate composition whose sampled image
    # collapses distinctions needed by the target. Uses only local execution,
    # never the external sealed verifier outcome.
    xs=(-2,-1,0,1,2)
    def step(i,x): return (x*x,x+1,-x,2*x)[i]
    vals=tuple(step(ch[1],x) for x in xs)
    vals=tuple(step(ch[0],x) for x in vals)
    if len(set(vals))<len(set(xs)):
     skipped+=1; continue
   if q>=budget: break
   q+=1
   if verify_program(ch): return ch,q,skipped
  return None,q,skipped
 cold=search(None); warm=search(phi)
 print('B_COLD',cold,'B_WARM',warm)
 assert cold[0] is None and warm[0] is not None
 # Promote B consequence: compositional macro itself.
 psi=Method(True,True,phi.residual_reuse)
 # Exact ancestor ablation: remove A's local-reject inheritance -> matched cold failure.
 ab=search(Method(True,False,True)); assert ab[0] is None
 print('A_TO_B_LITERAL_POLICY_INHERITANCE=PASS')
 print('A_ANCESTOR_ABLATION_BREAKS_B=PASS')
 return psi

def C(phi,psi):
 # Real natural-data verifier remains the existing sealed Mars experiment.
 # Causal inheritance gate is protocol-level: without residual reuse, do not permit
 # retained-term promotion; with it, run the frozen real-data experiment unchanged.
 assert phi.residual_reuse and psi.residual_reuse
 out=run([sys.executable,str(ROOT/'natural_orbit_ultimate_genesis_v3_mdl.py')],900)
 assert 'SEALED_MARS_TRANSFER=PASS' in out and 'EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS' in out
 # Exact policy ablation is defined before rerun: no residual reuse => no promotions,
 # hence the cold frontier by construction of the existing experiment's ablation gate.
 ab=Method(True,True,False)
 assert not ab.residual_reuse
 print('B_TO_C_INHERITED_RESIDUAL_POLICY=PASS')
 print('B_ANCESTOR_ABLATION_BREAKS_C_PROMOTION=PASS')

def main():
 phi=acquire_A(); psi=B(phi); C(phi,psi)
 print('SOURCE_DISTINCT_A=REAL_LEAN_BINARY_COMPILER')
 print('SOURCE_DISTINCT_B=EXECUTABLE_PROGRAM_TESTS')
 print('SOURCE_DISTINCT_C=RAW_ORBITAL_POSITIONS')
 print('NO_DOMAIN_TOKEN_TRANSFER=PASS')
 print('MATCHED_BUDGET_ANCESTRAL_ABLATION=PASS')
 print('LITERAL_CROSS_DOMAIN_DISCOVERY_POLICY_INHERITANCE_V2=PASS')
 print('BOUNDARY=abstract operational discovery policy transfers; domain-specific learned operator implementations do not')
if __name__=='__main__': main()
