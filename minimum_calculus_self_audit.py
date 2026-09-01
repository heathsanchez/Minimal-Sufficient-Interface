"""Executable self-audit for the Minimum Consequential Calculus.

The calculus is treated as its own hypothesis space.  Competing controller
formulations are separated only when an adversarial consequence demonstrates
that the distinction matters.  This is a finite executable specification, not
a claim of universal minimality.
"""

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Iterable, Tuple


class Decision(str, Enum):
    FIXED = "FIXED"
    COMPILE = "COMPILE"
    INTERACT = "INTERACT"
    ESCALATE = "ESCALATE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AuditCase:
    name: str
    residual: bool
    live_realizations: int
    coverage_complete: bool
    future_classes: int


@dataclass(frozen=True)
class CalculusVariant:
    name: str
    relative_fixed_point: bool
    requires_coverage_for_escalation: bool
    quotients_future_equivalent_realizers: bool
    preserves_provenance_outside_active_quotient: bool
    lawful_interaction_objective: bool

    def decide(self, case: AuditCase) -> Decision:
        if not case.residual:
            return Decision.FIXED

        live = case.future_classes if self.quotients_future_equivalent_realizers else case.live_realizations
        if live == 0:
            if self.requires_coverage_for_escalation and not case.coverage_complete:
                return Decision.UNKNOWN
            return Decision.ESCALATE
        if live == 1:
            return Decision.COMPILE
        return Decision.INTERACT


# V0 is the pre-self-audit four-way controller.
V0 = CalculusVariant(
    "V0_four_way",
    relative_fixed_point=False,
    requires_coverage_for_escalation=False,
    quotients_future_equivalent_realizers=False,
    preserves_provenance_outside_active_quotient=False,
    lawful_interaction_objective=False,
)

# V1 is the candidate self-refinement forced by the attacks below.
V1 = CalculusVariant(
    "V1_self_refined",
    relative_fixed_point=True,
    requires_coverage_for_escalation=True,
    quotients_future_equivalent_realizers=True,
    preserves_provenance_outside_active_quotient=True,
    lawful_interaction_objective=True,
)


def observational_signature(variant: CalculusVariant, cases: Iterable[AuditCase]) -> Tuple[Decision, ...]:
    return tuple(variant.decide(case) for case in cases)


def equivalent_under_attacks(a: CalculusVariant, b: CalculusVariant, cases: Iterable[AuditCase]) -> bool:
    return observational_signature(a, cases) == observational_signature(b, cases)


def future_equivalence_quotient(classes: Iterable[FrozenSet[str]]) -> Tuple[FrozenSet[str], ...]:
    """Canonical finite quotient of realizers already grouped by future behaviour."""
    return tuple(sorted(set(classes), key=lambda block: tuple(sorted(block))))


def best_lawful_interaction(interactions):
    """Choose only among lawful interactions, then maximize discrimination/cost lexicographically.

    The objective is deliberately not a universal scalar utility.  It preserves
    the constitutional admissibility boundary before comparing information gain.
    """
    lawful = [item for item in interactions if item["lawful"]]
    if not lawful:
        return None
    return max(lawful, key=lambda item: (item["blocks"], -item["worst_case"], -item["cost"], item["name"]))


def active_state_after_quotient(active_distinctions, protected_distinctions):
    """Forget only from the active interface; provenance is intentionally separate."""
    return frozenset(active_distinctions) & frozenset(protected_distinctions)
