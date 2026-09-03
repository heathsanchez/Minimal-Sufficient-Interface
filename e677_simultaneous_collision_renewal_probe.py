"""Bounded simultaneous-renewal discovery probe for the size-free E677 frontier.

This is a consequence model, not a finite-magma search. It couples two
collision-generated Good-row E crossings through exact short A/B renewal
transitions plus the source-backed Bad-shadow ground consequences retained from
the preceding experiment.

The matrix is ordered from smallest topologies upward. Because one SAT witness
already proves that this abstraction is insufficient, execution stops at the
first SAT result. Full expansion is performed only if every earlier case is
UNSAT/UNKNOWN. UNSAT across the whole bounded matrix is discovery evidence, not
a size-free theorem.
"""
from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from z3 import And, BoolSort, Const, DeclareSort, Function, Implies, Not, Or, Solver, sat, unknown

U = DeclareSort("USR")
mul = Function("mul_sr", U, U, U)
is_bad = Function("is_bad_sr", U, BoolSort())
shadow = Function("shadow_sr", U, U, U)
carrier = Function("carrier_sr", U, U, U)


def Bad(x):
    return is_bad(x)


def Good(x):
    return Not(Bad(x))


def sigma(x):
    return mul(mul(x, x), x)


def E677(x, y):
    return x == mul(y, mul(x, mul(mul(y, x), y)))


def shadow_E677(x, y):
    return x == shadow(y, shadow(x, shadow(shadow(y, x), y)))


class Node:
    def __init__(self, tag: str):
        self.r = Const(f"{tag}_r", U)
        self.g = Const(f"{tag}_g", U)
        self.b = Const(f"{tag}_b", U)
        self.z = Const(f"{tag}_z", U)
        self.h = Const(f"{tag}_h", U)
        self.w = Const(f"{tag}_w", U)
        self.q = Const(f"{tag}_q", U)

    def constants(self):
        return [self.r, self.g, self.b, self.z, self.h, self.w, self.q]


def node_axioms(n: Node):
    # Exact length-one Good-row crossing/renewal equations.
    return [
        Good(n.r), Good(n.g), Bad(n.b),
        mul(n.r, n.g) == n.b,
        mul(n.r, n.b) == n.z, Good(n.z),
        mul(n.z, n.r) == n.h, Good(n.h),
        mul(n.b, n.h) == n.g,
        mul(n.r, n.z) == n.w,
        mul(n.w, n.r) == n.q,
        mul(n.z, n.q) == n.b,
    ]


def transition_axioms(n: Node, nxt: Node, letter: str):
    assert letter in {"A", "B"}
    if letter == "A":
        return [Good(n.q), nxt.r == n.z, nxt.g == n.q, nxt.b == n.b]
    return [Bad(n.q), Good(n.w), nxt.r == n.w, nxt.g == n.r, nxt.b == n.q]


def crossing_distinct(a: Node, b: Node):
    return Or(a.r != b.r, a.g != b.g, a.b != b.b)


def uniq(xs):
    d = {}
    for x in xs:
        d[str(x)] = x
    return list(d.values())


def named_ground_axioms(vals, bad_terms, good_terms):
    """Ground only source-backed global schemas on the named fragment."""
    A = []
    A.extend(Bad(x) for x in bad_terms)
    A.extend(Good(x) for x in good_terms)

    # E677 and original-magma LEFT-row injectivity only.
    for x, y in product(vals, repeat=2):
        A.append(E677(x, y))
    for r, a, b in product(vals, repeat=3):
        A.append(Implies(mul(r, a) == mul(r, b), a == b))

    # Unique fixer for Good inputs / no fixer for Bad inputs, named rows only.
    for a in good_terms:
        A.append(mul(sigma(a), a) == a)
        for r in vals:
            A.append(Implies(mul(r, a) == a, r == sigma(a)))
    for a in bad_terms:
        A.append(mul(sigma(a), a) != a)
        for r in vals:
            A.append(mul(r, a) != a)

    # ZERO-reuse/no-HIT consequences retained from the shadow boundary.
    for x in bad_terms:
        A.append(Good(mul(x, x)))
        A.append(Good(sigma(x)))
        A.append(Bad(mul(sigma(x), x)))

    # Off-diagonal Bad closure and exact unique Bad carrier N_B(u,v)=1.
    for r, u in product(bad_terms, repeat=2):
        A.append(Implies(r != u, Bad(mul(r, u))))
    for u, v in product(bad_terms, repeat=2):
        A.append(Implies(u != v, And(Bad(carrier(u, v)), mul(carrier(u, v), u) == v)))
    for r, u, v in product(bad_terms, repeat=3):
        A.append(Implies(And(u != v, mul(r, u) == v), r == carrier(u, v)))

    # Idempotent Latin E677 Bad shadow; off diagonal it agrees with mul.
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


