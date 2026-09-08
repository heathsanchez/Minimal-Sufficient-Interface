"""Discover recursive branch-promotion schemas from a source law.

The compiler is deliberately tiny.  It is given a law lhs = rhs and a generic
known branch A⋄p = q.  It scans lhs subterms and asks where the *law subterm*,
using only the law's universally quantified variables as wildcards, can match
an arbitrary branch lhs A⋄p.  For every such attachment it:

1. computes the induced substitution on source-law variables;
2. instantiates the whole law;
3. replaces the attached occurrence by q;
4. emits the resulting outer equality as a candidate promotion rule.

The output is only a candidate.  In the experiment, Lean independently proves
soundness of the E40909 and E11116 candidates in AustinRecursiveObligation.lean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Mapping


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Op:
    left: "Term"
    right: "Term"


Term = Var | Op
Path = tuple[int, ...]


def V(name: str) -> Var:
    return Var(name)


def O(left: Term, right: Term) -> Op:
    return Op(left, right)


def subterms(term: Term, path: Path = ()) -> Iterator[tuple[Path, Term]]:
    yield path, term
    if isinstance(term, Op):
        yield from subterms(term.left, path + (0,))
        yield from subterms(term.right, path + (1,))


def match_law_pattern(
    pattern: Term,
    target: Term,
    law_variables: frozenset[str],
    env: dict[str, Term] | None = None,
) -> dict[str, Term] | None:
    """Directionally match a law term against a rigid target term.

    Only variables in ``law_variables`` may bind.  Target variables such as
    A/p are rigid placeholders representing arbitrary branch coordinates.
    """
    env = {} if env is None else dict(env)
    if isinstance(pattern, Var):
        if pattern.name not in law_variables:
            return env if pattern == target else None
        old = env.get(pattern.name)
        if old is None:
            env[pattern.name] = target
            return env
        return env if old == target else None

    if not isinstance(target, Op):
        return None
    env1 = match_law_pattern(pattern.left, target.left, law_variables, env)
    if env1 is None:
        return None
    return match_law_pattern(pattern.right, target.right, law_variables, env1)


def substitute(term: Term, env: Mapping[str, Term]) -> Term:
    if isinstance(term, Var):
        return env.get(term.name, term)
    return O(substitute(term.left, env), substitute(term.right, env))


def replace_at(term: Term, path: Path, replacement: Term) -> Term:
    if not path:
        return replacement
    if not isinstance(term, Op):
        raise ValueError("path descends through a variable")
    head, *tail = path
    rest = tuple(tail)
    if head == 0:
        return O(replace_at(term.left, rest, replacement), term.right)
    if head == 1:
        return O(term.left, replace_at(term.right, rest, replacement))
    raise ValueError(f"bad path component {head}")


@dataclass(frozen=True)
class Promotion:
    path: Path
    substitution: tuple[tuple[str, Term], ...]
    lhs: Term
    rhs: Term


def discover_promotions(
    law_lhs: Term,
    law_rhs: Term,
    law_variables: frozenset[str],
    branch_left: Term,
    branch_right: Term,
) -> list[Promotion]:
    """Find all generic branch attachments in ``law_lhs``."""
    found: list[Promotion] = []
    for path, candidate in subterms(law_lhs):
        env = match_law_pattern(candidate, branch_left, law_variables)
        if env is None:
            continue
        instantiated_lhs = substitute(law_lhs, env)
        instantiated_rhs = substitute(law_rhs, env)
        promoted_lhs = replace_at(instantiated_lhs, path, branch_right)
        found.append(
            Promotion(
                path=path,
                substitution=tuple(sorted(env.items())),
                lhs=promoted_lhs,
                rhs=instantiated_rhs,
            )
        )
    return found


def render(term: Term) -> str:
    if isinstance(term, Var):
        return term.name
    return f"({render(term.left)}⋄{render(term.right)})"


def render_promotion(p: Promotion) -> str:
    return f"{render(p.lhs)} = {render(p.rhs)}"


def law40909() -> tuple[Term, Term, frozenset[str]]:
    x, y, z = V("x"), V("y"), V("z")
    lhs = O(O(O(O(O(y, x), y), y), z), y)
    return lhs, x, frozenset({"x", "y", "z"})


def law11116() -> tuple[Term, Term, frozenset[str]]:
    x, y, z = V("x"), V("y"), V("z")
    lhs = O(y, O(O(x, O(z, x)), O(y, y)))
    return lhs, x, frozenset({"x", "y", "z"})


def compile_named(name: str) -> list[Promotion]:
    A, p, q = V("A"), V("p"), V("q")
    branch_lhs = O(A, p)
    if name == "E40909":
        lhs, rhs, variables = law40909()
    elif name == "E11116":
        lhs, rhs, variables = law11116()
    else:
        raise ValueError(name)
    return discover_promotions(lhs, rhs, variables, branch_lhs, q)


if __name__ == "__main__":
    for name in ("E40909", "E11116"):
        promotions = compile_named(name)
        print(name)
        for p in promotions:
            print(" path", p.path, "=>", render_promotion(p))
