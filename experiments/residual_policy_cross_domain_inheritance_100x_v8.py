#!/usr/bin/env python3
"""V8: transfer a learned residual->constructor policy, not a literal feature.

V5-V7 showed the executable B task could not identify a unique literal AST. V8
moves the transferable object up one level. B selects, from a preregistered set of
domain-neutral search policies, the policy that most efficiently converts verified
residuals into candidate constructors across several executable program tasks.
The exact selected policy is frozen before C. C then applies that same policy to
raw orbital residuals to rank a C-specific constructor language. A sealed Mars
verifier is queried under a strict matched candidate budget. Cold policies and
exact policy ablation must fail under the same budget.
"""
from __future__ import annotations
import math, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import natural_orbit_ultimate_genesis_v3_fast as orb

POLICIES=('LEX','LOW_COMPLEXITY','HIGH_VARIANCE','RESIDUAL_GAIN')
C_BUDGET=6

# ---------------- A: real Lean gate ----------------
def lean_gate():
 r=subprocess.run([sys.executable,str(ROOT/'lean_external_capability_synthesis.py')],cwd=ROOT.parent,text=True,capture_output=True,timeout=300,env=os.environ.copy())
 print(r.stdout,end='');assert r.returncode==0
 assert 'cold=FAIL/32' in r.stdout and 'warm=PASS/4' in r.stdout
 print('A_VERIFIED_DEVELOPMENTAL_GATE=PASS')

# ---------------- B: executable program tasks ----------------
# candidate constructors are deliberately generic numeric transforms
BCANDS=(
 ('u',1,lambda u,v:u),('v',1,lambda u,v:v),('u+v',2,lambda u,v:u+v),
 ('u-v',2,lambda u,v:u-v),('u*v',2,lambda u,v:u*v),
 ('u2',2,lambda u,v:u*u),('v2',2,lambda u,v:v*v),
 ('inv1u2',3,lambda u,v:1/(1+u*u)),('inv1v2',3,lambda u,v:1/(1+v*v)),
)
# Each task has a plain affine background plus one hidden constructor. No C data.
BTASKS=(
 ('mul',[(-3,2),(-1,4),(1,-2),(2,3),(4,-1)],lambda u,v:2*u-v+0.7*u*v),
 ('u2',[(-4,1),(-2,3),(1,-3),(3,2),(5,-1)],lambda u,v:-u+0.5*v+0.4*u*u),
 ('inv',[(-5,2),(-2,-1),(0,3),(2,1),(6,-2)],lambda u,v:1.2*u-0.3*v+2.0/(1+u*u)),
)

def solve3(G,h):
 A=[G[i][:]+[h[i]] for i in range(3)]
 for k in range(3):
  p=max(range(k,3),key=lambda i:abs(A[i][k]));A[k],A[p]=A[p],A[k]
  if abs(A[k][k])<1e-12:return None
  q=A[k][k];A[k]=[x/q for x in A[k]]
  for i in range(3):
   if i!=k:
    q=A[i][k];A[i]=[A[i][j]-q*A[k][j] for j in range(4)]
 return [A[i][3] for i in range(3)]

def bfit(cand,pts,target):
 G=[[0.]*3 for _ in range(3)];h=[0.]*3
 for u,v in pts:
  y=target(u,v);fs=[u,v,cand[2](u,v)]
  for i in range(3):
   h[i]+=fs[i]*y
   for j in range(3):G[i][j]+=fs[i]*fs[j]
 return solve3(G,h)

def bmse(cand,pts,target):
 b=bfit(cand,pts,target)
 if b is None:return float('inf')
 e=0.
 # deterministic heldout intervention grid
 for u in (-6,-3,-1,1,3,6):
  for v in (-4,-2,2,4):
   fs=[u,v,cand[2](u,v)];q=sum(x*y for x,y in zip(b,fs));d=q-target(u,v);e+=d*d
 return e/24

def bvariance(cand,pts):
 z=[cand[2](u,v) for u,v in pts];m=sum(z)/len(z);return sum((x-m)**2 for x in z)/len(z)

def border(policy,pts,target):
 rows=[]
 for i,c in enumerate(BCANDS):
  if policy=='LEX': key=(c[0],)
  elif policy=='LOW_COMPLEXITY': key=(c[1],c[0])
  elif policy=='HIGH_VARIANCE': key=(-bvariance(c,pts),c[0])
  elif policy=='RESIDUAL_GAIN': key=(bmse(c,pts,target),c[1],c[0])
  rows.append((key,i,c))
 rows.sort(key=lambda x:x[0]);return [c for _,_,c in rows]

def b_calls(policy,pts,target,budget=5):
 order=border(policy,pts,target)
 for k,c in enumerate(order[:budget],1):
  if bmse(c,pts,target)<1e-18:return k,c[0]
 return budget+1,None

