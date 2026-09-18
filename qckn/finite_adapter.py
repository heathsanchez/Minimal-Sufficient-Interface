"""Finite-set adapter onto the frozen QCK v1 constitutional vocabulary.

This module does not redefine QCK semantics.  It maps the existing finite MSI
interface into the same two-way operation assessment exposed formally by
`QCK.assessOperation`:

- certified substitution when the current equivalence is stable under an action;
- new-context defect with an explicit separating witness otherwise.

The Lean implementation remains authoritative for the finite-linear theorem
surface.  This adapter is for finite/discrete downstream experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Hashable, Iterable, TypeAlias, TypeVar

from consequential_core import EquivalenceRelation, PairResidual
from msi import Interface

X = TypeVar("X", bound=Hashable)
C = TypeVar("C", bound=Hashable)
O = TypeVar("O", bound=Hashable)


@dataclass(frozen=True)
class CertifiedSubstitution(Generic[X, C]):
    """Finite-set witness that an action descends through the current quotient."""

    basis: tuple[C, ...]
    classes: tuple[tuple[X, ...], ...]


@dataclass(frozen=True)
class NewContextDefect(Generic[X, C, O]):
    """Erased source distinction exposed after applying a proposed action."""

    basis: tuple[C, ...]
    left: X
    right: X
    image_left: X
    image_right: X
    consequence_left: tuple[O, ...]
    consequence_right: tuple[O, ...]

    def __post_init__(self) -> None:
        if self.consequence_left == self.consequence_right:
            raise ValueError("defect witness does not expose a protected consequence")


OperationAssessment: TypeAlias = (
    CertifiedSubstitution[X, C] | NewContextDefect[X, C, O]
)


def representation_from_interface(
    interface: Interface[X, C, O], basis: Iterable[C]
) -> EquivalenceRelation:
    """Materialize the current finite quotient relation for legacy consumers."""

    b = tuple(basis)
    return EquivalenceRelation(
        tuple(interface.situations),
        frozenset(interface.relation(b)),
    )


def assess_operation(
    interface: Interface[X, C, O],
    basis: Iterable[C],
    action: Callable[[X], X],
) -> OperationAssessment:
    """Classify a proposed operation using the frozen QCK v1 contract.

    This is the finite-set analogue of kernel stability.  If the operation is
    not quotient-admissible, return the first deterministic separating witness.
    """

    b = tuple(basis)
    for left in interface.situations:
        for right in interface.situations:
            if not interface.equivalent(left, right, b):
                continue
            image_left = action(left)
            image_right = action(right)
            if interface.equivalent(image_left, image_right, b):
                continue
            return NewContextDefect(
                basis=b,
                left=left,
                right=right,
                image_left=image_left,
                image_right=image_right,
                consequence_left=interface.signature(image_left, b),
                consequence_right=interface.signature(image_right, b),
            )

    return CertifiedSubstitution(
        basis=b,
        classes=interface.partition(b),
    )


def defect_to_pair_residual(
    interface: Interface[X, C, O],
    defect: NewContextDefect[X, C, O],
) -> PairResidual:
    """Bridge a QCK-style defect into the legacy consequential residual ledger."""

    representation = representation_from_interface(interface, defect.basis)
    return PairResidual(
        left=defect.left,
        right=defect.right,
        representation=representation,
        consequence_left=defect.consequence_left,
        consequence_right=defect.consequence_right,
    )
