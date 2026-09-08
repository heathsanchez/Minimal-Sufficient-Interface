"""Bounded structural probe for interactions among automatically generated rules.

This is not a confluence proof.  It asks a narrower question: after recursive
promotion, do rule families create new non-root unification sites that a
single-lineage representation must record?  The answer is measured for the
first three generations of E40909 and E11116.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class V:
    name: str


@dataclass(frozen=True)
class A:
    left: "T"
    right: "T"


T = V | A
Rule = tuple[T, T]
Path = tuple[int, ...]


def subs(t: T, path: Path = ()) -> Iterator[tuple[Path, T]]:
    yield path, t
    if isinstance(t, A):
        yield from subs(t.left, path + (0,))
        yield from subs(t.right, path + (1,))


def apply(t: T, s: dict[str, T]) -> T:
    if isinstance(t, V):
        return apply(s[t.name], s) if t.name in s else t
    return A(apply(t.left, s), apply(t.right, s))


def occurs(v: str, t: T, s: dict[str, T]) -> bool:
    t = apply(t, s)
    if isinstance(t, V):
        return t.name == v
    return occurs(v, t.left, s) or occurs(v, t.right, s)


def unify(a: T, b: T) -> dict[str, T] | None:
    s: dict[str, T] = {}
    pending = [(a, b)]
    while pending:
        x, y = pending.pop()
        x, y = apply(x, s), apply(y, s)
        if x == y:
            continue
        if isinstance(x, V):
            if occurs(x.name, y, s):
                return None
            s[x.name] = y
            continue
        if isinstance(y, V):
            if occurs(y.name, x, s):
                return None
            s[y.name] = x
            continue
        if isinstance(x, A) and isinstance(y, A):
            pending.extend(((x.left, y.left), (x.right, y.right)))
            continue
        return None
    return s


def rename(t: T, prefix: str) -> T:
    if isinstance(t, V):
        return V(prefix + t.name)
    return A(rename(t.left, prefix), rename(t.right, prefix))


def e40909_seed() -> Rule:
    x, y, z = V("x"), V("y"), V("z")
    return A(A(A(A(A(y, x), y), y), z), y), x


def e11116_seed() -> Rule:
    x, y, z = V("x"), V("y"), V("z")
    return A(y, A(A(x, A(z, x)), A(y, y))), x


def promote40909(rule: Rule, fresh: V) -> Rule:
    lhs, q = rule
    assert isinstance(lhs, A)
    branch_left, branch_right = lhs.left, lhs.right
    return A(A(A(A(q, branch_left), branch_left), fresh), branch_left), branch_right


def promote11116(rule: Rule, fresh: V) -> Rule:
    lhs, q = rule
    assert isinstance(lhs, A)
    branch_left, branch_right = lhs.left, lhs.right
    return A(fresh, A(A(branch_right, q), A(fresh, fresh))), branch_right


def lineage(seed: Rule, promote, depth: int) -> list[Rule]:
    out = [seed]
    for n in range(1, depth):
        out.append(promote(out[-1], V(f"fresh{n}")))
    return out


def nonroot_overlap_count(left_rule: Rule, right_rule: Rule, i: int, j: int) -> int:
    left = rename(left_rule[0], f"L{i}_")
    right = rename(right_rule[0], f"R{j}_")
    count = 0
    for path, term in subs(left):
        if not path or isinstance(term, V):
            continue
        if unify(term, right) is not None:
            count += 1
    return count


def matrix(rules: list[Rule]) -> list[list[int]]:
    return [[nonroot_overlap_count(a, b, i, j) for j, b in enumerate(rules)] for i, a in enumerate(rules)]


def total(m: list[list[int]]) -> int:
    return sum(map(sum, m))


if __name__ == "__main__":
    r40909 = lineage(e40909_seed(), promote40909, 3)
    r11116 = lineage(e11116_seed(), promote11116, 3)
    m40909, m11116 = matrix(r40909), matrix(r11116)
    print("E40909 non-root overlap matrix:", m40909, "total=", total(m40909))
    print("E11116 non-root overlap matrix:", m11116, "total=", total(m11116))
    assert total(m40909) > total(m11116)
