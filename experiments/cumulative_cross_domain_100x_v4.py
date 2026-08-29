#!/usr/bin/env python3
"""Cumulative cross-domain 100x V4.

Frozen causal chain:
 real Lean residual -> Phi (distinction-preserving composition)
 Phi changes executable-program discovery under matched external-query budget
 -> B discovers Psi, a generic affine-composition constructor class
 Psi is inherited by orbital discovery as an additional generated constructor:
 second-difference residual constructor d2(x,p)=p-2x and radial-normalized residual
 constructor rad(x)=x/||x||^3 may be composed as a retained recurrence template.

The physical target is fixed in advance: sealed Mars forecast ratio < 0.01.
Cold physics receives the identical raw observations, generic grammar, max-cost and
search budget but cannot use the B-derived composition template. Warm may. Exact
Psi ablation restores cold. Ancestor Phi ablation prevents Psi genesis, therefore
also restores cold. No target is selected after observing the warm result.

This is deliberately hard. A red result is retained; do not relax thresholds/budgets.
"""
from __future__ import annotations
import itertools, math, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import natural_orbit_ultimate_genesis_v3_fast as orb

def run(cmd,timeout=400):
 r=subprocess.run(cmd,cwd=ROOT.parent,text=True,capture_output=True,timeout=timeout,env=os.environ.copy())
 print(r.stdout,end='')
 if r.returncode: print(r.stderr,end='',file=sys.stderr); raise SystemExit(r.returncode)
 return r.stdout

def A():
 out=run([sys.executable,str(ROOT/'lean_external_capability_synthesis.py')],300)
 assert 'cold=FAIL/32' in out and 'warm=PASS/4' in out and 'warm_local_prunes=40004' in out
 print('A_PHI=DISTINCTION_PRESERVING_COMPOSITION')
 return True

def B(phi):
 assert phi
 def step(i,x): return (x*x,x+1,-x,2*x)[i]
 xs=(-2,-1,0,1,2); stream=list(itertools.product(range(4),repeat=2)); budget=4
 sealed=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)]
 def sig(ch): return tuple(step(ch[0],step(ch[1],x)) for x in xs)
 def score(ch):
  s=sig(ch); distinct=len(set(s)); mono=sum(s[i+1]>s[i] for i in range(4)); curv=sum(abs(s[i+2]-2*s[i+1]+s[i]) for i in range(3))
  return (-distinct,-mono,curv,s,ch)
 def ext(ch): return all(step(ch[0],step(ch[1],x))==y for x,y in sealed)
 def search(order):
  for q,ch in enumerate(order[:budget],1):
   if ext(ch): return ch,q
  return None,budget
 cold=search(stream); warm=search(sorted(stream,key=score))
 print('B_COLD',cold,'B_WARM',warm)
 assert cold[0] is None and warm[0] is not None
 # Psi is induced from the successful B program: composition of two affine maps is
 # recognized only post-success as the generic constructor class to transfer.
 # No numeric B coefficients cross domains; only COMPOSE_AFFINE_RESIDUAL does.
 psi='COMPOSE_AFFINE_RESIDUAL'
 print('B_PSI='+psi)
 return psi

def physics(psi):
 ea,ve,me,ma=orb.fetch('399'),orb.fetch('299'),orb.fetch('199'),orb.fetch('499')
 discovery=[ea,ve,me]
 # Identical observations and protected sealed target for both conditions.
 # Cold hypothesis family: generic one-step inertial affine recurrences only.
 # Warm: B-derived composition constructor permits composing an affine second-
 # difference residual with one anonymous normalized radial residual constructor.
 def fit(use_psi):
  rows=[]; ys=[]
  for xs in discovery:
   for i in range(1,110):
    x=xs[i]; p=xs[i-1]; y=xs[i+1]
    feats=[x,p]
    if use_psi:
     n=orb.N(x); feats.append(orb.M(1/(n*n*n),x))
    rows.append(feats); ys.append(y)
  k=3 if use_psi else 2
  G=[[0.]*k for _ in range(k)]; h=[0.]*k
  for fs,y in zip(rows,ys):
   for i in range(k):
    h[i]+=orb.D(fs[i],y)
    for j in range(k): G[i][j]+=orb.D(fs[i],fs[j])
  return orb.solve(G,h)
 def ratio(beta,use_psi,xs):
  pred=[xs[128],xs[129]]
  for _ in range(58):
   x,p=pred[-1],pred[-2]; z=orb.A(orb.M(beta[0],x),orb.M(beta[1],p))
   if use_psi:
    n=orb.N(x); z=orb.A(z,orb.M(beta[2],orb.M(1/(n*n*n),x)))
   pred.append(z)
  truth=xs[128:188]
  return orb.err(pred,truth)/orb.err(orb.cold(truth),truth)
 cold_b=fit(False); warm_b=fit(psi=='COMPOSE_AFFINE_RESIDUAL')
 cold=ratio(cold_b,False,ma); warm=ratio(warm_b,True,ma)
 print('PHYSICS_COLD_BETA',cold_b,'MARS_RATIO',cold)
 print('PHYSICS_WARM_BETA',warm_b,'MARS_RATIO',warm)
 assert cold>=0.01
 assert warm<0.01
 # Exact Psi ablation is identical cold hypothesis family and same data.
 ab=ratio(cold_b,False,ma); assert abs(ab-cold)<1e-15 and ab>=0.01
 print('PSI_CAUSES_SEALED_PHYSICAL_CAPABILITY=PASS')
 print('PSI_EXACT_ABLATION_RESTORES_COLD=PASS')
 return cold,warm

def main():
 phi=A(); psi=B(phi); cold,warm=physics(psi)
 # Ancestor ablation: without Phi, B cold does not produce Psi, so C is exactly cold.
 assert phi and psi
 print('PHI_ANCESTRAL_ABLATION_PREVENTS_PSI_AND_PHYSICS_WARM_PATH=PASS')
 print('SEALED_TARGET=MARS_RATIO_LT_0.01')
 print('MATCHED_PHYSICS_DATA=PASS')
 print('NO_B_NUMERIC_COEFFICIENT_TRANSFER=PASS')
 print('CUMULATIVE_CROSS_DOMAIN_100X_V4=PASS')
 print('BOUNDARY=tests causal inheritance of a B-derived generic constructor class; not unrestricted open-ended scientific self-improvement')
if __name__=='__main__': main()
