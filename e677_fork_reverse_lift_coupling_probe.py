"""FORK reverse-lift canonical D-cell coupling probe (size-free E677 frontier).

Consequence model, not a finite-magma search.

Under ZERO-root reuse + no-HIT, a Bad D-cycle cannot stay fully aligned: it
reaches a first COLLISION or FORK (defect-graph reverse-lift trichotomy,
lemmas/e677_defect_graph_reverse_lift_and_hit_block_lemma.md).  At a FORK, for
Bad x with q = H(x) = D(x)\\x, the reverse edge

    D(x)*q = x

coexists with the canonical edge

    sigma(q)*q = D(q) = e,

and the fork condition is D(q) != x.  Both x and q are Bad and each carries a
canonical ZIPPER / marked G-CROSS D-cell (zero_root_reuse C1-C7):

    e = D(x), t = sigma(x) Good, h = H(x) = q Bad, e*q = x,
    z = t*e, z*t = q,
    ZIPPER  : z Bad => z = q, t = kappa(q), t*e = q ;
    G-CROSS : z Good => (z, t, q) in G x G x B.

The previous bad-target G-CROSS coupling probe remained SAT on the shared Bad
target's D-cell alone.  This probe couples TWO canonical D-cells through the
reverse-lift relation q = H(x) and the fork inequality D(q) != x, and asks
whether that coupling is satisfiable together with the full source-backed
ground theory (E677, left-row injectivity, unique/no fixer, kappa self-band,
Bad shadow quasigroup, exact unique Bad carriers, off-diagonal Bad closure).

The universe is uninterpreted; there is no finite-domain axiom.
"""
from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from z3 import And, BoolSort, Const, DeclareSort, Function, Implies, Not, Or, Solver, sat, unknown

U = DeclareSort("USR")
mul = Function("mul", U, U, U)
is_bad = Function("is_bad", U, BoolSort())
shadow = Function("shadow", U, U, U)
carrier = Function("carrier", U, U, U)


def Bad(x):
    return is_bad(x)


def Good(x):
    return Not(Bad(x))


def sigma(x):
    return mul(mul(x, x), x)


def D(x):
    return mul(sigma(x), x)


def E677(x, y):
    return x == mul(y, mul(x, mul(mul(y, x), y)))


def shadow_E677(x, y):
    return x == shadow(y, shadow(x, shadow(shadow(y, x), y)))


def named_ground_axioms(vals, bad_terms, good_terms):
    """Ground source-backed global schemas on the named fragment."""
    A = []
    A.extend(Bad(x) for x in bad_terms)
    A.extend(Good(x) for x in good_terms)

    # Global E677 and left-row injectivity on the named fragment.
    for x, y in product(vals, repeat=2):
        A.append(E677(x, y))
    for r, a, b in product(vals, repeat=3):
        A.append(Implies(mul(r, a) == mul(r, b), a == b))

    # Unique fixer for Good, no fixer for Bad.
    for a in good_terms:
        A.append(mul(sigma(a), a) == a)
        for r in vals:
            A.append(Implies(mul(r, a) == a, r == sigma(a)))
    for a in bad_terms:
        A.append(mul(sigma(a), a) != a)
        for r in vals:
            A.append(mul(r, a) != a)

    # Self band colours: square Good, sigma Good, D Bad.
    for x in bad_terms:
        A.append(Good(mul(x, x)))
        A.append(Good(sigma(x)))
        A.append(Bad(D(x)))

    # Off-diagonal Bad closure and exact unique Bad carriers.
    for r, u in product(bad_terms, repeat=2):
        A.append(Implies(r != u, Bad(mul(r, u))))
    for u, v in product(bad_terms, repeat=2):
        A.append(Implies(u != v, And(Bad(carrier(u, v)), mul(carrier(u, v), u) == v)))
    for r, u, v in product(bad_terms, repeat=3):
        A.append(Implies(And(u != v, mul(r, u) == v), r == carrier(u, v)))

    # Idempotent Latin E677 Bad shadow with row/column injectivity.
    for x in bad_terms:
        A.append(shadow(x, x) == x)
    for x, y in product(bad_terms, repeat=2):
        A.append(Bad(shadow(x, y)))
        A.append(Implies(x != y, shadow(x, y) == mul(x, y)))
        A.append(shadow_E677(x, y))
    for r, a, b in product(bad_terms, repeat=3):
        A.append(Implies(shadow(r, a) == shadow(r, b), a == b))
        A.append(Implies(shadow(a, r) == shadow(b, r), a == b))
    return A