def role_terms(nodes, words_for_nodes):
    vals = uniq([x for nd in nodes for x in nd.constants()])
    bad_terms = [nd.b for nd in nodes]
    good_terms = [x for nd in nodes for x in (nd.r, nd.g, nd.z, nd.h)]
    for nd, letter in words_for_nodes:
        if letter == "A":
            good_terms.append(nd.q)
        else:
            bad_terms.append(nd.q)
            good_terms.append(nd.w)
    return vals, uniq(bad_terms), uniq(good_terms)


def model_crossings(m, nodes):
    return [
        {k: str(m.eval(getattr(nd, k), model_completion=True)) for k in ("r", "g", "b", "z", "h", "w", "q")}
        for nd in nodes
    ]


def build_same_cycle(word: str, offset: int, timeout_ms: int):
    nodes = [Node(f"S{i}") for i in range(len(word))]
    s = Solver(); s.set(timeout=timeout_ms)
    for nd in nodes:
        s.add(*node_axioms(nd))
    for i, letter in enumerate(word):
        s.add(*transition_axioms(nodes[i], nodes[(i + 1) % len(nodes)], letter))
    # Collision handoff: same Good input and Bad target, genuinely distinct row.
    s.add(nodes[0].g == nodes[offset].g, nodes[0].b == nodes[offset].b, nodes[0].r != nodes[offset].r)
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            s.add(crossing_distinct(nodes[i], nodes[j]))
    vals, bad_terms, good_terms = role_terms(nodes, list(zip(nodes, word)))
    ground = named_ground_axioms(vals, bad_terms, good_terms)
    s.add(*ground)
    res = s.check()
    out = {
        "topology": "same", "word": word, "offset": offset, "result": str(res),
        "named_terms": len(vals), "bad_role_terms": len(bad_terms),
        "ground_axioms": len(ground), "reason_unknown": s.reason_unknown() if res == unknown else "",
    }
    if res == sat:
        out["crossings"] = model_crossings(s.model(), nodes)
    return out


def build_distinct_cycles(word1: str, word2: str, timeout_ms: int):
    ns1 = [Node(f"L{i}") for i in range(len(word1))]
    ns2 = [Node(f"R{i}") for i in range(len(word2))]
    s = Solver(); s.set(timeout=timeout_ms)
    for nd in ns1 + ns2:
        s.add(*node_axioms(nd))
    for nodes, word in ((ns1, word1), (ns2, word2)):
        for i, letter in enumerate(word):
            s.add(*transition_axioms(nodes[i], nodes[(i + 1) % len(nodes)], letter))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                s.add(crossing_distinct(nodes[i], nodes[j]))
    s.add(ns1[0].g == ns2[0].g, ns1[0].b == ns2[0].b, ns1[0].r != ns2[0].r)
    for a in ns1:
        for b in ns2:
            s.add(crossing_distinct(a, b))
    pairs = list(zip(ns1, word1)) + list(zip(ns2, word2))
    vals, bad_terms, good_terms = role_terms(ns1 + ns2, pairs)
    ground = named_ground_axioms(vals, bad_terms, good_terms)
    s.add(*ground)
    res = s.check()
    out = {
        "topology": "distinct", "word1": word1, "word2": word2, "result": str(res),
        "named_terms": len(vals), "bad_role_terms": len(bad_terms),
        "ground_axioms": len(ground), "reason_unknown": s.reason_unknown() if res == unknown else "",
    }
    if res == sat:
        m = s.model()
        out["left_crossings"] = model_crossings(m, ns1)
        out["right_crossings"] = model_crossings(m, ns2)
    return out


