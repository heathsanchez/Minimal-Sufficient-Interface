"""Find minimal shifted-constraint family cores for UNSAT saturated K4 orientations.

Blind local diagnostic. Each shifted family is one row-pair (t,u); no-triple and exact
agreement profile remain fixed. We enumerate subsets of the six shifted families and
report inclusion-minimal UNSAT cores for each previously UNSAT orientation.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from z3 import Distinct, If, Int, Or, Solver, Sum, sat, unsat

N=7
PAIRS=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
UNSAT_VECTORS={
    "3-2-2":[(2,2,3,3,2,2),(2,3,2,2,3,2)],
    "4-3-0":[(0,4,3,3,4,0),(4,0,3,3,0,4)],
    "5-2-0":[(0,2,5,5,2,0),(2,0,5,5,0,2),(2,5,0,0,5,2)],
}


def build(prefix, active):
    U=[[Int(f"{prefix}_{r}_{i}") for i in range(N)] for r in range(4)]
    c=[]
    for i in range(N): c.append(U[0][i]==i)
    for r in range(1,4):
        c.append(Distinct(U[r]))
        for i in range(N): c += [U[r][i]>=0,U[r][i]<N]
    for t,u in active:
        d=u-t
        for i in range(N): c.append(U[u][i] != U[t][(i+d)%N])
    for i in range(N):
        for a,b,d in itertools.combinations(range(4),3):
            c.append(Or(U[a][i]!=U[b][i],U[a][i]!=U[d][i]))
    return U,c


def agreement(U,a,b): return Sum([If(U[a][i]==U[b][i],1,0) for i in range(N)])


def status(vec, active, tag):
    U,c=build(tag,active); s=Solver(); s.set(timeout=10000); s.add(c)
    for pair,target in zip(PAIRS,vec): s.add(agreement(U,*pair)==target)
    r=s.check(); return str(r)


def minimal_cores(vec, tag):
    unsat_sets=[]
    for k in range(1,len(PAIRS)+1):
        for sub in itertools.combinations(PAIRS,k):
            ss=frozenset(sub)
            if any(core.issubset(ss) for core in unsat_sets): continue
            r=status(vec,sub,f"{tag}_{k}_{len(unsat_sets)}")
            if r=="unknown": raise RuntimeError(f"timeout for {tag} {sub}")
            if r=="unsat": unsat_sets.append(ss)
    return [sorted([list(p) for p in core]) for core in unsat_sets]


def main():
    results={}
    for typ,vectors in UNSAT_VECTORS.items():
        rows=[]
        for i,vec in enumerate(vectors):
            cores=minimal_cores(vec,f"{typ}_{i}")
            rows.append({"vector":list(vec),"minimal_unsat_cores":cores})
        results[typ]=rows
    out={"pair_families":[list(p) for p in PAIRS],"results":results}
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/shifted_orientation_core_probe.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__": main()
