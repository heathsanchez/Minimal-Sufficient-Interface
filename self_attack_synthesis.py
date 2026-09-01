"""Residual-driven self-attack synthesis for the minimum calculus.

Rather than hand-selecting the next audit cases, this module generates a finite
attack grammar, evaluates each candidate against the current refined calculus
and its one-distinction ablations, and selects a minimum separating attack set.

Scope: finite grammar-relative self-audit.  It does not claim unrestricted
adversarial invention.
"""

from dataclasses import dataclass, replace
from itertools import combinations
from typing import Dict, FrozenSet, Iterable, List, Tuple

from minimum_calculus_self_audit import AuditCase, CalculusVariant, Decision, V1


@dataclass(frozen=True)
class SelfAttack:
    name: str
    kind: str
    payload: Tuple[int, ...]
    cost: int


@dataclass(frozen=True)
class AttackSynthesisReport:
    candidates: int
    informative: int
    mutants: int
    selected: Tuple[SelfAttack, ...]
    covered_mutants: FrozenSet[str]


MUTANTS: Tuple[CalculusVariant, ...] = (
    replace(V1, name="mut_no_relative_fixed_point", relative_fixed_point=False),
    replace(V1, name="mut_no_coverage_guard", requires_coverage_for_escalation=False),
    replace(V1, name="mut_no_future_quotient", quotients_future_equivalent_realizers=False),
    replace(V1, name="mut_drop_provenance", preserves_provenance_outside_active_quotient=False),
    replace(V1, name="mut_raw_discrimination", lawful_interaction_objective=False),
)


def enumerate_attack_grammar() -> Tuple[SelfAttack, ...]:
    attacks: List[SelfAttack] = []

    # Controller attacks are generated from the finite state grammar rather than
    # supplied as named expected counterexamples.
    for residual in (0, 1):
        for live in range(0, 5):
            for complete in (0, 1):
                for future_classes in range(0, live + 1):
                    if live == 0 and future_classes != 0:
                        continue
                    attacks.append(
                        SelfAttack(
                            name=f"controller_r{residual}_l{live}_c{complete}_f{future_classes}",
                            kind="controller",
                            payload=(residual, live, complete, future_classes),
                            cost=1 + live + future_classes,
                        )
                    )

    # Meta-attacks probe distinctions that live outside the four-way decision
    # function but are part of the refined calculus contract.
    for new_consequence in (0, 1):
        attacks.append(SelfAttack(
            name=f"fixedpoint_new{new_consequence}",
            kind="fixedpoint",
            payload=(new_consequence,),
            cost=1 + new_consequence,
        ))

    for active in range(1, 5):
        for protected in range(0, active + 1):
            attacks.append(SelfAttack(
                name=f"provenance_a{active}_p{protected}",
                kind="provenance",
                payload=(active, protected),
                cost=1 + active,
            ))

    for raw_blocks in range(2, 7):
        for safe_blocks in range(1, raw_blocks):
            attacks.append(SelfAttack(
                name=f"interaction_raw{raw_blocks}_safe{safe_blocks}",
                kind="interaction",
                payload=(raw_blocks, safe_blocks),
                cost=1 + raw_blocks,
            ))

    return tuple(attacks)


def attack_outcome(variant: CalculusVariant, attack: SelfAttack):
    if attack.kind == "controller":
        residual, live, complete, future_classes = attack.payload
        case = AuditCase(
            attack.name,
            bool(residual),
            live,
            bool(complete),
            future_classes,
        )
        return variant.decide(case).value

    if attack.kind == "fixedpoint":
        (new_consequence,) = attack.payload
        if not new_consequence:
            return "FIXED"
        return "REOPEN" if variant.relative_fixed_point else "GLOBALLY_FIXED"

    if attack.kind == "provenance":
        active, protected = attack.payload
        compressed = min(active, protected)
        retained = active if variant.preserves_provenance_outside_active_quotient else compressed
        return (compressed, retained)

    if attack.kind == "interaction":
        raw_blocks, safe_blocks = attack.payload
        if variant.lawful_interaction_objective:
            return ("safe", safe_blocks)
        return ("raw", raw_blocks)

    raise ValueError(f"unknown attack kind: {attack.kind}")


def separated_mutants(attack: SelfAttack) -> FrozenSet[str]:
    baseline = attack_outcome(V1, attack)
    return frozenset(
        mutant.name for mutant in MUTANTS
        if attack_outcome(mutant, attack) != baseline
    )


def _dominance_reduce(attacks: Iterable[SelfAttack]) -> Tuple[SelfAttack, ...]:
    """Keep the cheapest canonical attack for each exact separator set."""
    best: Dict[FrozenSet[str], SelfAttack] = {}
    for attack in attacks:
        separated = separated_mutants(attack)
        if not separated:
            continue
        incumbent = best.get(separated)
        key = (attack.cost, attack.name)
        if incumbent is None or key < (incumbent.cost, incumbent.name):
            best[separated] = attack
    return tuple(sorted(best.values(), key=lambda a: (a.cost, a.name)))


def synthesize_minimum_attack_set() -> AttackSynthesisReport:
    candidates = enumerate_attack_grammar()
    informative = tuple(a for a in candidates if separated_mutants(a))
    reduced = _dominance_reduce(informative)
    target = frozenset(mutant.name for mutant in MUTANTS)

    best_selection = None
    # Dominance reduction leaves at most one candidate per separator mask, so
    # exhaustive minimum-cover search is tiny and gives an exact finite result.
    for width in range(1, len(target) + 1):
        feasible = []
        for subset in combinations(reduced, width):
            covered = frozenset().union(*(separated_mutants(a) for a in subset))
            if covered == target:
                feasible.append(subset)
        if feasible:
            best_selection = min(
                feasible,
                key=lambda subset: (
                    sum(a.cost for a in subset),
                    tuple(a.name for a in subset),
                ),
            )
            break

    if best_selection is None:
        raise AssertionError("attack grammar failed to separate all one-distinction mutants")

    covered = frozenset().union(*(separated_mutants(a) for a in best_selection))
    return AttackSynthesisReport(
        candidates=len(candidates),
        informative=len(informative),
        mutants=len(MUTANTS),
        selected=tuple(best_selection),
        covered_mutants=covered,
    )
