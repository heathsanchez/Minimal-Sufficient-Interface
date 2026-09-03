"""Exact ground probe for the first FORK + G-CROSS residual.

This is deliberately a partial, source-backed consequence test, not a finite
magma search.  Multiplication is an uninterpreted binary operation.  We encode
only equations/disequalities proved in the upstream ZERO-reuse and reverse-lift
lemmas, left-row injectivity on the named inputs, and selected *ground* E677
instances.  Therefore:

* UNSAT proves those named consequences are already inconsistent.
* SAT proves only that this bounded ground consequence set is insufficient;
  it is not a magma and not a counterexample.

The probe first proves the structural shell SAT with no E677 instances, then
adds all ordered E677 pairs over the named fragment.  If UNSAT, it asks Z3 for
an assumption core and greedily minimizes the E677-pair set while retaining
all structural facts.
"""
from __future__ import annotations

import json
from pathlib import Path
from itertools import product
from z3 import Const, DeclareSort, Function, Solver, Bool, Implies, sat, unsat

U = DeclareSort("U")
mul = Function("mul", U, U, U)

# First FORK at x, q=H(x), then canonical mixed collision/G-CROSS at q.
names = ["x", "d", "q", "e", "h", "r", "sx", "sigx", "sq", "t", "z"]
C = {n: Const(n, U) for n in names}
BAD = [C[n] for n in ["x", "d", "q", "e", "h", "r"]]
GOOD = [C[n] for n in ["sx", "sigx", "sq", "t", "z"]]


def e677(a, b):
    # x = y * (x * ((y*x)*y))
    return a == mul(b, mul(a, mul(mul(b, a), b)))


def structural_assertions(include_injectivity: bool = True):
    x,d,q,e,h,r,sx,sigx,sq,t,z = (C[n] for n in names)
    A = []

    # Colour separation only.  Same-colour labels are not assumed distinct
    # unless the source forces it below.
    for b in BAD:
        for g in GOOD:
            A.append(b != g)

    # Badness/no-HIT at x and q: D(x)=d != x, D(q)=e != q.
    A += [d != x, e != q]

    # Canonical D band at x and at q.
    A += [mul(x,x) == sx, mul(sx,x) == sigx, mul(sigx,x) == d]
    A += [mul(q,q) == sq, mul(sq,q) == t, mul(t,q) == e]

    # First FORK: q=H(x), so D(x)*q=x, but D(q) != x.
    A += [mul(d,q) == x, e != x]

    # H(q)=h and the canonical mixed collision at (q,e).
    A += [mul(e,h) == q, mul(r,q) == e]

    # G-CROSS branch of the canonical companion at q.
    A += [mul(t,e) == z, mul(z,t) == h]

    # Every carrier c with c*q=e has the same companion hinge h=(c*e)*c.
    A += [mul(mul(r,e),r) == h]

    if include_injectivity:
        # Every left translation is a permutation, hence injective on this
        # finite named input subset.  No surjectivity/finite-domain assumption.
        inputs = [C[n] for n in names]
        rows = [C[n] for n in names]
        for row in rows:
            for i,a in enumerate(inputs):
                for b in inputs[i+1:]:
                    A.append(Implies(mul(row,a) == mul(row,b), a == b))
    return A


def solve(pair_subset=(), include_injectivity=True, track=False):
    s = Solver()
    s.add(*structural_assertions(include_injectivity))
    assumptions = []
    if track:
        for a_name,b_name in pair_subset:
            tag = Bool(f"E677__{a_name}__{b_name}")
            s.add(Implies(tag, e677(C[a_name], C[b_name])))
            assumptions.append(tag)
        res = s.check(*assumptions)
        core = [str(v) for v in s.unsat_core()] if res == unsat else []
        return res, s, core
    for a_name,b_name in pair_subset:
        s.add(e677(C[a_name], C[b_name]))
    return s.check(), s, []


def minimize_pairs(pairs):
    cur = list(pairs)
    changed = True
    while changed:
        changed = False
        for p in list(cur):
            trial = [q for q in cur if q != p]
            res,_,_ = solve(trial, include_injectivity=True, track=False)
            if res == unsat:
                cur = trial
                changed = True
    return cur


def equal_seed_pairs(model):
    out=[]
    vals={n:model.eval(C[n], model_completion=True) for n in names}
    for i,a in enumerate(names):
        for b in names[i+1:]:
            if str(vals[a]) == str(vals[b]):
                out.append([a,b])
    return out


def main():
    frontier=json.load(open("program_frontier.json"))
    assert frontier["authoritative"]
    assert frontier["live_residual"]["type"] == "REFRAME"
    assert "G-CROSS" in frontier["live_residual"]["text"]

    base_res,base_solver,_ = solve((), include_injectivity=True)
    assert base_res == sat, "structural shell must be a genuine consistent baseline"

    all_pairs=list(product(names,names))
    mixed_res,mixed_solver,core = solve(all_pairs, include_injectivity=True, track=True)

    # Causal ablation: if mixed is UNSAT, check whether injectivity is load-bearing.
    noinj_res,_,_ = solve(all_pairs, include_injectivity=False, track=False)

    minimal=[]
    sat_equalities=[]
    if mixed_res == unsat:
        # Start from the tracked core's E677 pair names, then greedily minimize.
        core_pairs=[]
        prefix="E677__"
        for tag in core:
            if tag.startswith(prefix):
                _,a,b = tag.split("__",2)
                core_pairs.append((a,b))
        minimal=minimize_pairs(core_pairs or all_pairs)
        classification="PROMOTE" if minimal else "REQUIRE_ATTACHMENT"
        residual=("The exact first-FORK + G-CROSS ground fragment is inconsistent under the listed mixed E677 instances. "
                  "Turn the minimized E677 pair core into a symbolic lemma and ablate each structural equation before any wider claim.")
    else:
        sat_equalities=equal_seed_pairs(mixed_solver.model())
        classification="PARK"
        residual=("The exact first-FORK + one G-CROSS fragment remains satisfiable after every ground E677 instance on the named fragment and left-row injectivity. "
                  "This is a partial uninterpreted model, not a magma. Local mixed equations at one fork are insufficient; the next object must couple multiple marked G-CROSSes through shared Bad-shadow/renewal structure.")

    out={
        "consumed_frontier_schema":frontier["schema_version"],
        "scope":"first FORK + one canonical G-CROSS; uninterpreted multiplication; named left-injectivity; ground E677 only",
        "base_shell":str(base_res),
        "ground_e677_pair_count":len(all_pairs),
        "mixed_result":str(mixed_res),
        "without_injectivity_result":str(noinj_res),
        "tracked_unsat_core":core,
        "minimal_e677_pairs":[list(p) for p in minimal],
        "sat_seed_equalities":sat_equalities,
        "finite_magma_claimed":False,
        "counterexample_claimed":False,
        "global_e677_implication_claimed":False,
        "proposed_transition":{"classification":classification,"residual":residual},
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/e677_fork_gcross_ground_e677_probe.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))
    print("FORK_GCROSS_GROUND_E677_PROBE_VERIFIED")

if __name__ == "__main__":
    main()
