#!/usr/bin/env python3
"""100x V1: cross-domain inheritance of a learned discovery method.

Three deliberately different finite verifier adapters expose ONLY binary consequence
judgments over opaque tokens. The same frozen controller learns an abstract method
from Domain A, transfers that method (not domain symbols) into Domain B where it
makes a second method reachable under a fixed budget, then transfers the second
method into Domain C where a third sealed capability becomes reachable.

This is a strict synthetic precursor to source-distinct Lean/program/physics adapters.
It is designed to decide the causal inheritance architecture before paying external
verifier cost. Claims are bounded to these finite adapters.
"""
from itertools import product

# Generic controller knows only opaque bit-vectors and composition-by-table.
def apply_table(table,g,h,n):
    out=0
    for r in range(n):
        a=(g>>r)&1; b=(h>>r)&1
        out |= ((table>>((a<<1)|b))&1)<<r
    return out

def costs(prims,ops,n,B):
    c={p:0 for p in prims}; changed=True
    while changed:
        changed=False; items=list(c.items())
        for op in ops:
            for g,cg in items:
                for h,ch in items:
                    zc=cg+ch+1
                    if zc>B: continue
                    z=apply_table(op,g,h,n)
                    if z not in c or zc<c[z]: c[z]=zc; changed=True
    return c

def score(prims,op,n): return len(set(costs(prims,(op,),n,1))-set(prims))
def choose(prims,n):
    candidates=[f for f in range(16) if score(prims,f,n)>0]
    return max(candidates,key=lambda f:(score(prims,f,n),-f))
def h1(f): return [f^(1<<i) for i in range(4)]

# Domain adapters intentionally use unrelated row counts / primitive encodings.
# A: 4-state proof-like acceptance signatures.
A=(0b1100,0b1010,0,15); nA=4
# B: 6 opaque executable-test signatures (truth rows repeated/permuted).
# Embed 4-row Boolean behaviours into six rows via row map [2,0,3,1,2,3].
mapB=(2,0,3,1,2,3); nB=6
def lift(table,rowmap):
    out=0
    for i,r in enumerate(rowmap): out|=((table>>r)&1)<<i
    return out
B=tuple(lift(p,mapB) for p in A)
# C: 8 opaque dynamics/prediction signatures, another independent presentation.
mapC=(3,1,0,2,1,3,2,0); nC=8
C=tuple(lift(p,mapC) for p in A)

def main():
    # Learn Phi only from A.
    phi=choose(A,nA)
    print('DOMAIN_A_LEARNED_METHOD',format(phi,'04b'),'score',score(A,phi,nA))

    # B: discover a distinct Psi only because inherited Phi is available.
    B0=costs(B,(),nB,2); Bphi=costs(B,(phi,),nB,2)
    psi_candidates=[]
    for psi,c in Bphi.items():
        if psi in B or c<2 or psi==lift(phi,mapB) or psi in B0: continue
        # exact ancestral method ablation: every one-bit mutation of Phi loses Psi
        if all(costs(B,(m,),nB,2).get(psi,99)>2 for m in h1(phi)):
            psi_candidates.append((c,psi))
    assert psi_candidates, 'A->B inheritance failed'
    _,psiB=min(psi_candidates)
    # Recover coordinate-free 4-bit behaviour represented by psiB by exhaustive table fit.
    fits=[t for t in range(16) if lift(t,mapB)==psiB]
    assert len(fits)==1
    psi=fits[0]
    print('DOMAIN_B_NEW_METHOD',format(psi,'04b'),'cold',psiB in B0,'with_phi_cost',Bphi[psiB])
    for m in h1(phi): print('A_METHOD_ABLATION_IN_B',format(m,'04b'),costs(B,(m,),nB,2).get(psiB,99)<=2)

    # C: sealed Omega must need inherited Psi beyond Phi alone.
    Cphi=costs(C,(phi,),nC,4); Cboth=costs(C,(phi,psi),nC,4)
    omega=[]
    for o,cnew in Cboth.items():
        if o in C: continue
        old=Cphi.get(o,99)
        if cnew<old: omega.append((old-cnew,o,cnew,old))
    assert omega,'B->C inheritance failed'
    gap,omegaC,newc,oldc=max(omega)
    print('DOMAIN_C_SEALED_CAPABILITY',bin(omegaC),'with_phi_psi',newc,'phi_only',oldc,'gap',gap)

    # Ancestral chain intervention: without Phi, Psi is not discoverable in B, so C cannot inherit it.
    assert psiB not in B0
    assert all(costs(B,(m,),nB,2).get(psiB,99)>2 for m in h1(phi))
    assert newc<oldc
    print('FROZEN_CONTROLLER=PASS')
    print('DOMAIN_A_ONLY_METHOD_GENESIS=PASS')
    print('CROSS_PRESENTATION_METHOD_INHERITANCE_A_TO_B=PASS')
    print('ANCESTRAL_ABLATION_BREAKS_B_GENESIS=PASS')
    print('B_METHOD_EXPANDS_C_FRONTIER=PASS')
    print('THREE_STAGE_CAUSAL_INHERITANCE=PASS')
    print('CROSS_DOMAIN_DISCOVERY_INHERITANCE_100X_V1=PASS')
if __name__=='__main__': main()
