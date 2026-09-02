"""Test the four saturated K4 agreement-profile types against full shifted constraints.

The probe is blind to the global equation target. Because shifted constraints depend on row
indices, every distinct orientation under S4 is tested, not only one canonical profile.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from z3 import Distinct, If, Int, Or, Solver, Sum, sat

N=7
EDGE_ORDER=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
TYPES=((7,0,0),(5,2,0),(4,3,0),(3,2,2))


def edge_index(a,b):
    if a>b: a,b=b,a
    return EDGE_ORDER.index((a,b))


def base_vector(t):
    a,b,c=t
    return (a,b,c,c,b,a)


def orient(v,p):
    return tuple(v[edge_index(p[a],p[b])] for a,b in EDGE_ORDER)


def orientations(t):
    v=base_vector(t)
    return sorted(set(orient(v,p) for p in itertools.permutations(range(4))))


def build(prefix):
    U=[[Int(f"{prefix}_{r}_{i}") for i in range(N)] for r in range(4)]
    c=[]
    for i in range(N): c.append(U[0][i]==i)
    for r in range(1,4):
        c.append(Distinct(U[r]))
        for i in range(N): c += [U[r][i]>=0,U[r][i]<N]
    for t,u in EDGE_ORDER:
        d=u-t
        for i in range(N): c.append(U[u][i] != U[t][(i+d)%N])
    for i in range(N):
        for a,b,d in itertools.combinations(range(4),3):
            c.append(Or(U[a][i]!=U[b][i],U[a][i]!=U[d][i]))
    return U,c


def agreement(U,a,b): return Sum([If(U[a][i]==U[b][i],1,0) for i in range(N)])


def test_vector(vec,tag):
    U,c=build(tag)
    s=Solver(); s.set(timeout=30000); s.add(c)
    for (a,b),target in zip(EDGE_ORDER,vec): s.add(agreement(U,a,b)==target)
    r=s.check()
    out={"vector":list(vec),"status":str(r)}
    if r==sat:
        m=s.model(); out["rows"]=[[m.eval(U[r][i]).as_long() for i in range(N)] for r in range(4)]
    return out


def main():
    results={}
    for t in TYPES:
        key="-".join(map(str,t)); rows=[]
        for j,v in enumerate(orientations(t)):
            rows.append(test_vector(v,f"p_{key}_{j}"))
        results[key]={"orientation_count":len(rows),"sat_count":sum(x["status"]=="sat" for x in rows),"orientations":rows}
    out={"types":results}
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/shifted_profile_orientation_probe.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:{"orientation_count":v["orientation_count"],"sat_count":v["sat_count"]} for k,v in results.items()},indent=2,sort_keys=True))
    if any(x["status"]=="unknown" for v in results.values() for x in v["orientations"]):
        raise SystemExit("orientation probe timed out")

if __name__=="__main__": main()
