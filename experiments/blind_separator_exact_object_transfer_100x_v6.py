#!/usr/bin/env python3
"""V6: B-only separator before blind exact-object transfer.

V5 correctly stopped because B observational evidence left multiple candidate ASTs
numerically indistinguishable. V6 does not add a tie-breaker. It searches a fixed,
B-only intervention pool for the smallest input that separates the current top
behavioural equivalence class, queries the executable B system there, then rescoring
must uniquely identify one AST before any C/orbit data are loaded.

The exact surviving AST is transferred unchanged through the same preregistered
generic scalar/vector algebra. If it is not useful for sealed Mars, RED.
"""
from __future__ import annotations
import math, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import blind_exact_object_transfer_100x_v5 as v5

ASTS=v5.ASTS

def target_B(u): return 2*u+1

def residual_score(ast,pairs):
 # Fit y=a*u+b+c*f(u,y), evaluate leave-one-out exactly as V5.
 def solve3(G,h):
  A=[G[i][:]+[h[i]] for i in range(3)]
  for k in range(3):
   p=max(range(k,3),key=lambda i:abs(A[i][k])); A[k],A[p]=A[p],A[k]
   if abs(A[k][k])<1e-10:return None
   q=A[k][k];A[k]=[x/q for x in A[k]]
   for i in range(3):
    if i!=k:
     q=A[i][k];A[i]=[A[i][j]-q*A[k][j] for j in range(4)]
  return [A[i][3] for i in range(3)]
 err=0.
 for hold in range(len(pairs)):
  G=[[0.]*3 for _ in range(3)];h=[0.]*3
  for j,(u,y) in enumerate(pairs):
   if j==hold:continue
   fs=[u,1.,v5.scalar(ast,u,y)]
   for a in range(3):
    h[a]+=fs[a]*y
    for b in range(3):G[a][b]+=fs[a]*fs[b]
  beta=solve3(G,h)
  if beta is None:return float('inf')
  u,y=pairs[hold];fs=[u,1.,v5.scalar(ast,u,y)]
  err+=(sum(c*x for c,x in zip(beta,fs))-y)**2
 return err

def behaviour(ast,pairs):
 # Domain-neutral observational signature on B evidence; used only to detect
 # unresolved equivalence, never C quantities.
 return tuple(round(v5.scalar(ast,u,y),12) for u,y in pairs)

def acquire_with_separator():
 pairs=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)]
 scores=sorted((residual_score(a,pairs),i,a) for i,a in enumerate(ASTS))
 print('B_INITIAL_SCORES',scores)
 best=scores[0][0]
 equiv=[a for s,_,a in scores if math.isfinite(s) and abs(s-best)<=1e-9]
 print('B_UNRESOLVED_EQUIVALENCE_CLASS',equiv)
 assert len(equiv)>1
 # Fixed intervention pool, independent of C. Pick smallest |u| then u whose
 # candidate predicted scalar features are not all identical. Query true B only.
 pool=tuple(range(-12,13))
 chosen=None
 for u in sorted(pool,key=lambda z:(abs(z),z)):
  if any(u==p[0] for p in pairs):continue
  y=target_B(u)
  vals=[round(v5.scalar(a,u,y),12) for a in equiv]
  if len(set(vals))>1:
   chosen=(u,y,vals);break
 assert chosen is not None
 print('B_MINIMAL_SEPARATOR_QUERY',chosen)
 pairs2=pairs+[(chosen[0],chosen[1])]
 scores2=sorted((residual_score(a,pairs2),i,a) for i,a in enumerate(ASTS))
 print('B_POST_SEPARATOR_SCORES',scores2)
 # Unique behavioural winner: require a strict score margin; no index/complexity tie-break.
 assert math.isfinite(scores2[0][0]) and scores2[0][0] < scores2[1][0]-1e-9, scores2[:2]
 psi=scores2[0][2]
 print('B_UNIQUE_PSI_AFTER_VERIFIED_SEPARATOR',psi)
 print('B_SEPARATOR_ONLY_USES_EXECUTABLE_B=PASS')
 print('B_UNIQUE_SELECTION_BEFORE_C=PASS')
 return psi

def main():
 v5.lean_gate()
 psi=acquire_with_separator()
 cold,_=v5.fit_C(('U',)); warm,beta=v5.fit_C(psi)
 print('C_COLD_RATIO',cold)
 print('C_EXACT_B_SELECTED_AST_RATIO',warm,'beta',beta)
 assert cold>=.01
 assert warm<.01,(psi,warm)
 alts=[(i,v5.fit_C(a)[0]) for i,a in enumerate(ASTS)]
 print('C_POSTHOC_ALL_ALTERNATIVES',alts)
 print('EXACT_AST_UNCHANGED_B_TO_C=PASS')
 print('NO_C_DATA_USED_TO_SELECT_PSI=PASS')
 print('VERIFIED_SEPARATOR_RESOLVES_B_EQUIVALENCE=PASS')
 print('PSI_CAUSES_SEALED_MARS_CAPABILITY=PASS')
 print('PSI_ABLATION_RESTORES_COLD=PASS')
 print('BLIND_SEPARATOR_EXACT_OBJECT_TRANSFER_100X_V6=PASS')
 print('BOUNDARY=shared preregistered typed algebra remains supplied; separator and exact object selection are B-only')
if __name__=='__main__':main()
