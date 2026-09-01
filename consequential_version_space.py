"""Shared residual-relative representation version-space operations.

This module is part of the consequential core subsystem. Tests and domains may
supply finite dynamics, but they do not reimplement refinement enumeration,
minimality, or discriminating-experiment extraction.
"""

from __future__ import annotations

from typing import Callable, Hashable, Iterable, Tuple

from consequential_core import DevelopmentState, EquivalenceRelation, PairResidual

State = Hashable
Dynamics = Tuple[Callable[[State], State], ...]


def _partitions(xs: Tuple[State, ...]):
    if not xs:
        yield ()
        return
    first, rest = xs[0], xs[1:]
    for p in _partitions(rest):
        yield ((first,),) + p
        for i in range(len(p)):
            q = [tuple(block) for block in p]
            q[i] = tuple(sorted(q[i] + (first,), key=repr))
            yield tuple(q)


def _lawful_under(rel: EquivalenceRelation, dynamics: Dynamics) -> bool:
    xs = rel.carrier
    return all(
        (not rel.same(x, y)) or rel.same(g(x), g(y))
        for g in dynamics
        for x in xs
        for y in xs
    )


def coarsest_representation_repairs(
    state: DevelopmentState,
    residual: PairResidual,
    dynamics: Dynamics,
) -> Tuple[EquivalenceRelation, ...]:
    """Return all coarsest lawful strict refinements resolving one pair residual."""
    if state.active_representation != residual.representation:
        raise ValueError("residual does not belong to active representation")

    old = residual.representation
    candidates = []
    for raw in _partitions(state.carrier):
        rel = EquivalenceRelation.from_partition(state.carrier, raw)
        if (
            rel.refines(old)
            and not rel.same(residual.left, residual.right)
            and _lawful_under(rel, dynamics)
        ):
            candidates.append(rel)

    if not candidates:
        return ()

    # Coarsest refinement = maximum number of retained ordered equivalence pairs.
    max_pairs = max(len(r.pairs) for r in candidates)
    minima = {r for r in candidates if len(r.pairs) == max_pairs}
    return tuple(sorted(minima, key=lambda r: repr(sorted(r.pairs, key=repr))))


def discriminating_pairs(
    repairs: Tuple[EquivalenceRelation, ...],
) -> Tuple[Tuple[State, State], ...]:
    """Pairs on which at least two live representation repairs disagree."""
    if not repairs:
        return ()
    carrier = repairs[0].carrier
    if any(r.carrier != carrier for r in repairs):
        raise ValueError("version-space carriers differ")

    out = set()
    for i in range(len(repairs)):
        for j in range(i + 1, len(repairs)):
            a, b = repairs[i], repairs[j]
            for x in carrier:
                for y in carrier:
                    if repr(x) < repr(y) and a.same(x, y) != b.same(x, y):
                        out.add((x, y))
    return tuple(sorted(out, key=repr))


def update_version_space_from_pair_answer(
    repairs: Tuple[EquivalenceRelation, ...],
    pair: Tuple[State, State],
    *,
    observed_same: bool,
) -> Tuple[EquivalenceRelation, ...]:
    x, y = pair
    return tuple(r for r in repairs if r.same(x, y) == observed_same)