def words(n):
    return ["".join(w) for w in product("AB", repeat=n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/e677_simultaneous_collision_renewal_probe.json")
    ap.add_argument("--timeout-ms", type=int, default=30000)
    args = ap.parse_args()

    frontier = json.load(open("program_frontier.json"))
    assert frontier.get("authoritative") is True
    assert frontier["schema_version"] >= 11
    rt = frontier["live_residual"]["text"].lower()
    assert "simultaneous" in rt and "renewal" in rt and "collision" in rt

    cases = []
    found_sat = False

    # Test the smallest same-cycle coexistence cases first, then grow only if
    # the abstraction has not already been falsified by a SAT witness.
    for n in range(2, 5):
        if found_sat:
            break
        for w in words(n):
            if found_sat:
                break
            for offset in range(1, n):
                c = build_same_cycle(w, offset, args.timeout_ms)
                cases.append(c)
                if c["result"] == "sat":
                    found_sat = True
                    break

    # Only if no same-cycle witness survives do we test distinct clean cycles.
    if not found_sat:
        for n1 in range(1, 4):
            if found_sat:
                break
            for n2 in range(1, 4):
                if found_sat:
                    break
                for w1 in words(n1):
                    if found_sat:
                        break
                    for w2 in words(n2):
                        c = build_distinct_cycles(w1, w2, args.timeout_ms)
                        cases.append(c)
                        if c["result"] == "sat":
                            found_sat = True
                            break

    sats = [c for c in cases if c["result"] == "sat"]
    unsats = [c for c in cases if c["result"] == "unsat"]
    unknowns = [c for c in cases if c["result"] == "unknown"]
    full_matrix_exhausted = not sats and len(cases) == 264

    if sats:
        classification = "PARK"
        residual = (
            "A bounded simultaneous collision-generated Good-row clean renewal topology survives even after attaching the shared Bad-shadow quasigroup, exact unique Bad carriers, grounded E677, left-row injectivity, and unique/no-fixer laws. Inspect this first SAT witness and identify the first source-backed coexistence constraint missing from the representation; do not append another isolated mark or widen cycle length blindly."
        )
    elif unknowns:
        classification = "REQUIRE_ATTACHMENT"
        residual = (
            "No tested simultaneous-renewal case is SAT, but at least one is verifier-UNKNOWN. Split by topology/word or ground only the causally active schemas before reading mathematics from the run."
        )
    else:
        classification = "PROMOTE"
        residual = (
            "Every tested same-cycle length 2-4 and distinct-cycle length 1-3 collision-generated simultaneous Good-row renewal word is UNSAT with the shared Bad-shadow/fixer theory. This is bounded discovery evidence only. Minimize UNSAT cases and extract a common length-independent invariant before any size-free claim."
        )

    out = {
        "consumed_frontier_schema": frontier["schema_version"],
        "scope": "bounded clean Good-row A/B renewal coexistence for two collision-generated E crossings sharing (u,b), with source-backed Bad-shadow ground consequences; uninterpreted universe; no finite-domain axiom",
        "cases": cases,
        "case_count": len(cases),
        "sat_count": len(sats), "unsat_count": len(unsats), "unknown_count": len(unknowns),
        "short_circuited_on_sat": bool(sats),
        "full_matrix_exhausted": full_matrix_exhausted,
        "smallest_sat": sats[0] if sats else None,
        "finite_domain_claimed": False, "finite_magma_claimed": False,
        "counterexample_claimed": False, "global_e677_implication_claimed": False,
        "size_free_theorem_claimed": False,
        "proposed_transition": {"classification": classification, "residual": residual},
    }
    p = Path(args.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("SIMULTANEOUS_RENEWAL_CASES=" + str(len(cases)))
    print("SIMULTANEOUS_RENEWAL_SAT=" + str(len(sats)))
    print("SIMULTANEOUS_RENEWAL_UNSAT=" + str(len(unsats)))
    print("SIMULTANEOUS_RENEWAL_UNKNOWN=" + str(len(unknowns)))
    print("SIMULTANEOUS_RENEWAL_SHORT_CIRCUITED=" + str(bool(sats)).lower())
    if sats:
        small = {k: v for k, v in sats[0].items() if "crossings" not in k}
        print("SIMULTANEOUS_RENEWAL_SMALLEST_SAT=" + json.dumps(small, sort_keys=True))
    print("SIMULTANEOUS_RENEWAL_TRANSITION=" + classification)
    print("SIMULTANEOUS_COLLISION_RENEWAL_PROBE_FINISHED")


if __name__ == "__main__":
    main()