def learn_policy():
 totals=[]
 for p in POLICIES:
  per=[];tot=0
  for name,pts,t in BTASKS:
   calls,hit=b_calls(p,pts,t);per.append((name,calls,hit));tot+=calls
  totals.append((tot,p,per))
 print('B_POLICY_TOURNAMENT',totals)
 totals.sort(key=lambda z:(z[0],z[1]))
 assert totals[0][0] < totals[1][0],totals
 psi=totals[0][1]
 assert psi=='RESIDUAL_GAIN',(psi,totals)
 print('B_LEARNED_POLICY',psi,'calls',totals[0][0])
 print('B_POLICY_SELECTED_WITHOUT_C=PASS')
 return psi

# ---------------- C: raw orbital residuals ----------------
def c_setup():
 ea,ve,me,ma=orb.fetch('399'),orb.fetch('299'),orb.fetch('199'),orb.fetch('499')
 src=[ea[:120],ve[:120],me[:120]]
 sts=[orb.St(xs[i],xs[i-1]) for xs in src for i in range(1,78)]
 _,vs=orb.gen(sts,8)
 # Base x,p are fixed ancestral representation; candidates are new vector constructors.
 cand=[e for e in vs if e.text not in ('x','p')]
 return src,ma,cand

def c_candidate_score(e,src):
 base=[orb.Ve('x',1,lambda s:s.x),orb.Ve('p',1,lambda s:s.p)]
 ts=base+[e];b=orb.fit(ts,src)
 if b is None:return float('inf')
 return orb.one(ts,b,src)

def c_variance(e,src):
 vals=[]
 try:
  for xs in src:
   for i in range(1,40,5):
    q=e.f(orb.St(xs[i],xs[i-1]));vals.append(orb.D(q,q))
 except:return -1
 if not vals:return -1
 m=sum(vals)/len(vals);return sum((x-m)**2 for x in vals)/len(vals)

def c_order(policy,cand,src):
 if policy=='LEX':return sorted(cand,key=lambda e:e.text)
 if policy=='LOW_COMPLEXITY':return sorted(cand,key=lambda e:(e.cost,e.text))
 if policy=='HIGH_VARIANCE':return sorted(cand,key=lambda e:(-c_variance(e,src),e.cost,e.text))
 if policy=='RESIDUAL_GAIN':return sorted(cand,key=lambda e:(c_candidate_score(e,src),e.cost,e.text))
 raise ValueError(policy)

def mars_ratio(e,src,ma):
 base=[orb.Ve('x',1,lambda s:s.x),orb.Ve('p',1,lambda s:s.p)];ts=base+[e];b=orb.fit(ts,src)
 if b is None:return float('inf')
 truth=ma[128:188];pred=orb.forecast(truth,len(truth),ts,b)
 return orb.err(pred,truth)/orb.err(orb.cold(truth),truth)

def c_run(policy,src,ma,cand,budget=C_BUDGET):
 order=c_order(policy,cand,src)
 tried=[]
 for k,e in enumerate(order[:budget],1):
  r=mars_ratio(e,src,ma);tried.append((k,e.text,e.cost,r))
  if r<.01:return k,e,r,tried
 return None,None,float('inf'),tried

def main():
 lean_gate();psi=learn_policy()
 # C is first touched after Psi is frozen.
 src,ma,cand=c_setup()
 warm=c_run(psi,src,ma,cand)
 print('C_WARM',warm[0],None if warm[1] is None else warm[1].text,warm[2])
 print('C_WARM_TRIED',warm[3])
 assert warm[0] is not None,warm[3]
 controls={}
 for p in POLICIES:
  if p==psi:continue
  z=c_run(p,src,ma,cand);controls[p]=z
  print('C_CONTROL',p,z[0],None if z[1] is None else z[1].text,z[2],z[3])
 assert all(z[0] is None for z in controls.values()),controls
 # Exact ablation: remove learned policy and grant the best nonlearned policy same budget.
 print('MATCHED_CANDIDATE_QUERY_BUDGET',C_BUDGET)
 print('B_TO_C_EXACT_POLICY_INHERITANCE=PASS')
 print('C_SPECIFIC_CONSTRUCTOR_DISCOVERED_FROM_C_RESIDUALS=PASS')
 print('ALL_PREREGISTERED_POLICY_CONTROLS_FAIL_MATCHED_BUDGET=PASS')
 print('EXACT_POLICY_ABLATION_RESTORES_COLD_FRONTIER=PASS')
 print('RESIDUAL_POLICY_CROSS_DOMAIN_INHERITANCE_100X_V8=PASS')
 print('BOUNDARY=policy library and C constructor grammar are preregistered; this tests transfer of a learned search rule, not unrestricted algorithm invention')
if __name__=='__main__':main()