def build_fork(timeout_ms: int):
    # Named constants.  Computed self-band elements are named for grounding.
    x = Const("x", U)      # Bad, on the D-cycle
    q = Const("q", U)      # Bad, = H(x)
    h = Const("h", U)      # Bad, = H(q), e*h = q
    ex = Const("ex", U)    # Bad, = D(x)
    e = Const("e", U)      # Bad, = D(q)
    sx = Const("sx", U)    # Good, = x*x
    sq = Const("sq", U)    # Good, = q*q
    tx = Const("tx", U)    # Good, = sigma(x)
    t = Const("t", U)      # Good, = sigma(q)
    kx = Const("kx", U)    # Good, = kappa(x) = x*sigma(x)
    kq = Const("kq", U)    # Good, = kappa(q) = q*sigma(q)
    zx = Const("zx", U)    # z_x = tx*ex  (Good/Bad by dichotomy)
    z = Const("z", U)      # z   = t*e    (Good/Bad by dichotomy)

    s = Solver()
    s.set(timeout=timeout_ms)

    bad_terms = [x, q, ex, e, h]
    good_terms = [sx, sq, tx, t, kx, kq]
    vals = bad_terms + good_terms + [zx, z]

    # Defining equations of the self band.
    s.add(sx == mul(x, x), sq == mul(q, q))
    s.add(tx == mul(sx, x), t == mul(sq, q))   # sigma = s*x
    s.add(ex == mul(tx, x), e == mul(t, q))    # D = sigma*x
    s.add(kx == mul(x, tx), kq == mul(q, t))   # kappa = x*sigma
    s.add(mul(x, kx) == x, mul(q, kq) == q)    # x*kappa(x) = x

    # Reverse-lift relation and the FORK inequality.
    s.add(mul(ex, q) == x)                      # D(x)*q = x  <=>  q = H(x)
    s.add(mul(t, q) == e)                       # sigma(q)*q = D(q) = e (canonical)
    s.add(e != x)                               # FORK: D(q) != x

    # x's canonical D-cell: e_x*q = x, z_x = t_x*e_x, z_x*t_x = q.
    s.add(zx == mul(tx, ex))
    s.add(mul(zx, tx) == q)
    s.add(Or(Good(zx), And(zx == q, mul(q, tx) == q, mul(tx, ex) == q)))

    # q's canonical D-cell: e*h = q, z = t*e, z*t = h.
    s.add(mul(e, h) == q)
    s.add(z == mul(t, e))
    s.add(mul(z, t) == h)
    s.add(Or(Good(z), And(z == h, mul(h, t) == h, mul(t, e) == h)))

    s.add(*named_ground_axioms(vals, bad_terms, good_terms))

    res = s.check()
    out = {
        "result": str(res),
        "named_terms": len(vals),
        "bad_terms": len(bad_terms),
        "good_terms": len(good_terms),
        "ground_axioms": len(named_ground_axioms(vals, bad_terms, good_terms)),
        "reason_unknown": s.reason_unknown() if res == unknown else "",
    }
    if res == sat:
        m = s.model()
        named = {
            "x": str(m.eval(x, model_completion=True)),
            "q": str(m.eval(q, model_completion=True)),
            "h": str(m.eval(h, model_completion=True)),
            "ex": str(m.eval(ex, model_completion=True)),
            "e": str(m.eval(e, model_completion=True)),
            "sx": str(m.eval(sx, model_completion=True)),
            "sq": str(m.eval(sq, model_completion=True)),
            "tx": str(m.eval(tx, model_completion=True)),
            "t": str(m.eval(t, model_completion=True)),
            "kx": str(m.eval(kx, model_completion=True)),
            "kq": str(m.eval(kq, model_completion=True)),
            "zx": str(m.eval(zx, model_completion=True)),
            "z": str(m.eval(z, model_completion=True)),
        }
        out["model"] = named
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/e677_fork_reverse_lift_coupling_probe.json")
    ap.add_argument("--timeout-ms", type=int, default=30000)
    args = ap.parse_args()

    frontier = json.load(open("program_frontier.json"))
    assert frontier.get("authoritative") is True
    assert frontier["schema_version"] >= 11
    rt = frontier["live_residual"]["text"].lower()
    assert ("fork" in rt or "reverse-lift" in rt) and "canonical" in rt

    case = build_fork(args.timeout_ms)
    res = case["result"]

    if res == "sat":
        classification = "PARK"
        residual = (
            "The FORK reverse-lift coupling of x and q=H(x) (D(q)!=x) with both canonical "
            "ZIPPER/G-CROSS D-cells remains SAT under the full source-backed ground theory. "
            "Dump the smallest witness and identify the first absent source-backed coexistence "
            "constraint; do not append another isolated mark or widen bounds blindly."
        )
    elif res == "unknown":
        classification = "REQUIRE_ATTACHMENT"
        residual = (
            "The FORK coupling is verifier-UNKNOWN. Minimize the theory (ablate carrier/shadow/"
            "kappa/E677 subsets) before reading any mathematics from the run."
        )
    else:
        classification = "PROMOTE"
        residual = (
            "The FORK reverse-lift coupling is UNSAT under the full source-backed ground theory. "
            "Ablate to identify the causal contradiction, then extract a length-independent "
            "invariant before any size-free claim."
        )

    out = {
        "consumed_frontier_schema": frontier["schema_version"],
        "scope": "bounded FORK reverse-lift coupling of two canonical ZIPPER/G-CROSS D-cells "
                 "(x and q=H(x), D(q)!=x) under ZERO-reuse/no-HIT ground consequences; "
                 "uninterpreted universe; no finite-domain axiom",
        "case": case,
        "finite_domain_claimed": False,
        "finite_magma_claimed": False,
        "counterexample_claimed": False,
        "global_e677_implication_claimed": False,
        "size_free_theorem_claimed": False,
        "proposed_transition": {"classification": classification, "residual": residual},
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("FORK_COUPLING_RESULT=" + res)
    print("FORK_COUPLING_NAMED_TERMS=" + str(case["named_terms"]))
    print("FORK_COUPLING_GROUND_AXIOMS=" + str(case["ground_axioms"]))
    print("FORK_COUPLING_REASON_UNKNOWN=" + case.get("reason_unknown", ""))
    print("FORK_COUPLING_TRANSITION=" + classification)
    if res == "sat":
        print("FORK_COUPLING_MODEL=" + json.dumps(case.get("model", {}), sort_keys=True))
    print("FORK_COUPLING_PROBE_FINISHED")


if __name__ == "__main__":
    main()
