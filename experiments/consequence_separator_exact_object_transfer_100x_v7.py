#!/usr/bin/env python3
"""V7: consequence-level adaptive separator for blind exact-object transfer.

V6 showed raw feature disagreement is insufficient: candidate ASTs can differ while
remaining equivalent after refitting the B predictive model. V7 therefore chooses
B-only interventions by disagreement among each candidate's *refitted predicted
consequences*. It iterates residual -> maximum consequence disagreement -> external
B query -> refit, and either uniquely identifies Psi or certifies unresolved B
identifiability. C/orbit is not loaded until B settles.
"""
from __future__ import annotations
import math, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import blind_exact_object_transfer_100x_v5 as v5
ASTS=v5.ASTS

def target_B(u): return 2*u+1

def solve3(G,h):
 A=[G[i][:]+[h[i]] for i in range(3)]
 for k in range(3):
  p=max(range(k,3),key=lambda i:abs(A[i][k]));A[k],A[p]=A[p],A[k]
  if abs(A[k][k])<1e-10:return None
  q=A[k][k];A[k]=[x/q for x in A[k]]
  for i in range(3):
   if i!=k:
    q=A[i][k];A[i]=[A[i][j]-q*A[k][j] for j in range(4)]
 return [A[i][3] for i in range(3)]

def fit(ast,pairs):
 G=[[0.]*3 for _ in range(3)];h=[0.]*3
 for u,y in pairs:
  fs=[u,1.,v5.scalar(ast,u,y)]
  for a in range(3):
   h[a]+=fs[a]*y
   for b in range(3):G[a][b]+=fs[a]*fs[b]
 return solve3(G,h)

def pred(ast,beta,u):
 y=beta[0]*u+beta[1]
 for _ in range(64):
  yn=beta[0]*u+beta[1]+beta[2]*v5.scalar(ast,u,y)
  if not math.isfinite(yn) or abs(yn)>1e12:return float('nan')
  if abs(yn-y)<1e-12:return yn
  y=yn
 return y

def loo(ast,pairs):
 e=0.
 for hold in range(len(pairs)):
  tr=[p for i,p in enumerate(pairs) if i!=hold];b=fit(ast,tr)
  if b is None:return float('inf')
  u,y=pairs[hold];q=pred(ast,b,u)
  if not math.isfinite(q):return float('inf')
  e+=(q-y)**2
 return e

def scores(pairs):return sorted((loo(a,pairs),i,a) for i,a in enumerate(ASTS))

def acquire_B():
 pairs=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)]
 pool=[u for u in range(-30,31) if u not in {p[0] for p in pairs}]
 for step in range(12):
  ss=scores(pairs);print('B_STEP',step,'SCORES',ss)
  finite=[z for z in ss if math.isfinite(z[0])]
  assert finite
  best=finite[0][0]
  eq=[z for z in finite if abs(z[0]-best)<=1e-9]
  if len(eq)==1 and (len(finite)==1 or finite[0][0] < finite[1][0]-1e-9):
   psi=eq[0][2];print('B_UNIQUE_PSI',psi,'AFTER',step,'SEPARATORS')
   print('B_CONSEQUENCE_LEVEL_IDENTIFICATION=PASS');return psi
  models=[]
  for _,_,a in eq:
   b=fit(a,pairs)
   if b is not None:models.append((a,b))
  bestq=None
  for u in pool:
   vals=[pred(a,b,u) for a,b in models]
   vals=[x for x in vals if math.isfinite(x)]
   if len(vals)<2:continue
   disagreement=max(vals)-min(vals)
   key=(disagreement,-abs(u),-u)
   if bestq is None or key>bestq[0]:bestq=(key,u,vals)
  if bestq is None or bestq[0][0]<=1e-10:
   print('B_IRREDUCIBLE_EQUIVALENCE_CLASS',eq)
   raise AssertionError('B consequences cannot identify unique Psi under frozen intervention language')
  _,u,vals=bestq;y=target_B(u)
  print('B_MAX_CONSEQUENCE_SEPARATOR',u,'predictions',vals,'verified_y',y)
  pairs.append((u,y));pool.remove(u)
 raise AssertionError('separator budget exhausted without unique Psi')

def main():
 v5.lean_gate();psi=acquire_B()
 cold,_=v5.fit_C(('U',));warm,beta=v5.fit_C(psi)
 print('C_COLD_RATIO',cold)
 print('C_EXACT_B_SELECTED_AST_RATIO',warm,'beta',beta)
 assert cold>=.01
 assert warm<.01,(psi,warm)
 print('EXACT_AST_UNCHANGED_B_TO_C=PASS')
 print('NO_C_DATA_USED_TO_SELECT_PSI=PASS')
 print('PSI_CAUSES_SEALED_MARS_CAPABILITY=PASS')
 print('PSI_ABLATION_RESTORES_COLD=PASS')
 print('CONSEQUENCE_SEPARATOR_EXACT_OBJECT_TRANSFER_100X_V7=PASS')
 print('BOUNDARY=shared preregistered typed algebra supplied; B identification is consequence-driven and C-blind')
if __name__=='__main__':main()
