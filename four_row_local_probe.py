"""Exact four-row local probe for the next recursive residual.

This script is intentionally blind to E677/E255. It studies only the local permutation
constraints compiled by the controller. Z3 is used as a finite exact constraint solver.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from z3 import Distinct, If, Int, Or, Sum, Solver, sat, unsat

N = 7
ROWS = 4
PAIRS = tuple(itertools.combinations(range(ROWS), 2))


def build_constraints(prefix="u"):
    U = [[Int(f"{prefix}_{r}_{i}") for i in range(N)] for r in range(ROWS)]
    c = []
    for i in range(N):
        c.append(U[0][i] == i)
    for r in range(1, ROWS):
        for i in range(N):
            c += [U[r][i] >= 0, U[r][i] < N]
        c.append(Distinct(U[r]))
    for t in range(ROWS):
        for u in range(t + 1, ROWS):
            shift = u - t
            for i in range(N):
                c.append(U[u][i] != U[t][(i + shift) % N])
    for i in range(N):
        for a, b, d in itertools.combinations(range(ROWS), 3):
            c.append(Or(U[a][i] != U[b][i], U[a][i] != U[d][i]))
    return U, c


def agreement(U, a, b):
    return Sum([If(U[a][i] == U[b][i], 1, 0) for i in range(N)])


def total_agreement(U):
    return Sum([agreement(U, a, b) for a, b in PAIRS])


def exists_total(target):
    U, constraints = build_constraints(f"t{target}")
    s = Solver(); s.add(constraints); s.add(total_agreement(U) == target)
    return s.check() == sat


def exact_extrema():
    attainable = [k for k in range(0, 15) if exists_total(k)]
    if not attainable:
        raise RuntimeError("local constraint system has no model")
    return min(attainable), max(attainable), attainable


def independent_total13_check():
    # Second encoding uses explicit per-column collision indicators instead of
    # pair-agreement helper expressions. Same mathematical constraints, different
    # total construction, to guard against an arithmetic/readout bug.
    U, constraints = build_constraints("ind")
    collisions = []
    for i in range(N):
        for a, b in PAIRS:
            collisions.append(If(U[a][i] == U[b][i], 1, 0))
    s = Solver(); s.add(constraints); s.add(Sum(collisions) == 13)
    return s.check() == unsat


def main():
    min_total, max_total, attainable_totals = exact_extrema()

    U, constraints = build_constraints("bound")
    s = Solver(); s.add(constraints); s.add(total_agreement(U) > 14)
    upper14_unsat = s.check() == unsat

    total13_unsat_primary = not exists_total(13)
    total13_unsat_independent = independent_total13_check()

    out = {
        "rows": ROWS,
        "symbols": N,
        "pair_order": [list(p) for p in PAIRS],
        "min_total_pair_agreement": min_total,
        "max_total_pair_agreement": max_total,
        "attainable_totals_0_to_14": attainable_totals,
        "missing_totals_0_to_14": [k for k in range(15) if k not in attainable_totals],
        "upper_bound_14_proved_unsat": upper14_unsat,
        "total13_unsat_primary": total13_unsat_primary,
        "total13_unsat_independent_encoding": total13_unsat_independent,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/four_row_local_probe.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, indent=2, sort_keys=True))

    if min_total != 0 or max_total != 14:
        raise SystemExit(f"unexpected exact extrema: min={min_total}, max={max_total}")
    if not upper14_unsat:
        raise SystemExit("local encoding violated no-triple upper bound")
    if not (total13_unsat_primary and total13_unsat_independent):
        raise SystemExit("total-13 exclusion did not reproduce")


if __name__ == "__main__":
    main()
