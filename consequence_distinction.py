"""Finite executable oracle for consequence-distinction duality.

The semantic core is intentionally small.  A representation is an
``EquivalenceRelation`` over a finite carrier.  A consequence is an extensional
callable on that carrier.  The declared consequence universe is supplied by the
caller; this module does not choose the constitution, verifier authority, or
resource boundary.

The two central maps are

    Phi(C) = intersection of the kernels of consequences in C
    Psi(E) = consequences in the declared universe that descend through E

and satisfy the antitone Galois law

    C subseteq Psi(E)  iff  E subseteq Phi(C).
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Iterable, TypeVar

from consequential_core import EquivalenceRelation


X = TypeVar("X")
Y = TypeVar("Y")
Consequence = Callable[[X], object]


class FailureKind(str, Enum):
    """Mutually exclusive diagnostic result under the declared invariants."""

    REPRESENTATION = "representation"
    CAPABILITY = "capability"
    SEARCH = "search"
    SOLVED = "solved"


def kernel(carrier: Iterable[X], consequence: Consequence[X]) -> EquivalenceRelation[X]:
    """Return the equality kernel induced by one consequence."""

    return EquivalenceRelation.from_observation(tuple(carrier), consequence)


def phi(
    carrier: Iterable[X], consequences: Iterable[Consequence[X]]
) -> EquivalenceRelation[X]:
    """Return the common kernel of a protected consequence family.

    The empty family induces the universal relation, as expected for an empty
    intersection of constraints.
    """

    carrier = tuple(carrier)
    consequences = tuple(consequences)
    pairs = frozenset(
        (left, right)
        for left in carrier
        for right in carrier
        if all(c(left) == c(right) for c in consequences)
    )
    return EquivalenceRelation(carrier=carrier, pairs=pairs)


def descends(
    representation: EquivalenceRelation[X], consequence: Consequence[X]
) -> bool:
    """Whether ``consequence`` is well-defined on the quotient by ``representation``."""

    return all(
        (not representation.same(left, right))
        or consequence(left) == consequence(right)
        for left in representation.carrier
        for right in representation.carrier
    )


def psi(
    representation: EquivalenceRelation[X],
    universe: Iterable[Consequence[X]],
) -> tuple[Consequence[X], ...]:
    """Return exactly the declared consequences that descend through ``representation``."""

    return tuple(c for c in universe if descends(representation, c))


def galois_holds(
    carrier: Iterable[X],
    consequences: Iterable[Consequence[X]],
    representation: EquivalenceRelation[X],
    universe: Iterable[Consequence[X]],
) -> bool:
    """Check ``C subseteq Psi(E) iff E subseteq Phi(C)`` in the finite oracle."""

    carrier = tuple(carrier)
    consequences = tuple(consequences)
    universe = tuple(universe)
    if any(c not in universe for c in consequences):
        raise ValueError("protected consequence lies outside declared universe")

    left = all(descends(representation, c) for c in consequences)
    right = representation.refines(phi(carrier, consequences))
    return left == right


def close_consequences(
    carrier: Iterable[X],
    consequences: Iterable[Consequence[X]],
    universe: Iterable[Consequence[X]],
) -> tuple[Consequence[X], ...]:
    """Consequential closure ``Psi(Phi(C))`` inside the declared universe."""

    carrier = tuple(carrier)
    consequences = tuple(consequences)
    universe = tuple(universe)
    return psi(phi(carrier, consequences), universe)


def close_representation(
    representation: EquivalenceRelation[X],
    universe: Iterable[Consequence[X]],
) -> EquivalenceRelation[X]:
    """Forget unsupported distinctions via ``Phi(Psi(E))``."""

    universe = tuple(universe)
    return phi(representation.carrier, psi(representation, universe))


def residual_witness(
    representation: EquivalenceRelation[X], consequence: Consequence[X]
) -> tuple[X, X] | None:
    """Return a pair witnessing failure of ``consequence`` to descend, if one exists."""

    for left in representation.carrier:
        for right in representation.carrier:
            if representation.same(left, right) and consequence(left) != consequence(right):
                return left, right
    return None


def minimal_repair(
    representation: EquivalenceRelation[X], consequence: Consequence[X]
) -> EquivalenceRelation[X]:
    """Return the coarsest refinement that makes one consequence descend.

    This is the finite executable form of ``E+ = E intersect ker(d)``.
    """

    consequence_kernel = kernel(representation.carrier, consequence)
    return EquivalenceRelation(
        carrier=representation.carrier,
        pairs=representation.pairs & consequence_kernel.pairs,
    )


def classify_failure(
    representation: EquivalenceRelation[X],
    consequence: Consequence[X],
    *,
    reachable: Iterable[Consequence[X]],
    found: bool,
) -> FailureKind:
    """Classify a desired consequence under the representation/capability split.

    ``reachable`` is the verifier-accepted bounded capability closure Gamma_B(L).
    The load-bearing invariant is ``reachable subseteq Psi(E)``: a consequence
    advertised as executable through the active representation must actually
    descend through it.

    Precedence then becomes exact:
      * not in Psi(E): representation failure;
      * in Psi(E) but not reachable: capability/language failure;
      * reachable but not found: search failure;
      * found: solved.
    """

    reachable = tuple(reachable)
    if any(not descends(representation, c) for c in reachable):
        raise ValueError(
            "reachable consequence does not descend through active representation"
        )

    if found:
        if consequence not in reachable:
            raise ValueError("found consequence must belong to the reachable closure")
        return FailureKind.SOLVED

    if not descends(representation, consequence):
        return FailureKind.REPRESENTATION
    if consequence not in reachable:
        return FailureKind.CAPABILITY
    return FailureKind.SEARCH
