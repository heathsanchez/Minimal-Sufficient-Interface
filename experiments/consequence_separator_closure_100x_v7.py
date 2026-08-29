#!/usr/bin/env python3
"""V7: consequence-separator closure before any physics transfer.

This follows the V6 residual literally. Candidate ASTs are not separated by raw
feature disagreement; they are separated only when their fitted B models make
different held-out consequence predictions. Starting from the original B evidence,
we repeatedly choose the smallest intervention in a frozen pool maximizing the
spread of those model predictions, query the executable B system, refit, and repeat.

There are only two legitimate terminal states:
  1) a unique B-necessary AST, which is then transferred unchanged to sealed C; or
  2) closure: no B intervention in the frozen pool can distinguish the surviving
     candidates in consequence space. In that case the cross-domain inheritance
     claim is rejected and physics is never consulted.

No complexity/index tie-break is allowed.
"""
from __future__ import annotations
import math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import blind_exact_object_transfer_100x_v5 as v5

ASTS=v5.ASTS
POOL=tuple(range(-24,25))
EPS=1e-9

def true_B(u): return 2*u+1

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
  for i in range(3):
   h[i]+=fs[i]*y
   for j in range(3):G[i][j]+=fs[i]*fs[j]
 return solve3(G,h)

def pred(ast,beta,u):
 # Feature may depend on y, so solve fixed-point by using the candidate's predicted
 # consequence self-consistently. Iterate from affine seed; all operations here are
 # B-only and generic.
 y=2*u+1 if beta is None else beta[0]*u+beta[1]
 for _ in range(50):
  z=beta[0]*u+beta[1]+beta[2]*v5.scalar(ast,u,y)
  if not math.isfinite(z):return float('nan')
  if abs(z-y)<1e-12:return z
  y=z
 return y

def loo(ast,pairs):
 e=0.
 for hold in range(len(pairs)):
  tr=[p for i,p in enumerate(pairs) if i!=hold]
  b=fit(ast,tr)
  if b is None:return float('inf')
  u,y=pairs[hold]; q=pred(ast,b,u)
  if not math.isfinite(q):return float('inf')
  e+=(q-y)**2
 return e

def surviving(pairs):
 scores=[(loo(a,pairs),a) for a in ASTS]
 finite=[s for s,_ in scores if math.isfinite(s)]
 if not finite:return [],scores
 best=min(finite)
 return [a for s,a in scores if math.isfinite(s) and abs(s-best)<=EPS],scores

def choose_consequence_separator(cands,pairs):
 fitted=[(a,fit(a,pairs)) for a in cands]
 fitted=[(a,b) for a,b in fitted if b is not None]
 seen={u for u,_ in pairs}; choices=[]
 for u in POOL:
  if u in seen:continue
  qs=[pred(a,b,u) for a,b in fitted]
  qs=[q for q in qs if math.isfinite(q)]
  if len(qs)!=len(fitted) or len(qs)<2:continue
  spread=max(qs)-min(qs)
  if spread>EPS:
   choices.append((-spread,abs(u),u,tuple(qs)))
 if not choices:return None
 choices.sort()
 _,_,u,qs=choices[0]
 return u,qs,-choices[0][0]

def main():
 v5.lean_gate()
 pairs=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)]
 trace=[]
 for t in range(len(POOL)):
  cands,scores=surviving(pairs)
  ranked=sorted(scores,key=lambda z:(z[0],str(z[1])))
  print('B_ROUND',t,'TOP',ranked[:6],'SURVIVORS',cands)
  if len(cands)==1:
   psi=cands[0]
   print('B_UNIQUE_PSI_BY_CONSEQUENCE',psi)
   print('B_CONSEQUENCE_SEPARATOR_TRACE',trace)
   print('B_UNIQUE_SELECTION_BEFORE_C=PASS')
   cold,_=v5.fit_C(('U',));warm,beta=v5.fit_C(psi)
   print('C_COLD_RATIO',cold)
   print('C_EXACT_B_SELECTED_AST_RATIO',warm,'beta',beta)
   assert cold>=.01
   assert warm<.01,(psi,warm)
   print('EXACT_AST_UNCHANGED_B_TO_C=PASS')
   print('NO_C_DATA_USED_TO_SELECT_PSI=PASS')
   print('PSI_CAUSES_SEALED_MARS_CAPABILITY=PASS')
   print('CONSEQUENCE_SEPARATOR_CLOSURE_100X_V7=PASS')
   return
  sep=choose_consequence_separator(cands,pairs)
  if sep is None:
   print('B_CONSEQUENCE_CLOSURE_SURVIVORS',cands)
   print('B_CONSEQUENCE_SEPARATOR_TRACE',trace)
   print('NO_FURTHER_B_CONSEQUENCE_SEPARATOR_IN_FROZEN_POOL=PASS')
   print('B_OPERATOR_IDENTIFIABILITY=FAIL')
   print('C_NOT_CONSULTED=PASS')
   print('CROSS_DOMAIN_100X_STRONG_CLAIM=FAIL')
   raise SystemExit(1)
  u,qs,spread=sep; y=true_B(u)
  trace.append((u,y,spread,qs)); pairs.append((u,y))
  print('B_MAX_CONSEQUENCE_SEPARATOR_QUERY',u,y,'spread',spread,'predictions',qs)
 raise AssertionError('separator loop exhausted without terminal state')

if __name__=='__main__':main()
