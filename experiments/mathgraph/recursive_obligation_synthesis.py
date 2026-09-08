#!/usr/bin/env python3
"""Blind synthesis test for recursive Austin-law obligations.

Input to the synthesizer is only:
  * a source equation AST,
  * its source variables,
  * an observed residual branch A ◇ p = q,
  * a small atom basis including one fresh parameter.

The generic operation is:
  instantiate source law -> find residual branch as a subterm -> rewrite it ->
  retain the new forced equality -> promote it as the next residual branch.

The test has three gates:
  1. one-step rediscovery for E40909 and E11116;
  2. causal ablation: source instantiation alone cannot produce the promoted rule;
  3. recursive replay: the same generic operation re-enters on its own output for
     several generations without a law-specific promotion routine.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Mapping, Sequence, TypeAlias


Term: TypeAlias = str | tuple[str, "Term", "Term"]
Equation: TypeAlias = tuple[Term, Term]


def op(a: Term, b: Term) -> Term:
    return ("op", a, b)


def is_op(t: Term) -> bool:
    return not isinstance(t, str) and t[0] == "op"


def children(t: Term) -> tuple[Term, Term]:
    assert is_op(t)
    return t[1], t[2]  # type: ignore[index]


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


def contains(t: Term, needle: Term) -> bool:
    if t == needle:
        return True
    if isinstance(t, str):
        return False
    return contains(t[1], needle) or contains(t[2], needle)


def size(t: Term) -> int:
    if isinstance(t, str):
        return 1
    return 1 + size(t[1]) + size(t[2])


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


def direct_instances(
    law: Equation,
    source_variables: Sequence[str],
    atoms: Sequence[Term],
) -> set[Equation]:
    """Ablation baseline: source instantiation with NO residual rewrite."""
    out: set[Equation] = set()
    for values in product(atoms, repeat=len(source_variables)):
        mapping = dict(zip(source_variables, values))
        out.add((substitute(law[0], mapping), substitute(law[1], mapping)))
    return out


def synthesize(
    law: Equation,
    source_variables: Sequence[str],
    *,
    branch_left: Term,
    branch_right: Term,
    atoms: Sequence[Term],
) -> list[Candidate]:
    """Generic residual-conditioned consequence compiler.

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


def next_branch_blind(
    law: Equation,
    source_variables: Sequence[str],
    branch: Equation,
    fresh: Term,
) -> tuple[Equation, Candidate]:
    """Promote one residual without a law-specific constructor.

    The only generic branch interface required is that the residual lhs is a
    binary root A◇p=q.  Candidate selection is consequence-driven:
      * output rhs must recover the previous p;
      * output lhs must be another binary root;
      * it must actually use the fresh parameter;
      * choose the smallest such forced equality deterministically.
    """
    branch_left, branch_right = branch
    if not is_op(branch_left):
        raise AssertionError("residual branch lhs is not a binary root")
    A_now, p_now = children(branch_left)
    atoms = (A_now, p_now, fresh)
    candidates = synthesize(
        law,
        source_variables,
        branch_left=branch_left,
        branch_right=branch_right,
        atoms=atoms,
    )
    admissible = [
        c for c in candidates
        if c.equation[1] == p_now
        and is_op(c.equation[0])
        and contains(c.equation[0], fresh)
        and c.equation != branch
    ]
    if not admissible:
        raise AssertionError("no recursively promotable forced branch found")
    admissible.sort(key=lambda c: (size(c.equation[0]), render(c.equation[0]), c.substitution))
    chosen = admissible[0]
    return chosen.equation, chosen


def replay(
    law: Equation,
    source_variables: Sequence[str],
    seed: Equation,
    generations: int,
    prefix: str,
) -> tuple[list[Equation], list[Candidate]]:
    chain = [seed]
    witnesses: list[Candidate] = []
    for n in range(generations):
        nxt, witness = next_branch_blind(
            law,
            source_variables,
            chain[-1],
            f"{prefix}{n}",
        )
        if nxt in chain:
            raise AssertionError("recursive promotion cycled instead of generating a new obligation")
        chain.append(nxt)
        witnesses.append(witness)
    return chain, witnesses


# ---------------------------------------------------------------------------
# Frozen source laws.  These are the only law-specific inputs to synthesis.
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

SEED: Equation = (op(A, p), q)
ATOMS = (A, p, F)

# Assertions about one-step output, never consulted by synthesize/replay.
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
        branch_left=SEED[0],
        branch_right=SEED[1],
        atoms=ATOMS,
    )
    c11116 = synthesize(
        LAW_11116,
        (x, y, z),
        branch_left=SEED[0],
        branch_right=SEED[1],
        atoms=ATOMS,
    )

    # Gate 1: blind one-step rediscovery.
    assert contains_equation(c40909, EXPECTED_40909)
    assert contains_equation(c11116, EXPECTED_11116)

    # Gate 2: causal ablation.  The exact promoted rule is absent if residual
    # rewriting is removed; it is not merely a lucky direct source instance.
    direct40909 = direct_instances(LAW_40909, (x, y, z), ATOMS)
    direct11116 = direct_instances(LAW_11116, (x, y, z), ATOMS)
    assert EXPECTED_40909 not in direct40909
    assert EXPECTED_11116 not in direct11116

    # Gate 3: recursive re-entry of the same generic operation.
    chain40909, ws40909 = replay(LAW_40909, (x, y, z), SEED, 5, "u")
    chain11116, ws11116 = replay(LAW_11116, (x, y, z), SEED, 5, "v")
    assert len(set(chain40909)) == 6
    assert len(set(chain11116)) == 6

    # The first blind replay stage must coincide with the independently stated
    # one-step targets modulo the fresh variable name.
    expected40909_u0 = substitute(EXPECTED_40909[0], {F: "u0"}), EXPECTED_40909[1]
    expected11116_v0 = substitute(EXPECTED_11116[0], {F: "v0"}), EXPECTED_11116[1]
    assert chain40909[1] == expected40909_u0
    assert chain11116[1] == expected11116_v0

    print("BLIND_RECURSIVE_OBLIGATION_SYNTHESIS=PASS")
    print("ABLATION_DIRECT_SOURCE_ONLY=PASS")
    print("RECURSIVE_REENTRY_5_GENERATIONS=PASS")
    print(f"E40909 initial_candidates={len(c40909)} direct_instances={len(direct40909)}")
    print(f"E11116 initial_candidates={len(c11116)} direct_instances={len(direct11116)}")
    for label, chain, witnesses in (
        ("E40909", chain40909, ws40909),
        ("E11116", chain11116, ws11116),
    ):
        print(f"{label} chain_sizes={[size(eq[0]) for eq in chain]}")
        for i, witness in enumerate(witnesses[:3], 1):
            print(f"{label} stage{i} substitution={dict(witness.substitution)}")
            print(f"{label} stage{i} forced={render(chain[i][0])} = {render(chain[i][1])}")


if __name__ == "__main__":
    main()
