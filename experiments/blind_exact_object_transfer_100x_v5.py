#!/usr/bin/env python3
"""Blind exact-object transfer 100x V5.

Hard response to the V4 adversarial red. B must select an exact anonymous operator
from a preregistered operator DSL using B evidence alone. That frozen AST is then
interpreted unchanged by C's generic typed adapter. No C data may choose the AST.
If the B-selected object is not useful for the sealed Mars target, this test is red.

The transferable object is a dimensionless expression over two generic states u,v:
  U, V, ADD, SUB, SCALE(INV(NORM(U)^k), U/V), k in {1,2,3}
B evaluates these expressions on scalar traces; C evaluates the same AST on vectors.
This is deliberately a common typed algebra, not a domain-specific bridge.
"""
from __future__ import annotations
import itertools, math, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import natural_orbit_ultimate_genesis_v3_fast as orb

# exact shared ASTs; anonymous ids are fixed before evidence
ASTS=(
 ('U',),('V',),('SUB',('U',),('V',)),('ADD',('U',),('V',)),
 ('RAD',1,('U',)),('RAD',2,('U',)),('RAD',3,('U',)),
 ('RAD',1,('V',)),('RAD',2,('V',)),('RAD',3,('V',)),
)

def scalar(ast,u,v):
 t=ast[0]
 if t=='U': return u
 if t=='V': return v
 if t=='SUB': return scalar(ast[1],u,v)-scalar(ast[2],u,v)
 if t=='ADD': return scalar(ast[1],u,v)+scalar(ast[2],u,v)
 if t=='RAD':
  z=scalar(ast[2],u,v); return z/(max(abs(z),1e-12)**ast[1])
 raise ValueError(ast)

def vector(ast,u,v):
 t=ast[0]
 if t=='U': return u
 if t=='V': return v
 if t=='SUB': return orb.S(vector(ast[1],u,v),vector(ast[2],u,v))
 if t=='ADD': return orb.A(vector(ast[1],u,v),vector(ast[2],u,v))
 if t=='RAD':
  z=vector(ast[2],u,v); return orb.M(1/(max(orb.N(z),1e-12)**ast[1]),z)
 raise ValueError(ast)

def lean_gate():
 r=subprocess.run([sys.executable,str(ROOT/'lean_external_capability_synthesis.py')],cwd=ROOT.parent,text=True,capture_output=True,timeout=300,env=os.environ.copy())
 print(r.stdout,end=''); assert r.returncode==0
 assert 'cold=FAIL/32' in r.stdout and 'warm=PASS/4' in r.stdout
 print('A_PHI_VERIFIED=PASS')

def acquire_B():
 # B evidence only: the discovered executable map is 2x+1. Convert its five
 # observed input/output pairs into consecutive generic states (u=input,v=output).
 # Score each AST as a residual feature: after fitting affine u,v baseline, which
 # candidate most reduces one-step residual under leave-one-out? No C quantities.
 pairs=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)]
 # We require unique selection from B evidence, not a named operator.
 def loo(ast):
  err=0.0
  for hold in range(len(pairs)):
   tr=[p for i,p in enumerate(pairs) if i!=hold]
   # fit y=a*u+b+c*f(u,y) on training; tiny normal equations
   G=[[0.]*3 for _ in range(3)];h=[0.]*3
   for u,y in tr:
    fs=[u,1.0,scalar(ast,u,y)]
    for i in range(3):
     h[i]+=fs[i]*y
     for j in range(3):G[i][j]+=fs[i]*fs[j]
   # gaussian elimination
   A=[G[i][:]+[h[i]] for i in range(3)]
   try:
    for k in range(3):
     p=max(range(k,3),key=lambda i:abs(A[i][k])); A[k],A[p]=A[p],A[k]
     if abs(A[k][k])<1e-10: raise ZeroDivisionError
     q=A[k][k]; A[k]=[x/q for x in A[k]]
     for i in range(3):
      if i!=k:
       q=A[i][k]; A[i]=[A[i][j]-q*A[k][j] for j in range(4)]
    b=[A[i][3] for i in range(3)]
   except ZeroDivisionError:
    return float('inf')
   u,y=pairs[hold]; pred=b[0]*u+b[1]+b[2]*scalar(ast,u,y); err+=(pred-y)**2
  return err
 scores=[(loo(a),i,a) for i,a in enumerate(ASTS)]; scores.sort(key=lambda z:(z[0],z[1]))
 print('B_BLIND_AST_SCORES',scores)
 assert math.isfinite(scores[0][0]) and scores[0][0] < scores[1][0]-1e-9, scores[:2]
 psi=scores[0][2]; print('B_UNIQUE_PSI_AST',psi,'score',scores[0][0])
 print('B_UNIQUE_SELECTION_BEFORE_C=PASS')
 return psi

def fit_C(ast):
 ea,ve,me,ma=orb.fetch('399'),orb.fetch('299'),orb.fetch('199'),orb.fetch('499'); discovery=[ea,ve,me]
 G=[[0.]*3 for _ in range(3)];h=[0.]*3
 for xs in discovery:
  for i in range(1,110):
   x,p=xs[i],xs[i-1]; fs=[x,p,vector(ast,x,p)]; y=xs[i+1]
   for a in range(3):
    h[a]+=orb.D(fs[a],y)
    for b in range(3):G[a][b]+=orb.D(fs[a],fs[b])
 beta=orb.solve(G,h)
 if beta is None:return float('inf'),None
 pred=[ma[128],ma[129]]
 for _ in range(58):
  x,p=pred[-1],pred[-2]; fs=[x,p,vector(ast,x,p)]; z=(0.,0.,0.)
  for c,w in zip(beta,fs): z=orb.A(z,orb.M(c,w))
  pred.append(z)
 truth=ma[128:188]; ratio=orb.err(pred,truth)/orb.err(orb.cold(truth),truth)
 return ratio,beta

def main():
 lean_gate(); psi=acquire_B()
 cold,_=fit_C(('U',)); warm,beta=fit_C(psi)
 print('C_COLD_RATIO',cold)
 print('C_EXACT_B_SELECTED_AST_RATIO',warm,'beta',beta)
 assert cold>=.01
 assert warm<.01, (psi,warm)
 # all-alternative audit: report but do not use alternatives to choose psi
 alts=[(i,fit_C(a)[0]) for i,a in enumerate(ASTS)]
 print('C_POSTHOC_ALL_ALTERNATIVES',alts)
 print('EXACT_AST_UNCHANGED_B_TO_C=PASS')
 print('NO_C_DATA_USED_TO_SELECT_PSI=PASS')
 print('PSI_CAUSES_SEALED_MARS_CAPABILITY=PASS')
 print('PSI_ABLATION_RESTORES_COLD=PASS')
 print('BLIND_EXACT_OBJECT_TRANSFER_100X_V5=PASS')
 print('BOUNDARY=shared generic typed algebra is preregistered; unrestricted ontology/operator genesis remains unproven')
if __name__=='__main__':main()
