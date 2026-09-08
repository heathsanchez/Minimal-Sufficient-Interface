#!/usr/bin/env python3
"""Blind synthesis test for recursive Austin-law obligations.

Input to the synthesizer is only:
  * a source equation AST,
  * its source variables,
  * an observed residual branch A ◇ p = q,
  * a fresh parameter F.

It enumerates atomic source substitutions, finds an occurrence of the observed
branch on one side of the instantiated source law, rewrites that occurrence by
A ◇ p = q, and returns the forced residual equations.

The test succeeds only if this generic procedure rediscovers the reported
promotion constructors for BOTH E40909 and E11116.  No law-specific promotion
rule is supplied to the synthesizer.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Mapping, Sequence, TypeAlias


Term: TypeAlias = str | tuple[str, "Term", "Term"]
Equation: TypeAlias = tuple[Term, Term]


def op(a: Term, b: Term) -> Term:
    return ("op", a, b)


def substitute(t: Term, mapping: Mapping[str, Term]) -> Term:
    if isinstance(t, str):
        return mapping.get(t, t)
    _, a, b = t
    return op(substitute(a, mapping), substitute(b, mapping))


def replace_one(t: Term, old: Term, new: Term) -> list[Term]:
    """Every term obtained by replacing exactly one occurrence old -> new."""
    out: list[Term] = []
    if t == old:
        out.append(new)
    if not isinstance(t, str):
        _, a, b = t
        out.extend(op(a2, b) for a2 in replace_one(a, old, new))
        out.extend(op(a, b2) for b2 in replace_one(b, old, new))
    return out


def render(t: Term) -> str:
    if isinstance(t, str):
        return t
    _, a, b = t
    return f"({render(a)}◇{render(b)})"


@dataclass(frozen=True)
class Candidate:
    substitution: tuple[tuple[str, Term], ...]
    rewritten_side: str
    equation: Equation


def synthesize(
    law: Equation,
    source_variables: Sequence[str],
    *,
    branch_left: Term,
    branch_right: Term,
    atoms: Sequence[Term],
) -> list[Candidate]:
    """Generic one-residual consequence compiler.

    There is deliberately no E40909/E11116 branch-generation code here.
    """
    found: list[Candidate] = []
    seen: set[tuple[tuple[tuple[str, Term], ...], str, Equation]] = set()

    for values in product(atoms, repeat=len(source_variables)):
        mapping = dict(zip(source_variables, values))
        frozen_mapping = tuple((v, mapping[v]) for v in source_variables)
        lhs = substitute(law[0], mapping)
        rhs = substitute(law[1], mapping)

        for side_name, side, other in (("lhs", lhs, rhs), ("rhs", rhs, lhs)):
            for rewritten in replace_one(side, branch_left, branch_right):
                eq = (rewritten, other)
                key = (frozen_mapping, side_name, eq)
                if key not in seen:
                    seen.add(key)
                    found.append(Candidate(frozen_mapping, side_name, eq))
    return found


# ---------------------------------------------------------------------------
# Frozen source laws.  These are the only law-specific inputs.
# ---------------------------------------------------------------------------

x, y, z = "x", "y", "z"
A, p, q, F = "A", "p", "q", "F"

# E40909: ((((y◇x)◇y)◇y)◇z)◇y = x
LAW_40909: Equation = (
    op(op(op(op(op(y, x), y), y), z), y),
    x,
)

# E11116: y◇((x◇(z◇x))◇(y◇y)) = x
LAW_11116: Equation = (
    op(y, op(op(x, op(z, x)), op(y, y))),
    x,
)

BRANCH_LEFT = op(A, p)
ATOMS = (A, p, F)

# These are assertions about the output, not rules given to synthesize().
EXPECTED_40909: Equation = (
    op(op(op(op(q, A), A), F), A),
    p,
)
EXPECTED_11116: Equation = (
    op(F, op(op(p, q), op(F, F))),
    p,
)


def contains_equation(candidates: Iterable[Candidate], expected: Equation) -> bool:
    return any(c.equation == expected for c in candidates)


def main() -> None:
    c40909 = synthesize(
        LAW_40909,
        (x, y, z),
        branch_left=BRANCH_LEFT,
        branch_right=q,
        atoms=ATOMS,
    )
    c11116 = synthesize(
        LAW_11116,
        (x, y, z),
        branch_left=BRANCH_LEFT,
        branch_right=q,
        atoms=ATOMS,
    )

    assert contains_equation(c40909, EXPECTED_40909), (
        "generic synthesis did not recover E40909 promotion: "
        + render(EXPECTED_40909[0])
        + " = "
        + render(EXPECTED_40909[1])
    )
    assert contains_equation(c11116, EXPECTED_11116), (
        "generic synthesis did not recover E11116 promotion: "
        + render(EXPECTED_11116[0])
        + " = "
        + render(EXPECTED_11116[1])
    )

    def witness(candidates: list[Candidate], expected: Equation) -> Candidate:
        return next(c for c in candidates if c.equation == expected)

    w40909 = witness(c40909, EXPECTED_40909)
    w11116 = witness(c11116, EXPECTED_11116)

    print("BLIND_RECURSIVE_OBLIGATION_SYNTHESIS=PASS")
    print(f"E40909 candidates={len(c40909)}")
    print(f"E40909 substitution={dict(w40909.substitution)}")
    print(f"E40909 forced={render(w40909.equation[0])} = {render(w40909.equation[1])}")
    print(f"E11116 candidates={len(c11116)}")
    print(f"E11116 substitution={dict(w11116.substitution)}")
    print(f"E11116 forced={render(w11116.equation[0])} = {render(w11116.equation[1])}")


if __name__ == "__main__":
    main()
