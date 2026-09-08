"""Install a verified contextual-transport constructor and reuse it on a held-out law.

This is a bounded developmental adapter, not an unrestricted grammar inventor.
The existing arithmetic State is preserved; a separate typed capability archive
uses its source bound, digest and rejection protocol. The independent Lean gate
checks the mathematical proof schema. Python certificates are not Lean proofs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import open_development_test as arithmetic
from austin_promotion_compiler import (
    Var, Op, V, O, substitute, replace_at, discover_promotions,
    law40909, law11116, render,
)

OPERATOR = "contextual_transport"
PROOF = "AustinCapabilityInstallation.transport"
SOURCE = ("install", ("operator", OPERATOR), ("proof", PROOF))


@dataclass(frozen=True)
class CapabilityCertificate:
    name: str
    source: tuple
    dependencies: tuple[str, ...]
    proof: str
    identity: str


@dataclass(frozen=True)
class DevelopmentState:
    arithmetic_state: arithmetic.State = arithmetic.State()
    archive: tuple[CapabilityCertificate, ...] = ()

    @property
    def bound(self):
        return self.arithmetic_state.bound


@dataclass(frozen=True)
class Obligation:
    name: str
    lhs: object
    rhs: object
    variables: frozenset[str]


def obligation(name, source):
    lhs, rhs, variables = source()
    return Obligation(name, lhs, rhs, variables)


def certificate():
    deps = ()
    return CapabilityCertificate(OPERATOR, SOURCE, deps, PROOF,
        arithmetic.digest([OPERATOR, SOURCE, deps, PROOF]))


def verify_state(state):
    arithmetic.Verifier.state(state.arithmetic_state)
    if state.bound != arithmetic.SOURCE_BOUND:
        raise arithmetic.Rejected("Source bound changed")
    seen = set()
    for cert in state.archive:
        if cert != certificate() or cert.identity in seen:
            raise arithmetic.Rejected("Unknown, forged or duplicate capability")
        seen.add(cert.identity)
    return True


def candidates(state):
    verify_state(state)
    return ("root",) + ((OPERATOR,) if state.archive else ())


def derive(spec, operator, branch_left=None, branch_right=None):
    """Enumerate the current constructor grammar, not named target policies."""
    if operator not in ("root", OPERATOR):
        raise arithmetic.Rejected("Unknown constructor")
    branch_left = branch_left or O(V("A"), V("p"))
    branch_right = branch_right or V("q")
    found = discover_promotions(spec.lhs, spec.rhs, spec.variables,
                                branch_left, branch_right)
    if operator == "root":
        found = [p for p in found if not p.path]
    return tuple(found)


def develop(state, spec):
    """Select a structural constructor from a training obligation only."""
    verify_state(state)
    if state.archive:
        return state, None
    rejected = []
    for candidate in ("root", OPERATOR):
        result = derive(spec, candidate)
        if not result:
            rejected.append(candidate)
            continue
        if candidate == OPERATOR:
            cert = certificate()
            after = DevelopmentState(state.arithmetic_state, state.archive + (cert,))
            verify_state(after)
            return after, {"certificate": cert, "source": SOURCE,
                           "rejected": tuple(rejected), "promotions": result}
    return state, None


def apply(state, spec):
    verify_state(state)
    return tuple(p for candidate in candidates(state)
                 for p in derive(spec, candidate))


def variables(t):
    if isinstance(t, Var):
        return {t.name}
    return variables(t.left) | variables(t.right)


def lean_term(t):
    if isinstance(t, Var):
        return t.name
    return f"(op {lean_term(t.left)} {lean_term(t.right)})"


def context_at(t, path):
    if not path:
        return V("hole")
    if not isinstance(t, Op):
        raise arithmetic.Rejected("Invalid context path")
    if path[0] == 0:
        return O(context_at(t.left, path[1:]), t.right)
    if path[0] == 1:
        return O(t.left, context_at(t.right, path[1:]))
    raise arithmetic.Rejected("Invalid context path")


def theorem_source(spec, promotion):
    """Generate a proof by generic congruence followed by the source law."""
    env = dict(promotion.substitution)
    original = substitute(spec.lhs, env)
    expected = replace_at(original, promotion.path, V("q"))
    assert expected == promotion.lhs
    context = context_at(original, promotion.path)
    old = O(V("A"), V("p"))
    assert replace_at(original, promotion.path, old) == original
    assert replace_at(original, promotion.path, V("q")) == promotion.lhs
    free = sorted((variables(spec.lhs) | variables(spec.rhs)) - set(env))
    args = " ".join(lean_term(env.get(v, V(v))) for v in sorted(spec.variables))
    binders = " ".join(free)
    extra = f" ({binders} : G)" if binders else ""
    return "\n".join([
        f"theorem sound_{spec.name} {{G : Type}} (op : G → G → G)",
        f"    (hLaw : ∀ { ' '.join(sorted(spec.variables)) } : G, {lean_term(spec.lhs)} = {lean_term(spec.rhs)})",
        f"    {{A p q : G}} (hBranch : op A p = q){extra} :",
        f"    {lean_term(promotion.lhs)} = {lean_term(promotion.rhs)} := by",
        f"  have hctx : {lean_term(promotion.lhs)} = {lean_term(original)} :=",
        f"    transport (fun hole => {lean_term(context)}) hBranch.symm",
        f"  exact hctx.trans (hLaw {args})",
        "",
    ])


def lean_source():
    training = obligation("E40909", law40909)
    heldout = obligation("E11116", law11116)
    state, evidence = develop(DevelopmentState(), training)
    assert evidence is not None
    lines = ["import Std", "", "namespace AustinCapabilityInstallation", "",
             "theorem transport {G : Type} (C : G → G) {a b : G} (h : a = b) :",
             "    C a = C b := congrArg C h", ""]
    for spec in (training, heldout):
        for p in apply(state, spec):
            lines.append(theorem_source(spec, p))
    lines += ["end AustinCapabilityInstallation", ""]
    return "\n".join(lines)


def qualification():
    training = obligation("E40909", law40909)
    heldout = obligation("E11116", law11116)
    before = DevelopmentState()
    after, evidence = develop(before, training)
    assert evidence is not None
    assert verify_state(after)
    assert after.arithmetic_state == before.arithmetic_state
    assert after.bound == before.bound == arithmetic.SOURCE_BOUND
    assert len(SOURCE) == arithmetic.SOURCE_BOUND
    assert evidence["rejected"] == ("root",)
    assert len(apply(before, heldout)) == 0
    assert len(apply(after, heldout)) == 1
    assert len(apply(DevelopmentState(after.arithmetic_state), heldout)) == 0
    assert after.archive == before.archive + (evidence["certificate"],)
    return {"training": training.name, "heldout": heldout.name,
            "baseline_reachable": 0, "installed_reachable": 1,
            "ablation_reachable": 0, "source_bound": after.bound,
            "certificate": evidence["certificate"].identity,
            "scope": "bounded structural promotion; external Lean proof required"}


if __name__ == "__main__":
    import json
    print(json.dumps(qualification(), sort_keys=True))
