"""Minimum-developmental-action policy over typed QCKN outcomes.

QCK decides what the evidence means.  MDA decides what to try next under an
explicit prospective cost model.  The admissible action family is typed; the
actual choice is cost-sensitive and therefore stays outside QCK semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import inf
from typing import Callable, Hashable, TypeAlias

from .finite_adapter import CertifiedSubstitution, NewContextDefect
from .outcomes import (
    CertificateInvalid,
    ImplementationMismatch,
    OutOfScope,
    RecoveryUnavailable,
    ReserveRequired,
    Unknown,
)


class Intervention(str, Enum):
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    EXPAND = "EXPAND"
    REVOKE = "REVOKE"
    CONSTRUCT = "CONSTRUCT"
    VERIFY = "VERIFY"
    RESTRUCTURE = "RESTRUCTURE"
    COMPILE = "COMPILE"


TypedOutcome: TypeAlias = (
    CertifiedSubstitution
    | NewContextDefect
    | ReserveRequired
    | RecoveryUnavailable
    | ImplementationMismatch
    | CertificateInvalid
    | OutOfScope
    | Unknown
)


@dataclass(frozen=True)
class InterventionPlan:
    primary: Intervention
    admissible: tuple[Intervention, ...]
    prospective_cost: float


def admissible_interventions(outcome: TypedOutcome) -> tuple[Intervention, ...]:
    """Return the action family licensed by the typed outcome.

    This table is developmental policy, not QCK semantics.  In particular a
    new-context defect licenses several possible repairs; prospective cost
    chooses among them.
    """

    if isinstance(outcome, CertifiedSubstitution):
        return (Intervention.COMPILE,)
    if isinstance(outcome, NewContextDefect):
        return (
            Intervention.SPLIT,
            Intervention.EXPAND,
            Intervention.RESTRUCTURE,
            Intervention.CONSTRUCT,
            Intervention.VERIFY,
        )
    if isinstance(outcome, ReserveRequired):
        return (Intervention.EXPAND, Intervention.RESTRUCTURE)
    if isinstance(outcome, RecoveryUnavailable):
        return (
            Intervention.CONSTRUCT,
            Intervention.RESTRUCTURE,
            Intervention.EXPAND,
        )
    if isinstance(outcome, ImplementationMismatch):
        return (
            Intervention.RESTRUCTURE,
            Intervention.VERIFY,
            Intervention.REVOKE,
        )
    if isinstance(outcome, CertificateInvalid):
        return (Intervention.REVOKE, Intervention.VERIFY)
    if isinstance(outcome, OutOfScope):
        return (Intervention.EXPAND, Intervention.CONSTRUCT)
    if isinstance(outcome, Unknown):
        return (Intervention.VERIFY, Intervention.CONSTRUCT)
    raise TypeError(type(outcome))


def choose_intervention(
    outcome: TypedOutcome,
    cost: Callable[[Intervention], float],
) -> InterventionPlan:
    """Choose the minimum-cost licensed intervention, deterministically."""

    options = admissible_interventions(outcome)
    if not options:
        raise ValueError("typed outcome has no licensed intervention")

    scored = []
    for index, intervention in enumerate(options):
        value = float(cost(intervention))
        if value < 0:
            raise ValueError("prospective intervention cost must be nonnegative")
        scored.append((value, index, intervention))

    value, _index, primary = min(scored)
    if value == inf:
        raise ValueError("all licensed interventions have infinite cost")
    return InterventionPlan(primary, options, value)
