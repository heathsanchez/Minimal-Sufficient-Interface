"""Quantifier-free ground projection of the shared Bad-shadow theory.

The preceding first-order probe returned UNKNOWN by timeout on both marked
branches.  This verifier change preserves the same source-backed axiom schemas
but instantiates them only on the existing 19 named terms from the linked
q -> H(q)=h fragment.  Function outputs remain unrestricted elements of the
uninterpreted universe: this is NOT a finite-domain model and SAT is NOT a
counterexample.  UNSAT, however, is a valid contradiction from this finite
subset of the first-order theory and can be minimized/formalized.
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

from z3 import And, Implies, Solver, sat, unsat, unknown

from e677_linked_two_mark_probe import C, names, common_structural_assertions, mul
from e677_shared_bad_shadow_probe import (
    Bad,
    Good,
    D,
    E677,
    carrier,
    kappa,
    shadow,
    shadow_E677,
    sigma,
)

VALS = [C[n] for n in names]


def ground_shadow_axioms():
    """Instantiate every universal schema used by the first-order probe on VALS."""
    A = []

    # Global E677 on all named pairs.
    for x, y in product(VALS, repeat=2):
        A.append(E677(x, y))

    # Global left-row injectivity, grounded on named rows/arguments.
    for r, a, b in product(VALS, repeat=3):
        A.append(Implies(mul(r, a) == mul(r, b), a == b))

    # No row fixes a Bad input.
    for r, u in product(VALS, repeat=2):
        A.append(Implies(Bad(u), mul(r, u) != u))

    # ZERO-reuse/no-HIT band for each named input.
    for x in VALS:
        A.append(Implies(Bad(x), And(
            Good(mul(x, x)),
            Good(sigma(x)),
            Good(kappa(x)),
            Bad(D(x)),
            mul(x, sigma(x)) == kappa(x),
            mul(x, kappa(x)) == x,
        )))

    # Off-diagonal Bad closure.
    for r, u in product(VALS, repeat=2):
        A.append(Implies(And(Bad(r), Bad(u), r != u), Bad(mul(r, u))))

    # Exact N_B(u,v)=1, grounded on named inputs/targets/carrier competitors.
    for u, v in product(VALS, repeat=2):
        A.append(Implies(And(Bad(u), Bad(v), u != v), And(
            Bad(carrier(u, v)),
            mul(carrier(u, v), u) == v,
        )))
    for r, u, v in product(VALS, repeat=3):
        A.append(Implies(
            And(Bad(r), Bad(u), Bad(v), u != v, mul(r, u) == v),
            r == carrier(u, v),
        ))

    # Idempotent Latin E677 Bad shadow, with off-diagonal link to mul.
    for x in VALS:
        A.append(Implies(Bad(x), shadow(x, x) == x))
    for x, y in product(VALS, repeat=2):
        A.append(Implies(And(Bad(x), Bad(y)), Bad(shadow(x, y))))
        A.append(Implies(And(Bad(x), Bad(y), x != y), shadow(x, y) == mul(x, y)))
        A.append(Implies(And(Bad(x), Bad(y)), shadow_E677(x, y)))
    for r, a, b in product(VALS, repeat=3):
        A.append(Implies(
            And(Bad(r), Bad(a), Bad(b), shadow(r, a) == shadow(r, b)),
            a == b,
        ))
        A.append(Implies(
            And(Bad(r), Bad(a), Bad(b), shadow(a, r) == shadow(b, r)),
            a == b,
        ))

    return A


def solve(branch: str, timeout_ms: int = 120000):
    s = Solver()
    s.set(timeout=timeout_ms)
    s.add(*common_structural_assertions(
        branch, include_injectivity=False, include_no_fixers=False
    ))
    axioms = ground_shadow_axioms()
    s.add(*axioms)
    res = s.check()
    payload = {
        "result": str(res),
        "reason_unknown": s.reason_unknown() if res == unknown else "",
        "ground_axiom_count": len(axioms),
    }
    if res == sat:
        m = s.model()
        values = {n: str(m.eval(C[n], model_completion=True)) for n in names}
        classes = {}
        for n, v in values.items():
            classes.setdefault(v, []).append(n)
        payload["named_values"] = values
        payload["named_equality_classes"] = sorted(
            [sorted(v) for v in classes.values()], key=lambda xs: (len(xs), xs)
        )
        payload["model_sexpr"] = m.sexpr()
    return res, payload


def main():
    frontier = json.load(open("program_frontier.json"))
    assert frontier["authoritative"] is True
    assert frontier["schema_version"] >= 10
    assert frontier["live_residual"]["type"] == "REFRAME"
    residual = frontier["live_residual"]["text"].lower()
    assert "ground consequence" in residual and "bad-shadow" in residual

    results = {}
    for branch in ("ZIPPER", "GCROSS"):
        _, results[branch] = solve(branch)

    sats = [b for b, r in results.items() if r["result"] == "sat"]
    unsats = [b for b, r in results.items() if r["result"] == "unsat"]
    unknowns = [b for b, r in results.items() if r["result"] == "unknown"]

    if len(unsats) == 2:
        classification = "PROMOTE"
        next_residual = (
            "Both marked continuations are UNSAT already in the quantifier-free named-input "
            "ground projection of the shared Bad-shadow theory. Minimize the ground cores, "
            "ablate shadow/carrier/renewal ingredients, and derive the shortest symbolic "
            "length-independent obstruction before widening scope."
        )
    elif unknowns:
        classification = "REQUIRE_ATTACHMENT"
        next_residual = (
            f"The quantifier-free ground projection is still verifier-inconclusive on {unknowns}. "
            "Do not infer mathematics. Split the axiom families incrementally or move the "
            "highest-leverage shadow consequence into Lean."
        )
    elif len(sats) == 2:
        classification = "PARK"
        next_residual = (
            "Both ZIPPER and G-CROSS survive the quantifier-free named-input projection of the "
            "shared Bad-shadow axioms. The first shared shadow algebra does not itself close "
            "the marked fragment. Stop strengthening isolated local algebra and attach the "
            "simultaneous Good-row/Bad-row renewal network through shared marks and shadow carriers."
        )
    else:
        classification = "PROMOTE"
        next_residual = (
            f"The ground shared-shadow projection excludes {unsats} and admits {sats}. "
            "Minimize the excluded branch and route the live renewal argument through the "
            "surviving continuation before any scope widening."
        )

    out = {
        "consumed_frontier_schema": frontier["schema_version"],
        "scope": (
            "19 named linked q->H(q)=h terms; quantifier-free named-input instances of the "
            "first-order Bad-shadow axioms; unrestricted function outputs; no finite-domain axiom"
        ),
        "named_elements": len(names),
        "results": results,
        "sat_branches": sats,
        "unsat_branches": unsats,
        "unknown_branches": unknowns,
        "finite_domain_claimed": False,
        "finite_magma_claimed": False,
        "finite_counterexample_claimed": False,
        "global_e677_implication_claimed": False,
        "proposed_transition": {
            "classification": classification,
            "residual": next_residual,
        },
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/e677_shared_bad_shadow_ground_probe.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({
        "consumed_frontier_schema": out["consumed_frontier_schema"],
        "scope": out["scope"],
        "results": {
            b: {k: v for k, v in r.items() if k not in {"model_sexpr", "named_values"}}
            for b, r in results.items()
        },
        "proposed_transition": out["proposed_transition"],
    }, indent=2, sort_keys=True))
    print("GROUND_SHADOW_ZIPPER=" + results["ZIPPER"]["result"])
    print("GROUND_SHADOW_GCROSS=" + results["GCROSS"]["result"])
    print("GROUND_SHADOW_TRANSITION=" + classification)
    print("GROUND_SHARED_BAD_SHADOW_PROBE_FINISHED")


if __name__ == "__main__":
    main()
