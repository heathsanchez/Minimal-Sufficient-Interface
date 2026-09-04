"""Functional-graph merger->root certificate (BOUNDED verification).

BOUNDED evidence only: this script exhaustively verifies the fact for finite
sizes n = 2..6. It is NOT a generic theorem for arbitrary finite sets.

The generic statement and its hand proof (indegree-count identity
    Sigma_y |tau^{-1}(y)| = |S| )
live in merger_to_root_generic_proof.md, and are classified
REQUIRE_GENERIC_VERIFICATION (awaiting Lean kernel acceptance over an
arbitrary [Fintype S] [Nonempty S]). Do not cite the n=2..6 run as a generic
finite-functional-graph theorem.

The fact: a total map on a finite set with a merger (some vertex indegree > 1)
must have a root (some vertex indegree 0). No E677 / magma / renewal
vocabulary. This is the pigeonhole instance consumed by the backward-component
step of the frozen diagonal-escape lemma and by the mixed collision-fibre
tau-merger.
"""

import argparse
import json
import sys
from z3 import And, BoolVal, Int, Or, Solver, unsat


def merger_implies_root(n: int):
    """Prove: for a total map f on {0..n-1}, (exists y indeg>=2) => (exists z indeg=0).

    Equivalently, (exists y indeg>=2) AND (all z indeg>=1) is UNSAT.
    """
    s = Solver()
    f = []
    for x in range(n):
        fx = Int(f"f_{x}")
        s.add(fx >= 0, fx < n)
        f.append(fx)

    def indeg_ge_1(y):
        return Or([f[x] == y for x in range(n)])

    def indeg_ge_2(y):
        return Or([
            And(f[a] == y, f[b] == y, a != b)
            for a in range(n) for b in range(n)
        ])

    # counter-assumption: some merger AND no root
    merger = Or([indeg_ge_2(y) for y in range(n)])
    no_root = And([indeg_ge_1(z) for z in range(n)])
    s.add(merger, no_root)

    r = s.check()
    # UNSAT means: merger -> root (the counter-assumption is impossible).
    return (r == unsat), str(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/merger_root_certificate.json")
    ap.add_argument("--max-n", type=int, default=6)
    args = ap.parse_args()

    results = {}
    all_unsat = True
    for n in range(2, args.max_n + 1):
        holds, verdict = merger_implies_root(n)
        results[f"n={n}"] = verdict
        if not holds:
            all_unsat = False

    out = {
        "certificate": "merger_to_root",
        "theorem": (
            "finite set + total map + (some vertex indegree>1) => "
            "(some vertex indegree 0)"
        ),
        "domain_independent": True,
        "results": results,
        "all_counter_assumptions_unsat": all_unsat,
        "transition": "PROMOTE" if all_unsat else "REJECT",
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))
    sys.exit(0 if all_unsat else 1)


if __name__ == "__main__":
    main()
