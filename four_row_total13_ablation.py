"""Causal ablation for the four-row total-agreement=13 exclusion.

Blind local diagnostic: identify which constraint family is necessary for UNSAT.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from z3 import Distinct, If, Int, Or, Solver, Sum, sat, unsat

N=7
ROWS=4
PAIRS=tuple(itertools.combinations(range(ROWS),2))


def build(prefix:str, shifted:bool, no_triple:bool):
    U=[[Int(f"{prefix}_{r}_{i}") for i in range(N)] for r in range(ROWS)]
    c=[]
    for i in range(N): c.append(U[0][i]==i)
    for r in range(1,ROWS):
        c.append(Distinct(U[r]))
        for i in range(N): c += [U[r][i]>=0,U[r][i]<N]
    if shifted:
        for t,u in PAIRS:
            d=u-t
            for i in range(N): c.append(U[u][i] != U[t][(i+d)%N])
    if no_triple:
        for i in range(N):
            for a,b,d in itertools.combinations(range(ROWS),3):
                c.append(Or(U[a][i]!=U[b][i],U[a][i]!=U[d][i]))
    return U,c


def total(U):
    return Sum([If(U[a][i]==U[b][i],1,0) for a,b in PAIRS for i in range(N)])


def check(name:str, shifted:bool, no_triple:bool):
    U,c=build(name,shifted,no_triple)
    s=Solver(); s.add(c); s.add(total(U)==13)
    r=s.check()
    out={"status":str(r),"shifted":shifted,"no_triple":no_triple}
    if r==sat:
        m=s.model()
        counts=[]
        for a,b in PAIRS:
            counts.append(sum(1 for i in range(N) if m.eval(U[a][i]).as_long()==m.eval(U[b][i]).as_long()))
        out["pair_agreement_counts"]=counts
        out["rows"]=[[m.eval(U[r][i]).as_long() for i in range(N)] for r in range(ROWS)]
    return out


def main():
    cases={
        "full": check("full",True,True),
        "without_shifted": check("noshift",False,True),
        "without_no_triple": check("notriple",True,False),
        "permutations_only": check("perm",False,False),
    }
    out={"target_total":13,"cases":cases}
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/four_row_total13_ablation.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))
    if cases["full"]["status"] != "unsat":
        raise SystemExit("full total-13 exclusion failed")

if __name__=="__main__": main()
