from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Hashable, Iterable, Sequence, TypeVar

X = TypeVar("X", bound=Hashable)
C = TypeVar("C", bound=Hashable)
O = TypeVar("O", bound=Hashable)


@dataclass(frozen=True)
class Interface:
    situations: tuple[X, ...]
    continuations: tuple[C, ...]
    outcome: Callable[[X, C], O]

    def signature(self, x: X, basis: Iterable[C]) -> tuple[O, ...]:
        b = tuple(basis)
        return tuple(self.outcome(x, c) for c in b)

    def equivalent(self, x: X, y: X, basis: Iterable[C]) -> bool:
        return self.signature(x, basis) == self.signature(y, basis)

    def partition(self, basis: Iterable[C]) -> tuple[tuple[X, ...], ...]:
        b = tuple(basis)
        groups: dict[tuple[O, ...], list[X]] = {}
        for x in self.situations:
            groups.setdefault(self.signature(x, b), []).append(x)
        return tuple(sorted((tuple(v) for v in groups.values()), key=repr))

    def relation(self, basis: Iterable[C]) -> frozenset[tuple[X, X]]:
        b = tuple(basis)
        return frozenset(
            (x, y)
            for x in self.situations
            for y in self.situations
            if self.equivalent(x, y, b)
        )

    def separates(self, c: C, x: X, y: X) -> bool:
        return self.outcome(x, c) != self.outcome(y, c)

    def residual_witness(
        self, basis: Iterable[C], target: Iterable[C] | None = None
    ) -> tuple[X, X, C] | None:
        b = tuple(basis)
        bset = set(b)
        full = tuple(self.continuations if target is None else target)
        for x in self.situations:
            for y in self.situations:
                if not self.equivalent(x, y, b):
                    continue
                for c in full:
                    if c not in bset and self.separates(c, x, y):
                        return x, y, c
        return None

    def sufficient(self, basis: Iterable[C], target: Iterable[C] | None = None) -> bool:
        full = self.continuations if target is None else tuple(target)
        return self.relation(basis) == self.relation(full)

    def lawful_repair(
        self, basis: Iterable[C], target: Iterable[C] | None = None
    ) -> tuple[C, ...]:
        b = list(dict.fromkeys(basis))
        while True:
            witness = self.residual_witness(b, target)
            if witness is None:
                return tuple(b)
            b.append(witness[2])

    def minimum_basis(self, target: Iterable[C] | None = None) -> tuple[C, ...]:
        full = tuple(self.continuations if target is None else target)
        target_relation = self.relation(full)
        for r in range(len(full) + 1):
            for subset in combinations(full, r):
                if self.relation(subset) == target_relation:
                    return subset
        raise AssertionError("full continuation family must be sufficient for itself")

    def preserves_equivalence(self, f: Callable[[X], X], basis: Iterable[C]) -> bool:
        b = tuple(basis)
        for x in self.situations:
            for y in self.situations:
                if self.equivalent(x, y, b) and not self.equivalent(f(x), f(y), b):
                    return False
        return True

    def quotient_map(
        self, f: Callable[[X], X], basis: Iterable[C]
    ) -> dict[tuple[X, ...], tuple[X, ...]]:
        b = tuple(basis)
        if not self.preserves_equivalence(f, b):
            raise ValueError("transformation is not congruent with the current interface")
        classes = self.partition(b)
        class_of = {x: cls for cls in classes for x in cls}
        return {cls: class_of[f(cls[0])] for cls in classes}


def compose(f: Callable[[X], X], g: Callable[[X], X]) -> Callable[[X], X]:
    return lambda x: f(g(x))


def closure(
    situations: Sequence[X],
    generators: Sequence[Callable[[X], X]],
    starts: Iterable[X],
) -> frozenset[X]:
    seen = set(starts)
    frontier = list(starts)
    universe = set(situations)
    while frontier:
        x = frontier.pop()
        for f in generators:
            y = f(x)
            if y not in universe:
                raise ValueError("generator leaves the declared situation space")
            if y not in seen:
                seen.add(y)
                frontier.append(y)
    return frozenset(seen)
