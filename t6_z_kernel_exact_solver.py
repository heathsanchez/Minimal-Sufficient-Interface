"""Exact reduced solver for the live uniform T6 Z-kernel frontier.

For fixed canonical D and normalized A, solve directly for the seven inverse rows
Z_t = U_t^{-1}.  This deliberately drops the full magma and retains only the
coordinates already proved to attach to the live T6 frontier.

Constraints:
  1. every Z_t is a permutation of Z_7 and Z_t(0) != 0 (Badness);
  2. for every target s, t -> Z_t(s)+t is a permutation (shifted Latin law);
  3. every target has exactly two row-pair agreements, hence profile (2,2,1,1,1);
  4. exact bidirectional T6 pair-kernel law:
       Z_t(s)=Z_u(s)  iff  F_t(Z_t^{-1}(s))=F_u(Z_u^{-1}(s)),
     where F_t(q)=D(q-t)-A(q).

The solver is finite and exact modulo the underlying SMT decision procedure.  SAT
models are independently rechecked by pure Python before being accepted.
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

N = 7
CANONICAL_D = ('0125634','0145236','1023546','1024356')
PERMS = list(itertools.permutations(range(N)))
AS = [p for p in PERMS if p[0] == 0]


def parse(s: str):
    return tuple(map(int, s))


def F(D, A, t, q):
    return (D[(q - t) % N] - A[q]) % N


def edge_graph(D, A):
    images = [set(F(D, A, t, q) for q in range(N)) for t in range(N)]
    return tuple((t,u) for t in range(N) for u in range(t+1,N)
                 if images[t].isdisjoint(images[u]))


def extreme_cases():
    out=[]
    for dname in CANONICAL_D:
        D=parse(dname)
        for ai,A in enumerate(AS):
            edges=edge_graph(D,A)
            if len(edges) >= 6:
                out.append((dname,ai,A,edges))
    assert len(out)==40
    assert sum(len(x[3])==7 for x in out)==12
    assert sum(len(x[3])==6 for x in out)==28
    return out


def inverse_row(z):
    inv=[None]*N
    for s,v in enumerate(z):
        inv[v]=s
    return tuple(inv)


def verify_model(D,A,Z):
    assert len(Z)==N
    for t,z in enumerate(Z):
        assert sorted(z)==list(range(N))
        assert z[0] != 0
    for s in range(N):
        assert len({(Z[t][s]+t)%N for t in range(N)})==N
        eq=sum(Z[t][s]==Z[u][s] for t in range(N) for u in range(t+1,N))
        assert eq==2
    inv=[inverse_row(z) for z in Z]
    for s in range(N):
        for t in range(N):
            for u in range(t+1,N):
                left=Z[t][s]==Z[u][s]
                rt=F(D,A,t,inv[t][s])
                ru=F(D,A,u,inv[u][s])
                assert left == (rt==ru), (s,t,u,left,rt,ru)
    return True


def solve_case(dname, ai, timeout_ms=120000):
    try:
        import z3
    except Exception as exc:
        raise SystemExit(f'z3-solver is required: {exc}')
    D=parse(dname); A=AS[ai]
    S=z3.Solver()
    S.set(timeout=timeout_ms)
    Z=[[z3.Int(f'z_{t}_{s}') for s in range(N)] for t in range(N)]
    for t in range(N):
        for s in range(N):
            S.add(Z[t][s] >= 0, Z[t][s] < N)
        S.add(z3.Distinct(*Z[t]))
        S.add(Z[t][0] != 0)
    for s in range(N):
        S.add(z3.Distinct(*[((Z[t][s]+t) % N) for t in range(N)]))
        agreements=[]
        for t in range(N):
            for u in range(t+1,N):
                agreements.append(z3.If(Z[t][s]==Z[u][s],1,0))
        S.add(z3.Sum(agreements)==2)

    # rho_t(s) = F_t(q) for the unique q with Z_t(q)=s.
    rho=[[None]*N for _ in range(N)]
    for t in range(N):
        for s in range(N):
            rho[t][s]=z3.Sum(*[
                z3.If(Z[t][q]==s, F(D,A,t,q), 0) for q in range(N)
            ])
    for s in range(N):
        for t in range(N):
            for u in range(t+1,N):
                S.add((Z[t][s]==Z[u][s]) == (rho[t][s]==rho[u][s]))

    started=time.time(); status=S.check(); elapsed=time.time()-started
    rec={'D':dname,'A_index':ai,'A':list(A),'status':str(status),'seconds':elapsed,
         'forbidden_edges':[list(e) for e in edge_graph(D,A)]}
    if status==z3.sat:
        m=S.model()
        rows=tuple(tuple(m.eval(Z[t][s]).as_long() for s in range(N)) for t in range(N))
        verify_model(D,A,rows)
        rec['Z']=[list(r) for r in rows]
        rec['pure_python_recheck']=True
    elif status==z3.unknown:
        rec['reason_unknown']=S.reason_unknown()
    return rec


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--case',type=int)
    ap.add_argument('--all-extreme',action='store_true')
    ap.add_argument('--timeout-ms',type=int,default=120000)
    ap.add_argument('--output',default='artifacts/t6_z_kernel_exact_solver.json')
    args=ap.parse_args()
    cases=extreme_cases()
    if args.case is not None:
        selected=[(args.case,cases[args.case])]
    elif args.all_extreme:
        selected=list(enumerate(cases))
    else:
        raise SystemExit('use --case N or --all-extreme')
    results=[]
    for idx,(dname,ai,A,edges) in selected:
        r=solve_case(dname,ai,args.timeout_ms); r['case_index']=idx
        results.append(r)
        print(json.dumps(r,sort_keys=True))
    summary={
        'cases':len(results),
        'sat':sum(r['status']=='sat' for r in results),
        'unsat':sum(r['status']=='unsat' for r in results),
        'unknown':sum(r['status']=='unknown' for r in results),
        'results':results,
    }
    if args.all_extreme:
        Path(args.output).parent.mkdir(exist_ok=True)
        Path(args.output).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:summary[k] for k in ('cases','sat','unsat','unknown')},sort_keys=True))
    print('T6_Z_KERNEL_EXACT_SOLVER_COMPLETE')

if __name__=='__main__':
    main()
