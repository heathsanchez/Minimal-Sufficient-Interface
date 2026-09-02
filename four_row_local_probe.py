"""Exact four-row local probe for the next recursive residual.

This script is intentionally blind to E677/E255. It studies only the local permutation
constraints compiled by the controller. Z3 is used as a finite exact constraint solver.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from z3 import And, Distinct, If, Int, Optimize, Or, Sum, Solver, sat, unsat

N = 7
ROWS = 4


def build_constraints():
    U = [[Int(f"u_{r}_{i}") for i in range(N)] for r in range(ROWS)]
    c = []
    for i in range(N):
        c.append(U[0][i] == i)
    for r in range(1, ROWS):
        for i in range(N):
            c += [U[r][i] >= 0, U[r][i] < N]
        c.append(Distinct(U[r]))
    # Shifted disagreement: for every earlier row t and later row u,
    # U_u(i) differs from U_t(i + (u-t)).
    for t in range(ROWS):
        for u in range(t + 1, ROWS):
            d = u - t
            for i in range(N):
                c.append(U[u][i] != U[t][(i + d) % N])
    # No three rows agree in one column.
    for i in range(N):
        for a, b, d in itertools.combinations(range(ROWS), 3):
            c.append(Or(U[a][i] != U[b][i], U[a][i] != U[d][i]))
    return U, c


def agreement(U, a, b):
    return Sum([If(U[a][i] == U[b][i], 1, 0) for i in range(N)])


def optimize_total(U, constraints):
    pairs = list(itertools.combinations(range(ROWS), 2))
    ms = [agreement(U, a, b) for a, b in pairs]
    total = Sum(ms)
    opt = Optimize()
    opt.add(constraints)
    hmax = opt.maximize(total)
    hmin = opt.minimize(total)
    assert opt.check() == sat
    max_total = opt.upper(hmax).as_long()
    min_total = opt.lower(hmin).as_long()
    return pairs, ms, min_total, max_total


def exists_total(U, constraints, target):
    pairs = list(itertools.combinations(range(ROWS), 2))
    total = Sum([agreement(U, a, b) for a, b in pairs])
    s = Solver(); s.add(constraints); s.add(total == target)
    return s.check() == sat


def main():
    U, constraints = build_constraints()
    pairs, ms, min_total, max_total = optimize_total(U, constraints)
    attainable_totals = [k for k in range(0, 15) if exists_total(U, constraints, k)]

    # Check the obvious no-triple-agreement upper bound independently.
    s = Solver(); s.add(constraints); s.add(Sum(ms) > 14)
    upper14_unsat = s.check() == unsat

    out = {
        "rows": ROWS,
        "symbols": N,
        "pair_order": [list(p) for p in pairs],
        "min_total_pair_agreement": min_total,
        "max_total_pair_agreement": max_total,
        "attainable_totals_0_to_14": attainable_totals,
        "upper_bound_14_proved_unsat": upper14_unsat,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/four_row_local_probe.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, indent=2, sort_keys=True))
    if not upper14_unsat:
        raise SystemExit("local encoding violated no-triple upper bound")


if __name__ == "__main__":
    main()
