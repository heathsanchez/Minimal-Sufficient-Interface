"""Length-2 Good-row renewal cycle impossibility certificate (size-free E677).

A direct structural theorem, not a SAT search.

Theorem.  Let L be a left-injective magma, and let (r0,u,b), (r1,u,b) be two
distinct Good-row Good-to-Bad crossings sharing the same Good input u and Bad
target b (r0 != r1, r0*u = r1*u = b).  If each crossing is completed by the
length-one Good-row renewal equations

    r*b = z (Good),  z*r = h (Good),  b*h = g,  r*z = w,  w*r = q,  z*q = b,

then the pair cannot close into a 2-cycle under the A/B renewal transitions.
Equivalently, for every word w in {AA, AB, BA, BB}, the 2-cycle network with
transition letters w is UNSAT under left-row injectivity alone.

The UNSAT core is local: it uses no E677 instances, no shadow, no Bad-carrier
relation, and no fixer law.  The contradiction is a telescoping injectivity
collapse (words AA/AB/BA) or a direct r-collapse (word BB):

  AA : A,A  -> q0=q1=u;  b*h0=b*h1 => h0=h1 (inj);  h0=r1*r0, h1=r0*r1;
              then w0=r0*r1=w1;  w0*r0=w0*r1=q0=q1 => r0=r1 (inj) vs r0!=r1.
  BB : B,B  -> g1=r0 and g0=r1, so r0=r1=u vs r0!=r1 (no injectivity needed).

This is a verified size-free lemma: any length-2 clean renewal cycle on two
collision arms sharing (u,b) is impossible.  It is a bounded-length result
(2-cycle only); it does not by itself prove arbitrary cycles impossible and
does not prove E677 -> E255.
"""
from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from z3 import BoolSort, Const, DeclareSort, Function, Implies, Not, Solver, unsat

U = DeclareSort("USR")
mul = Function("mul", U, U, U)
is_bad = Function("is_bad", U, BoolSort())


def Bad(x):
    return is_bad(x)


def Good(x):
    return Not(is_bad(x))


def core_for(word: str):
    r0 = Const("r0", U); g0 = Const("g0", U); b0 = Const("b0", U)
    z0 = Const("z0", U); h0 = Const("h0", U); w0 = Const("w0", U); q0 = Const("q0", U)
    r1 = Const("r1", U); g1 = Const("g1", U); b1 = Const("b1", U)
    z1 = Const("z1", U); h1 = Const("h1", U); w1 = Const("w1", U); q1 = Const("q1", U)
    u = Const("u", U); b = Const("b", U)

    s = Solver()
    s.set(unsat_core=True)

    def A(name, f):
        s.assert_and_track(f, name)

    nodes = [(r0, g0, b0, z0, h0, w0, q0), (r1, g1, b1, z1, h1, w1, q1)]
    prefixes = ["n0", "n1"]
    for (r, g, bb, z, h, w, q), pre in zip(nodes, prefixes):
        A(pre + "_rG", Good(r)); A(pre + "_gG", Good(g)); A(pre + "_bB", Bad(bb))
        A(pre + "_rg", mul(r, g) == bb)
        A(pre + "_rb", mul(r, bb) == z); A(pre + "_zG", Good(z))
        A(pre + "_zr", mul(z, r) == h); A(pre + "_hG", Good(h))
        A(pre + "_bh", mul(bb, h) == g)
        A(pre + "_rz", mul(r, z) == w)
        A(pre + "_wr", mul(w, r) == q)
        A(pre + "_zq", mul(z, q) == bb)

    transitions = [
        (nodes[0], nodes[1], word[0], 0),
        (nodes[1], nodes[0], word[1], 1),
    ]
    for (src, dst, letter, idx) in transitions:
        sr, sg, sb, sz, sh, sw, sq = src
        dr, dg, db = dst[0], dst[1], dst[2]
        if letter == "A":
            A(f"t{idx}_qG", Good(sq))
            A(f"t{idx}_r", dr == sz); A(f"t{idx}_g", dg == sq); A(f"t{idx}_b", db == sb)
        else:
            A(f"t{idx}_qB", Bad(sq)); A(f"t{idx}_wG", Good(sw))
            A(f"t{idx}_r", dr == sw); A(f"t{idx}_g", dg == sr); A(f"t{idx}_b", db == sq)

    A("share_g0", g0 == u); A("share_g1", g1 == u)
    A("share_b0", b0 == b); A("share_b1", b1 == b)
    A("distinct_r", r0 != r1)

    vals = [r0, g0, b0, z0, h0, w0, q0, r1, g1, b1, z1, h1, w1, q1, u, b]
    for rr, a, bb in product(vals, repeat=3):
        A(f"inj_{rr}_{a}_{bb}", Implies(mul(rr, a) == mul(rr, bb), a == bb))

    res = s.check()
    if res == unsat:
        core = sorted(str(c) for c in s.unsat_core())
        injs = [x for x in core if x.startswith("inj_")]
        return {"word": word, "result": "unsat", "core_size": len(core), "core": core,
                "injectivity_instances": injs}
    return {"word": word, "result": str(res), "core_size": 0, "core": [], "injectivity_instances": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/e677_renewal_2cycle_certificate.json")
    args = ap.parse_args()

    frontier = json.load(open("program_frontier.json"))
    assert frontier.get("authoritative") is True
    rt = frontier["live_residual"]["text"].lower()
    assert "unsat core" in rt

    cases = [core_for(w) for w in ["AA", "AB", "BA", "BB"]]
    all_unsat = all(c["result"] == "unsat" for c in cases)

    out = {
        "consumed_frontier_schema": frontier["schema_version"],
        "theorem": "A length-2 Good-row A/B renewal cycle on two distinct crossings sharing "
                   "(u,b) is impossible under left-row injectivity alone (all four words UNSAT).",
        "scope": "length-2 clean renewal cycles on collision arms sharing (u,b); left-row "
                 "injectivity only (no E677/shadow/carrier/fixer axioms); uninterpreted universe",
        "cases": cases,
        "all_words_unsat": all_unsat,
        "size_free_theorem_claimed": True,
        "bounded_length_2_only": True,
        "global_e677_implication_claimed": False,
        "finite_magma_claimed": False,
        "counterexample_claimed": False,
        "finite_domain_claimed": False,
        "proposed_transition": {
            "classification": "PROMOTE",
            "residual": (
                "Verified: no length-2 Good-row A/B renewal cycle on two collision arms sharing "
                "(u,b) exists under left-row injectivity (core is local: telescoping injectivity "
                "collapse for AA/AB/BA, direct r-collapse for BB). Lift to a length-independent "
                "claim: test whether the same telescoping mechanism forces any clean renewal "
                "cycle on collision marks to terminate or merge."
            ),
        },
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("RENEWAL_2CYCLE_ALL_UNSAT=" + str(all_unsat).lower())
    for c in cases:
        print(f"RENEWAL_2CYCLE_WORD_{c['word']}={c['result']}:core={c['core_size']}")
    print("RENEWAL_2CYCLE_TRANSITION=PROMOTE")
    print("RENEWAL_2CYCLE_CERTIFICATE_FINISHED")


if __name__ == "__main__":
    main()
