#!/usr/bin/env python3
"""Adversarial audit of cumulative_cross_domain_100x_v4.

Attacks the strongest alternative explanation: V4's B->C bridge may be encoded by
hand because Psi is a post-success string and physics maps that string directly to
a physics-specific radial feature. This audit tests whether B evidence identifies
that feature against matched alternatives. It MUST fail if B provides no evidence
that discriminates among physics constructors.
"""
from __future__ import annotations
import itertools, math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import natural_orbit_ultimate_genesis_v3_fast as orb

# Reproduce B evidence only.
def B_evidence():
 def step(i,x): return (x*x,x+1,-x,2*x)[i]
 xs=(-2,-1,0,1,2); stream=list(itertools.product(range(4),repeat=2)); budget=4
 sealed=[(-3,-5),(-1,-1),(0,1),(2,5),(5,11)]
 def sig(ch): return tuple(step(ch[0],step(ch[1],x)) for x in xs)
 def score(ch):
  s=sig(ch); return (-len(set(s)),-sum(s[i+1]>s[i] for i in range(4)),sum(abs(s[i+2]-2*s[i+1]+s[i]) for i in range(3)),s,ch)
 def ext(ch): return all(step(ch[0],step(ch[1],x))==y for x,y in sealed)
 warm=sorted(stream,key=score)
 hit=next((ch for ch in warm[:budget] if ext(ch)),None)
 assert hit is not None
 return {'hit':hit,'signature':sig(hit),'score':score(hit)}

# Candidate C constructors are anonymous and all equally compatible with the B
# observation unless a derivation from B evidence says otherwise.
def physics_candidates():
 return {
  'k0': lambda x,p: x,
  'k1': lambda x,p: p,
  'k2': lambda x,p: orb.M(1/(orb.N(x)**3),x),
  'k3': lambda x,p: orb.M(1/max(orb.N(x),1e-12),x),
  'k4': lambda x,p: orb.S(x,p),
  'k5': lambda x,p: orb.A(x,p),
 }

def fit_extra(f):
 ea,ve,me,ma=orb.fetch('399'),orb.fetch('299'),orb.fetch('199'),orb.fetch('499'); discovery=[ea,ve,me]
 rows=[];ys=[]
 for xs in discovery:
  for i in range(1,110):
   x=xs[i];p=xs[i-1];rows.append([x,p,f(x,p)]);ys.append(xs[i+1])
 G=[[0.]*3 for _ in range(3)];h=[0.]*3
 for fs,y in zip(rows,ys):
  for i in range(3):
   h[i]+=orb.D(fs[i],y)
   for j in range(3):G[i][j]+=orb.D(fs[i],fs[j])
 b=orb.solve(G,h)
 if b is None:return float('inf')
 pred=[ma[128],ma[129]]
 for _ in range(58):
  x,p=pred[-1],pred[-2];z=(0.,0.,0.)
  for c,v in zip(b,[x,p,f(x,p)]):z=orb.A(z,orb.M(c,v))
  pred.append(z)
 truth=ma[128:188]
 return orb.err(pred,truth)/orb.err(orb.cold(truth),truth)

def main():
 ev=B_evidence(); print('B_EVIDENCE',ev)
 # Critical identification test. There is no B-derived map from its scalar affine
 # signature to one of these vector constructors. Therefore all are tied BEFORE C
 # data are consulted. Choosing k2 is extra experimental knowledge.
 names=tuple(physics_candidates())
 b_support={n:0 for n in names}
 print('B_ONLY_SUPPORT_FOR_C_CONSTRUCTORS',b_support)
 assert len(set(b_support.values()))==1
 print('B_DOES_NOT_IDENTIFY_PHYSICS_CONSTRUCTOR=PASS')
 # Show that C data itself makes the radial inverse-cube option special; this is
 # useful physics evidence, but it is not evidence that B discovered that option.
 ratios={n:fit_extra(f) for n,f in physics_candidates().items()}
 print('C_CONSTRUCTOR_MARS_RATIOS',ratios)
 winner=min(ratios,key=ratios.get); print('C_DATA_WINNER',winner,ratios[winner])
 assert winner=='k2' and ratios['k2']<.01
 # The V4 claimed bridge is therefore not identified by B evidence.
 print('HAND_DESIGNED_BRIDGE_ALTERNATIVE_EXPLANATION=SURVIVES')
 print('CUMULATIVE_100X_V4_STRONG_INTERPRETATION=FAIL')
 print('VALID_REMAINDER=V4 demonstrates a useful constructor added to C, but B did not causally select its physics-specific content')
 # Exit nonzero deliberately: adversarial gate is red until B evidence itself
 # selects the transferred constructor among preregistered alternatives.
 raise SystemExit(1)
if __name__=='__main__':main()
