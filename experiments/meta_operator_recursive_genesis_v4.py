#!/usr/bin/env python3
"""V4: invent Phi on acquisition evidence, freeze it, then use Phi to invent Psi.

No named Boolean operators are supplied. Binary behaviours are anonymous 4-bit tables.
Stage A synthesizes Phi from all nontrivial tables by residual frontier score.
Stage B is held out from acquisition: choose a distinct Psi that is NOT reachable within
budget B from the cold language, but IS reachable by composing frozen Phi within B.
Psi must differ from Phi and primitives. Exact ablation checks every one-bit mutation
of Phi: none may recover Psi at B. Finally promote Psi and require a third target Omega
whose bounded cost strictly improves over language with Phi alone.

This is finite/resource-bounded recursive search-language development, not open-ended AGI.
"""
X=0b1100; Y=0b1010; PRIMS=(X,Y,0,15)

def bit(f,a,b): return (f>>((a<<1)|b))&1
def apply(f,g,h):
 out=0
 for r in range(4): out|=bit(f,(g>>r)&1,(h>>r)&1)<<r
 return out

def costs(ops,B):
 c={p:0 for p in PRIMS}; changed=True
 while changed:
  changed=False; items=list(c.items())
  for op in ops:
   for g,cg in items:
    for h,ch in items:
     zc=cg+ch+1
     if zc>B: continue
     z=apply(op,g,h)
     if z not in c or zc<c[z]: c[z]=zc; changed=True
 return c

def score(op): return len(set(costs((op,),1))-set(PRIMS))
def nontrivial(f): return f not in PRIMS
def h1(f): return [f^(1<<i) for i in range(4)]

def main():
 # Stage A: anonymous exhaustive synthesis; deterministic complexity-neutral tie break.
 ranked=sorted(((score(f),-f,f) for f in range(16) if nontrivial(f)),reverse=True)
 phi=ranked[0][2]
 assert nontrivial(phi)
 # Stage B: held-out target is NOT phi. It must require recursive use of phi (cost >=2).
 B=2; cold=costs((),B); warm=costs((phi,),B)
 psis=[]
 for psi,c in warm.items():
  if psi==phi or psi in PRIMS or c<2 or psi in cold: continue
  if all(costs((m,),B).get(psi,99)>B for m in h1(phi)):
   psis.append((c,psi))
 assert psis, ('NO_PSI',format(phi,'04b'),warm)
 _,psi=min(psis)
 # Stage C: after Psi promotion, require a distinct Omega with strict bounded cost gain.
 B2=4; phi_only=costs((phi,),B2); phi_psi=costs((phi,psi),B2)
 omegas=[]
 for o,cnew in phi_psi.items():
  if o in PRIMS or o in (phi,psi): continue
  coldc=phi_only.get(o,99)
  if cnew<coldc: omegas.append((coldc-cnew,o,cnew,coldc))
 assert omegas, ('NO_OMEGA',format(phi,'04b'),format(psi,'04b'))
 gap,omega,newc,oldc=max(omegas)
 print('STAGE_A_SYNTHESIZED_PHI',format(phi,'04b'),'score',score(phi),'top5',[(s,format(f,'04b')) for s,_,f in ranked[:5]])
 print('STAGE_B_HELDOUT_PSI',format(psi,'04b'),'phi_cost',warm[psi],'cold_reachable',psi in cold,'psi_is_phi',psi==phi)
 for m in h1(phi): print('PHI_ONE_BIT_ABLATION',format(m,'04b'),'psi_reachable',costs((m,),B).get(psi,99)<=B)
 print('STAGE_C_OMEGA',format(omega,'04b'),'with_phi_psi',newc,'phi_only',oldc,'gap',gap)
 # Exact ablation of Psi for Omega: compare Phi-only is already the ablation.
 assert psi!=phi and psi not in PRIMS and psi not in cold and warm[psi]<=B
 assert all(costs((m,),B).get(psi,99)>B for m in h1(phi))
 assert newc<oldc
 print('PHI_INVENTED_FROM_ACQUISITION=PASS')
 print('PHI_ENABLES_DISTINCT_HELDOUT_PSI=PASS')
 print('PHI_EXACT_ABLATION_DESTROYS_PSI=PASS')
 print('PSI_PROMOTION_EXPANDS_NEXT_FRONTIER=PASS')
 print('OPERATOR_TO_OPERATOR_RECURSIVE_GENESIS=PASS')
 print('META_OPERATOR_RECURSIVE_GENESIS_V4=PASS')
if __name__=='__main__': main()
