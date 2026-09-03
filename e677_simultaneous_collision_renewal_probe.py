"""Bounded simultaneous-renewal discovery probe for the size-free E677 frontier.

This is deliberately a consequence model, not a finite magma search.

Source-backed ingredients (frozen upstream commit 5a205195...):
- two distinct collision rows can generate Good-row E crossings (r,u,b)
  sharing the same Good input u and Bad target b;
- the exact length-one Good-row renewal equations and A/B transitions;
- global E677 and left-row injectivity on the named fragment;
- Good inputs have the unique sigma-fixer; Bad inputs have no fixer;
- under terminal ZERO reuse/no-HIT, Bad carries an idempotent Latin E677
  shadow quasigroup, with off-diagonal shadow product equal to original mul
  and exact unique Bad carriers N_B(u,v)=1.

We enumerate short clean A/B cycle words only as a discovery tool.  There are
no terminal/merger events in an admitted case because every transition is A/B
and crossing triples are required to remain distinct where the topology says
there is no merger.

SAT means only that this bounded simultaneous abstraction survives.  UNSAT for
all tested words is not a size-free theorem: it is a request to minimize a
recurring contradiction and extract a length-independent invariant.
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
        self.tag = tag
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
    """Exact length-one Good-row crossing/renewal equations."""
    return [
        Good(n.r), Good(n.g), Bad(n.b),
        mul(n.r, n.g) == n.b,
        mul(n.r, n.b) == n.z, Good(n.z),
        mul(n.z, n.r) == n.h, Good(n.h),  # clean: no hinge terminal
        mul(n.b, n.h) == n.g,
        mul(n.r, n.z) == n.w,
        mul(n.w, n.r) == n.q,
        mul(n.z, n.q) == n.b,
    ]


def transition_axioms(n: Node, nxt: Node, letter: str):
    assert letter in {"A", "B"}
    if letter == "A":
        return [
            Good(n.q),
            nxt.r == n.z,
            nxt.g == n.q,
            nxt.b == n.b,
        ]
    return [
        Bad(n.q), Good(n.w),
        nxt.r == n.w,
        nxt.g == n.r,
        nxt.b == n.q,
    ]


def crossing_distinct(a: Node, b: Node):
    return Or(a.r != b.r, a.g != b.g, a.b != b.b)


def named_ground_axioms(vals, bad_terms, good_terms):
    """Ground only the source-backed global schemas on the named fragment."""
    A = []

    # Assert all statically known colours.  Equality completion is left to SMT.
    A.extend(Bad(x) for x in bad_terms)
    A.extend(Good(x) for x in good_terms)

    # E677 and left-row injectivity on named terms only.
    for x, y in product(vals, repeat=2):
        A.append(E677(x, y))
    for r, a, b in product(vals, repeat=3):
        A.append(Implies(mul(r, a) == mul(r, b), a == b))

    # Unique Good fixer / no Bad fixer, grounded on named rows.
    for a in good_terms:
        A.append(mul(sigma(a), a) == a)
        for r in vals:
            A.append(Implies(mul(r, a) == a, r == sigma(a)))
    for a in bad_terms:
        A.append(mul(sigma(a), a) != a)
        for r in vals:
            A.append(mul(r, a) != a)

    # ZERO-reuse/no-HIT Bad-shadow consequences used by the preceding verifier.
    # Bad squares and sigma are Good; D remains Bad.
    for x in bad_terms:
        A.append(Good(mul(x, x)))
        A.append(Good(sigma(x)))
        A.append(Bad(mul(sigma(x), x)))

    # Off-diagonal Bad closure and exact unique Bad carrier N_B(u,v)=1.
    for r, u in product(bad_terms, repeat=2):
        A.append(Implies(r != u, Bad(mul(r, u))))
    for u, v in product(bad_terms, repeat=2):
        A.append(Implies(u != v, And(
            Bad(carrier(u, v)),
            mul(carrier(u, v), u) == v,
        )))
    for r, u, v in product(bad_terms, repeat=3):
        A.append(Implies(
            And(u != v, mul(r, u) == v),
            r == carrier(u, v),
        ))

    # Idempotent Latin E677 Bad shadow, linked off diagonal to original mul.
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


def build_same_cycle(word: str, offset: int, timeout_ms: int):
    n = len(word)
    nodes = [Node(f"S{i}") for i in range(n)]
    s = Solver(); s.set(timeout=timeout_ms)
    for nd in nodes:
        s.add(*node_axioms(nd))
    for i, letter in enumerate(word):
        s.add(*transition_axioms(nodes[i], nodes[(i + 1) % n], letter))
    # Two collision-generated starts share exactly (u,b), with distinct rows.
    s.add(nodes[0].g == nodes[offset].g)
    s.add(nodes[0].b == nodes[offset].b)
    s.add(nodes[0].r != nodes[offset].r)
    # A clean cycle has not merged earlier.
    for i in range(n):
        for j in range(i + 1, n):
            s.add(crossing_distinct(nodes[i], nodes[j]))

    vals = []
    for nd in nodes: vals.extend(nd.constants())
    bad_terms = [nd.b for nd in nodes]
    good_terms = [x for nd in nodes for x in (nd.r, nd.g, nd.z, nd.h)]
    # q/w colours are letter-dependent.
    for nd, letter in zip(nodes, word):
        if letter == "A": good_terms.append(nd.q)
        else:
            bad_terms.append(nd.q); good_terms.append(nd.w)
    # de-duplicate expression objects by string identity to limit grounding.
    def uniq(xs):
        d = {}
        for x in xs: d[str(x)] = x
        return list(d.values())
    vals, bad_terms, good_terms = uniq(vals), uniq(bad_terms), uniq(good_terms)
    ground = named_ground_axioms(vals, bad_terms, good_terms)
    s.add(*ground)
    res = s.check()
    out = {"topology":"same", "word":word, "offset":offset, "result":str(res),
           "named_terms":len(vals), "bad_role_terms":len(bad_terms),
           "ground_axioms":len(ground), "reason_unknown":s.reason_unknown() if res == unknown else ""}
    if res == sat:
        m = s.model()
        out["crossings"] = [
            {k:str(m.eval(getattr(nd,k), model_completion=True)) for k in ("r","g","b","z","h","w","q")}
            for nd in nodes
        ]
    return out


def build_distinct_cycles(word1: str, word2: str, timeout_ms: int):
    ns1 = [Node(f"L{i}") for i in range(len(word1))]
    ns2 = [Node(f"R{i}") for i in range(len(word2))]
    s = Solver(); s.set(timeout=timeout_ms)
    for nd in ns1 + ns2: s.add(*node_axioms(nd))
    for nodes, word in ((ns1, word1),(ns2, word2)):
        for i, letter in enumerate(word):
            s.add(*transition_axioms(nodes[i], nodes[(i + 1) % len(nodes)], letter))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                s.add(crossing_distinct(nodes[i], nodes[j]))
    # Collision handoff: same Good input/Bad target, genuinely distinct rows.
    s.add(ns1[0].g == ns2[0].g, ns1[0].b == ns2[0].b, ns1[0].r != ns2[0].r)
    # Distinct-cycle topology excludes any crossing merger across the cycles.
    for a in ns1:
        for b in ns2:
            s.add(crossing_distinct(a,b))

    vals=[]
    for nd in ns1+ns2: vals.extend(nd.constants())
    bad_terms=[nd.b for nd in ns1+ns2]
    good_terms=[x for nd in ns1+ns2 for x in (nd.r,nd.g,nd.z,nd.h)]
    for nodes, word in ((ns1,word1),(ns2,word2)):
        for nd, letter in zip(nodes,word):
            if letter == "A": good_terms.append(nd.q)
            else:
                bad_terms.append(nd.q); good_terms.append(nd.w)
    def uniq(xs):
        d={}
        for x in xs: d[str(x)] = x
        return list(d.values())
    vals,bad_terms,good_terms=uniq(vals),uniq(bad_terms),uniq(good_terms)
    ground=named_ground_axioms(vals,bad_terms,good_terms)
    s.add(*ground)
    res=s.check()
    out={"topology":"distinct","word1":word1,"word2":word2,"result":str(res),
         "named_terms":len(vals),"bad_role_terms":len(bad_terms),"ground_axioms":len(ground),
         "reason_unknown":s.reason_unknown() if res == unknown else ""}
    if res == sat:
        m=s.model()
        out["left_crossings"]=[{k:str(m.eval(getattr(nd,k),model_completion=True)) for k in ("r","g","b","z","h","w","q")} for nd in ns1]
        out["right_crossings"]=[{k:str(m.eval(getattr(nd,k),model_completion=True)) for k in ("r","g","b","z","h","w","q")} for nd in ns2]
    return out


def words(n):
    return ["".join(w) for w in product("AB", repeat=n)]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/e677_simultaneous_collision_renewal_probe.json")
    ap.add_argument("--timeout-ms", type=int, default=30000)
    args=ap.parse_args()

    frontier=json.load(open("program_frontier.json"))
    assert frontier.get("authoritative") is True
    assert frontier["schema_version"] >= 11
    rt=frontier["live_residual"]["text"].lower()
    assert "simultaneous" in rt and "renewal" in rt and "collision" in rt

    cases=[]
    # Same-cycle coexistence requires two distinct marked positions, hence n>=2.
    for n in range(2,5):
        for w in words(n):
            for offset in range(1,n):
                cases.append(build_same_cycle(w,offset,args.timeout_ms))
    # Distinct clean cycles: shortest words first, through length 3 each.
    for n1 in range(1,4):
        for n2 in range(1,4):
            for w1 in words(n1):
                for w2 in words(n2):
                    cases.append(build_distinct_cycles(w1,w2,args.timeout_ms))

    sats=[c for c in cases if c["result"]=="sat"]
    unsats=[c for c in cases if c["result"]=="unsat"]
    unknowns=[c for c in cases if c["result"]=="unknown"]
    if sats:
        classification="PARK"
        residual=(
            "At least one bounded simultaneous collision-generated Good-row clean renewal topology survives even after attaching the shared Bad-shadow quasigroup, exact unique Bad carriers, grounded E677, left-row injectivity, and unique/no-fixer laws. Inspect the smallest SAT witness and identify the first source-backed coexistence constraint missing from this representation; do not append another isolated mark or widen cycle length blindly."
        )
    elif unknowns:
        classification="REQUIRE_ATTACHMENT"
        residual=(
            "No tested simultaneous-renewal case is SAT, but at least one is verifier-UNKNOWN. Split by topology/word or ground only the causally active shadow schemas before reading mathematics from the run."
        )
    else:
        classification="PROMOTE"
        residual=(
            "Every tested same-cycle (length 2-4) and distinct-cycle (length 1-3 each) collision-generated simultaneous Good-row renewal word is UNSAT with the shared Bad-shadow/fixer theory. This is bounded discovery evidence only. Minimize UNSAT cases across word lengths and extract the common length-independent invariant before any size-free claim."
        )

    out={
        "consumed_frontier_schema":frontier["schema_version"],
        "scope":"bounded clean Good-row A/B renewal coexistence for two collision-generated E crossings sharing (u,b), with source-backed Bad-shadow ground consequences; uninterpreted universe; no finite-domain axiom",
        "cases":cases,
        "case_count":len(cases),
        "sat_count":len(sats),"unsat_count":len(unsats),"unknown_count":len(unknowns),
        "smallest_sat":sats[0] if sats else None,
        "finite_domain_claimed":False,"finite_magma_claimed":False,"counterexample_claimed":False,
        "global_e677_implication_claimed":False,"size_free_theorem_claimed":False,
        "proposed_transition":{"classification":classification,"residual":residual},
    }
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("SIMULTANEOUS_RENEWAL_CASES="+str(len(cases)))
    print("SIMULTANEOUS_RENEWAL_SAT="+str(len(sats)))
    print("SIMULTANEOUS_RENEWAL_UNSAT="+str(len(unsats)))
    print("SIMULTANEOUS_RENEWAL_UNKNOWN="+str(len(unknowns)))
    if sats:
        print("SIMULTANEOUS_RENEWAL_SMALLEST_SAT="+json.dumps({k:v for k,v in sats[0].items() if "crossings" not in k},sort_keys=True))
    print("SIMULTANEOUS_RENEWAL_TRANSITION="+classification)
    print("SIMULTANEOUS_COLLISION_RENEWAL_PROBE_FINISHED")


if __name__ == "__main__":
    main()
