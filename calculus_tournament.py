"""Exact tournament over all 2^5 variants of the refined minimum calculus.

This extends the one-distinction self-audit into a finite full-factorial
experiment.  Every Boolean combination of the five current controller
refinements is treated as a candidate calculus.  The existing generated attack
grammar acts as the judge.

The experiment computes:
  * the observational quotient of all 32 candidate calculi under all 91 attacks;
  * an exact cardinality-minimum attack suite preserving that quotient;
  * exact ablations of every selected attack;
  * necessity witnesses for each refinement relative to the fully refined V1.

Scope: exhaustive only over this supplied five-bit calculus family and supplied
finite attack grammar.  It is not a claim of universal minimality.
"""

from dataclasses import dataclass
from itertools import combinations, product
from typing import Dict, FrozenSet, Iterable, Mapping, Sequence, Tuple

from minimum_calculus_self_audit import CalculusVariant
from self_attack_synthesis import SelfAttack, attack_outcome, enumerate_attack_grammar


REFINEMENTS: Tuple[str, ...] = (
    "relative_fixed_point",
    "requires_coverage_for_escalation",
    "quotients_future_equivalent_realizers",
    "preserves_provenance_outside_active_quotient",
    "lawful_interaction_objective",
)


@dataclass(frozen=True)
class TournamentReport:
    candidates: int
    attacks: int
    quotient_classes: int
    pairwise_distinctions: int
    pairwise_possible: int
    reduced_attack_masks: int
    selected: Tuple[SelfAttack, ...]
    selected_quotient_classes: int
    ablation_quotient_classes: Mapping[str, int]
    refined_unique: bool
    necessity_witnesses: Mapping[str, Tuple[str, ...]]


def enumerate_calculi() -> Tuple[CalculusVariant, ...]:
    variants = []
    for bits in product((False, True), repeat=len(REFINEMENTS)):
        kwargs = dict(zip(REFINEMENTS, bits))
        variants.append(
            CalculusVariant(
                name="C_" + "".join("1" if bit else "0" for bit in bits),
                **kwargs,
            )
        )
    return tuple(variants)


def observational_signature(
    variant: CalculusVariant,
    attacks: Iterable[SelfAttack],
) -> Tuple[object, ...]:
    return tuple(attack_outcome(variant, attack) for attack in attacks)


def observational_quotient(
    variants: Iterable[CalculusVariant],
    attacks: Iterable[SelfAttack],
) -> Tuple[Tuple[str, ...], ...]:
    attacks = tuple(attacks)
    classes: Dict[Tuple[object, ...], list[str]] = {}
    for variant in variants:
        classes.setdefault(observational_signature(variant, attacks), []).append(variant.name)
    return tuple(sorted((tuple(sorted(block)) for block in classes.values())))


def _separated_pairs(
    attack: SelfAttack,
    variants: Sequence[CalculusVariant],
) -> FrozenSet[Tuple[int, int]]:
    outcomes = tuple(attack_outcome(variant, attack) for variant in variants)
    return frozenset(
        (i, j)
        for i in range(len(variants))
        for j in range(i + 1, len(variants))
        if outcomes[i] != outcomes[j]
    )


def _reduced_attacks(
    variants: Sequence[CalculusVariant],
    attacks: Iterable[SelfAttack],
) -> Tuple[SelfAttack, ...]:
    """Keep the cheapest canonical attack for each exact pair-separation mask."""
    best: Dict[FrozenSet[Tuple[int, int]], SelfAttack] = {}
    for attack in attacks:
        mask = _separated_pairs(attack, variants)
        if not mask:
            continue
        incumbent = best.get(mask)
        if incumbent is None or (attack.cost, attack.name) < (incumbent.cost, incumbent.name):
            best[mask] = attack
    return tuple(sorted(best.values(), key=lambda a: (a.cost, a.name)))


def synthesize_minimum_quotient_preserving_suite(
    variants: Sequence[CalculusVariant],
    attacks: Sequence[SelfAttack],
) -> Tuple[Tuple[SelfAttack, ...], FrozenSet[Tuple[int, int]], int]:
    masks = tuple(_separated_pairs(attack, variants) for attack in attacks)
    target = frozenset().union(*masks)
    reduced = _reduced_attacks(variants, attacks)
    reduced_masks = {attack.name: _separated_pairs(attack, variants) for attack in reduced}

    # Five independent Boolean refinements imply an upper bound of five
    # separators for this supplied family.  Iterative deepening proves exact
    # minimum cardinality rather than relying on greedy cover.
    for width in range(1, len(REFINEMENTS) + 1):
        feasible = []
        for subset in combinations(reduced, width):
            covered = frozenset().union(*(reduced_masks[attack.name] for attack in subset))
            if covered == target:
                feasible.append(subset)
        if feasible:
            return (
                min(
                    feasible,
                    key=lambda subset: (
                        sum(attack.cost for attack in subset),
                        tuple(attack.name for attack in subset),
                    ),
                ),
                target,
                len(reduced),
            )

    raise AssertionError("attack grammar did not admit a quotient-preserving suite")


def run_tournament() -> TournamentReport:
    variants = enumerate_calculi()
    attacks = enumerate_attack_grammar()
    full_quotient = observational_quotient(variants, attacks)
    selected, distinguished_pairs, reduced_count = synthesize_minimum_quotient_preserving_suite(
        variants, attacks
    )
    selected_quotient = observational_quotient(variants, selected)

    ablations = {
        attack.name: len(observational_quotient(variants, tuple(a for a in selected if a != attack)))
        for attack in selected
    }

    refined = next(variant for variant in variants if variant.name == "C_11111")
    refined_signature = observational_signature(refined, selected)
    refined_unique = sum(
        observational_signature(variant, selected) == refined_signature for variant in variants
    ) == 1

    necessity = {}
    for index, refinement in enumerate(REFINEMENTS):
        mutant_name = "C_" + "".join("0" if i == index else "1" for i in range(len(REFINEMENTS)))
        mutant = next(variant for variant in variants if variant.name == mutant_name)
        necessity[refinement] = tuple(
            attack.name
            for attack in attacks
            if attack_outcome(refined, attack) != attack_outcome(mutant, attack)
        )

    possible_pairs = len(variants) * (len(variants) - 1) // 2
    return TournamentReport(
        candidates=len(variants),
        attacks=len(attacks),
        quotient_classes=len(full_quotient),
        pairwise_distinctions=len(distinguished_pairs),
        pairwise_possible=possible_pairs,
        reduced_attack_masks=reduced_count,
        selected=selected,
        selected_quotient_classes=len(selected_quotient),
        ablation_quotient_classes=ablations,
        refined_unique=refined_unique,
        necessity_witnesses=necessity,
    )


if __name__ == "__main__":
    report = run_tournament()
    print(f"candidates={report.candidates}")
    print(f"attacks={report.attacks}")
    print(f"quotient_classes={report.quotient_classes}")
    print(f"pairwise_distinctions={report.pairwise_distinctions}/{report.pairwise_possible}")
    print(f"reduced_attack_masks={report.reduced_attack_masks}")
    print("selected=" + ",".join(attack.name for attack in report.selected))
    print(f"selected_quotient_classes={report.selected_quotient_classes}")
    for name, classes in report.ablation_quotient_classes.items():
        print(f"ablate[{name}]={classes}")
    print(f"refined_unique={report.refined_unique}")
    for refinement, witnesses in report.necessity_witnesses.items():
        print(f"necessity[{refinement}]={len(witnesses)}:{witnesses[0] if witnesses else 'NONE'}")
