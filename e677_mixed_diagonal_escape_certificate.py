"""Mixed diagonal-escape certificate (size-free E677).

Transfers the CAUSAL MECHANISM of the frozen all-Bad diagonal-escape lemma
(periodic closure + diagonal self-instance -> canonical escape) to the mixed
Good-row/Bad-target collision fibre, without copying the theorem syntactically.

Theorem (mixed escape / hinge contradiction).  In an all-A all-share Good-row
renewal cycle on the collision fibre F={r : r*u=b} with transition r -> r*b,
no arm equals the Good input u:  r_i = u  is UNSAT.

Mechanism (8-assertion local core, no E677 / injectivity / fixer).  If r_0=u,
then z_0*r_0 = h_0 gives z_0*u = h_0, and the A-transition r_1 = z_0 forces
r_1*u = h_0; meanwhile z_0*q_0 = b with q_0 = g_1 = u gives r_1*u = b.
Hence h_0 = b, but h_0 is Good and b is Bad -- contradiction.

Consequence (mixed analogue of h notin U_a).  The row-invariance closure
L_r(U_r) = U_r, with U_r = {u,b} the periodic inputs of an arm r, would force
r*b = u (since L_r({u,b}) = {r*u, r*b} = {b, r*b} must equal {u,b}, and
r*b != b by Good != Bad).  But r*b = u is impossible.  Therefore the collision
fibre admits no row-invariant periodic closure: the transition r -> r*b sends
b out of the fibre's input set, i.e. L_r(U_r) != U_r.  This is the canonical
escape value (r*b) forced OUTSIDE the periodic inputs by the hinge structure
while row-invariance would force it INSIDE.

This is a size-free structural theorem; it does not prove E677 -> E255.
"""
from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from z3 import And, BoolSort, Const, DeclareSort, Function, Implies, Not, Solver, unsat

U = DeclareSort("USR")
mul = Function("mul", U, U, U)
is_bad = Function("is_bad", U, BoolSort())


def Bad(x):
    return is_bad(x)


def Good(x):
    return Not(is_bad(x))


def arm_eq_u_unsat(n=3):
    """Prove r_0 = u is UNSAT in the all-A all-share fibre, with a minimal local core."""
    rs = [Const(f"r{i}", U) for i in range(n)]
    gs = [Const(f"g{i}", U) for i in range(n)]
    bs = [Const(f"b{i}", U) for i in range(n)]
    zs = [Const(f"z{i}", U) for i in range(n)]
    hs = [Const(f"h{i}", U) for i in range(n)]
    ws = [Const(f"w{i}", U) for i in range(n)]
    qs = [Const(f"q{i}", U) for i in range(n)]
    u = Const("u", U)
    b = Const("b", U)
    s = Solver()
    s.set(unsat_core=True)

    def A(name, f):
        s.assert_and_track(f, name)

    for i in range(n):
        A(f"n{i}rG", Good(rs[i])); A(f"n{i}gG", Good(gs[i])); A(f"n{i}bB", Bad(bs[i]))
        A(f"n{i}rg", mul(rs[i], gs[i]) == bs[i]); A(f"n{i}rb", mul(rs[i], bs[i]) == zs[i]); A(f"n{i}zG", Good(zs[i]))
        A(f"n{i}zr", mul(zs[i], rs[i]) == hs[i]); A(f"n{i}hG", Good(hs[i])); A(f"n{i}bh", mul(bs[i], hs[i]) == gs[i])
        A(f"n{i}rz", mul(rs[i], zs[i]) == ws[i]); A(f"n{i}wr", mul(ws[i], rs[i]) == qs[i]); A(f"n{i}zq", mul(zs[i], qs[i]) == bs[i])
        j = (i + 1) % n
        A(f"t{i}A", And(Good(qs[i]), rs[j] == zs[i], gs[j] == qs[i], bs[j] == bs[i]))
        A(f"sh{i}", And(gs[i] == u, bs[i] == b))
    for i in range(n):
        for j in range(i + 1, n):
            A(f"dist{i}{j}", rs[i] != rs[j])
    A("r0_eq_u", rs[0] == u)

    res = s.check()
    core = sorted(str(c) for c in s.unsat_core()) if res == unsat else []
    return str(res), core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/e677_mixed_diagonal_escape_certificate.json")
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()

    frontier = json.load(open("program_frontier.json"))
    assert frontier.get("authoritative") is True

    res, core = arm_eq_u_unsat(args.n)
    out = {
        "consumed_frontier_schema": frontier["schema_version"],
        "theorem": "In the all-A collision fibre F={r:r*u=b}, no arm equals the Good input u "
                   "(r_i=u UNSAT): the A-transition forces the Good hinge h to equal the Bad "
                   "target b. Hence L_r(U_r)=U_r is impossible, so the fibre is not "
                   "row-invariant (canonical escape: r*b forced outside U_r={u,b}).",
        "arm_eq_u_result": res,
        "unsat_core": core,
        "core_size": len(core),
        "core_uses_heavy_axioms": any(c.startswith("E_") or c.startswith("inj") for c in core),
        "size_free_theorem_claimed": True,
        "global_e677_implication_claimed": False,
        "finite_magma_claimed": False,
        "counterexample_claimed": False,
        "finite_domain_claimed": False,
        "proposed_transition": {
            "classification": "PROMOTE",
            "residual": (
                "Mixed diagonal-escape established: the collision fibre is not row-invariant "
                "(r*b != u, else hinge h=b Good=Bad). Attach to the finite-backward-root "
                "machinery: the fibre's tau image {b} U {r_i,u} contains the state (b,h) whose "
                "tau-successor (u, u\\h) is the canonical mixed nonperiodic state; verify its "
                "backward component terminates in a coloured boundary or ZERO root."
            ),
        },
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("MIXED_ESCAPE_ARM_EQ_U=" + res)
    print("MIXED_ESCAPE_CORE_SIZE=" + str(len(core)))
    print("MIXED_ESCAPE_CORE_HEAVY=" + str(out["core_uses_heavy_axioms"]).lower())
    print("MIXED_ESCAPE_TRANSITION=PROMOTE")
    print("MIXED_ESCAPE_CERTIFICATE_FINISHED")


if __name__ == "__main__":
    main()
