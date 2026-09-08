"""Compile critical-pair residuals from recursively promoted Austin rules.

This is the next developmental boundary after branch promotion.  It does not
assume a completion rule.  For a bounded prefix of generated rewrite rules it:

* standardises two rules apart;
* finds every non-variable overlap of one lhs inside another lhs;
* computes the two reducts of the resulting critical peak;
* normalises both sides with the currently known rule prefix;
* records only peaks that remain unequal.

Thus an unresolved peak is a concrete residual for the *completion grammar*.
The experiment is intentionally bounded; any stable pattern found here is a
candidate constructor and must later be proved generically in Lean.
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
Subst = dict[str, T]


def walk(t: T, path: Path = ()) -> Iterator[tuple[Path, T]]:
    yield path, t
    if isinstance(t, A):
        yield from walk(t.left, path + (0,))
        yield from walk(t.right, path + (1,))


def replace_at(t: T, path: Path, r: T) -> T:
    if not path:
        return r
    assert isinstance(t, A)
    h, *rest = path
    rest = tuple(rest)
    if h == 0:
        return A(replace_at(t.left, rest, r), t.right)
    return A(t.left, replace_at(t.right, rest, r))


def subst(t: T, s: Subst) -> T:
    if isinstance(t, V):
        if t.name not in s:
            return t
        return subst(s[t.name], s)
    return A(subst(t.left, s), subst(t.right, s))


def occurs(x: str, t: T, s: Subst) -> bool:
    t = subst(t, s)
    if isinstance(t, V):
        return t.name == x
    return occurs(x, t.left, s) or occurs(x, t.right, s)


def unify(a: T, b: T) -> Subst | None:
    s: Subst = {}
    pending = [(a, b)]
    while pending:
        x, y = pending.pop()
        x, y = subst(x, s), subst(y, s)
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
    return {k: subst(v, s) for k, v in s.items()}


def rename(t: T, prefix: str) -> T:
    if isinstance(t, V):
        return V(prefix + t.name)
    return A(rename(t.left, prefix), rename(t.right, prefix))


def rename_rule(r: Rule, prefix: str) -> Rule:
    return rename(r[0], prefix), rename(r[1], prefix)


def match(pattern: T, target: T, env: Subst | None = None) -> Subst | None:
    """One-way first-order pattern match for rewriting."""
    env = {} if env is None else dict(env)
    if isinstance(pattern, V):
        old = env.get(pattern.name)
        if old is None:
            env[pattern.name] = target
            return env
        return env if old == target else None
    if not isinstance(target, A):
        return None
    env = match(pattern.left, target.left, env)
    if env is None:
        return None
    return match(pattern.right, target.right, env)


def rewrite_once(t: T, rules: list[Rule]) -> tuple[T, bool]:
    """Deterministic outermost-leftmost rewrite."""
    for lhs, rhs in rules:
        m = match(lhs, t)
        if m is not None:
            return subst(rhs, m), True
    if isinstance(t, A):
        l, changed = rewrite_once(t.left, rules)
        if changed:
            return A(l, t.right), True
        r, changed = rewrite_once(t.right, rules)
        if changed:
            return A(t.left, r), True
    return t, False


def normalise(t: T, rules: list[Rule], budget: int = 500) -> tuple[T, bool]:
    for _ in range(budget):
        t2, changed = rewrite_once(t, rules)
        if not changed:
            return t, True
        t = t2
    return t, False


def e40909_seed() -> Rule:
    x, y, z = V("x"), V("y"), V("z")
    return A(A(A(A(A(y, x), y), y), z), y), x


def e11116_seed() -> Rule:
    x, y, z = V("x"), V("y"), V("z")
    return A(y, A(A(x, A(z, x)), A(y, y))), x


def promote40909(rule: Rule, fresh: V) -> Rule:
    lhs, q = rule
    assert isinstance(lhs, A)
    A0, p = lhs.left, lhs.right
    return A(A(A(A(q, A0), A0), fresh), A0), p


def promote11116(rule: Rule, fresh: V) -> Rule:
    lhs, q = rule
    assert isinstance(lhs, A)
    A0, p = lhs.left, lhs.right
    return A(fresh, A(A(p, q), A(fresh, fresh))), p


def lineage(seed: Rule, promote, depth: int) -> list[Rule]:
    rs = [seed]
    for n in range(1, depth):
        rs.append(promote(rs[-1], V(f"fresh{n}")))
    return rs


@dataclass(frozen=True)
class Residual:
    outer_rank: int
    inner_rank: int
    path: Path
    left_nf: T
    right_nf: T
    normalised: bool


def residuals(rules: list[Rule]) -> list[Residual]:
    out: list[Residual] = []
    for i, outer0 in enumerate(rules):
        for j, inner0 in enumerate(rules):
            outer = rename_rule(outer0, f"O{i}_")
            inner = rename_rule(inner0, f"I{j}_")
            olhs, orhs = outer
            ilhs, irhs = inner
            for path, site in walk(olhs):
                if not path or isinstance(site, V):
                    continue
                u = unify(site, ilhs)
                if u is None:
                    continue
                peak_root = subst(orhs, u)
                peak_inner = replace_at(subst(olhs, u), path, subst(irhs, u))
                # Rewrite with fresh copies of the current finite rule prefix so
                # variable namespaces in the critical-pair calculation do not
                # accidentally become rigid rule names.
                active = [rename_rule(r, f"N{k}_") for k, r in enumerate(rules)]
                left_nf, ok_l = normalise(peak_root, active)
                right_nf, ok_r = normalise(peak_inner, active)
                if left_nf != right_nf:
                    out.append(Residual(i, j, path, left_nf, right_nf, ok_l and ok_r))
    return out


def size(t: T) -> int:
    if isinstance(t, V):
        return 1
    return size(t.left) + size(t.right) + 1


def shape(t: T) -> str:
    if isinstance(t, V):
        return "v"
    return f"({shape(t.left)}*{shape(t.right)})"


def summarise(name: str, rules: list[Rule]) -> None:
    rs = residuals(rules)
    pairs: dict[tuple[int, int], int] = {}
    signatures: dict[tuple[int, int, str, str], int] = {}
    for r in rs:
        pairs[(r.outer_rank, r.inner_rank)] = pairs.get((r.outer_rank, r.inner_rank), 0) + 1
        sig = (size(r.left_nf), size(r.right_nf), shape(r.left_nf), shape(r.right_nf))
        signatures[sig] = signatures.get(sig, 0) + 1
    print(name, "rules=", len(rules), "unresolved=", len(rs), "rank-pairs=", sorted(pairs.items()))
    print(name, "residual-shape-classes=", len(signatures))
    for sig, count in sorted(signatures.items(), key=lambda kv: (-kv[1], kv[0]))[:10]:
        print(" ", count, "x sizes", sig[:2], "shapes", sig[2:])


if __name__ == "__main__":
    for depth in (1, 2, 3, 4):
        summarise(f"E40909/d{depth}", lineage(e40909_seed(), promote40909, depth))
        summarise(f"E11116/d{depth}", lineage(e11116_seed(), promote11116, depth))
