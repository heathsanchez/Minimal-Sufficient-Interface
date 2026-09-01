"""Generic consequential interaction over synthesized realization version spaces.

A residual can force an abstract quotient without uniquely fixing how it should
be realized.  This module treats the remaining lawful realizers as a live
version space.  Admissible future queries are scored by how strongly their
*operational cost* partitions that version space under a declared constructor
grammar.  A verifier outcome then contracts the version space.

The selector never uses domain-specific semantic names or a privileged target
realizer.  It only sees extensional candidate coordinates, declared queries,
and a grammar/cost model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable, Mapping, Optional, Sequence, Tuple

from realizer_synthesis import Expression, SynthesisGrammar, enumerate_expressions

Observation = Callable[[Hashable], Hashable]


@dataclass(frozen=True)
class Interaction:
    name: str
    query: Observation


@dataclass(frozen=True)
class InteractionAssessment:
    interaction: Interaction
    outcomes: Tuple[Optional[int], ...]
    blocks: Tuple[Tuple[int, ...], ...]
    score: Tuple[int, int, int]


@dataclass(frozen=True)
class InteractionDecision:
    chosen: InteractionAssessment
    contracted_indices: Tuple[int, ...]
    observed_outcome: Optional[int]


def _query_values(carrier: Tuple[Hashable, ...], query: Observation) -> Tuple[Hashable, ...]:
    return tuple(query(x) for x in carrier)


def minimum_query_cost(
    carrier: Tuple[Hashable, ...],
    basis: Mapping[str, Observation],
    constructors: SynthesisGrammar,
    query: Observation,
) -> Optional[int]:
    """Minimum expression size that realizes query from ``basis``.

    ``None`` means the query is unreachable within the frozen grammar bound.
    Primitive names are irrelevant to correctness; only extensional values and
    expression size matter.
    """
    grammar = SynthesisGrammar(
        primitives=basis,
        unary=constructors.unary,
        binary=constructors.binary,
        max_size=constructors.max_size,
    )
    target = _query_values(carrier, query)
    matches = [e.size for e in enumerate_expressions(carrier, grammar) if e.values == target]
    return min(matches, default=None)


def _partition(outcomes: Sequence[Optional[int]]) -> Tuple[Tuple[int, ...], ...]:
    groups = {}
    for index, outcome in enumerate(outcomes):
        groups.setdefault(outcome, []).append(index)
    return tuple(sorted((tuple(v) for v in groups.values()), key=lambda block: (len(block), block)))


def assess_interaction(
    carrier: Tuple[Hashable, ...],
    interface: Mapping[str, Observation],
    realizers: Sequence[Expression],
    constructors: SynthesisGrammar,
    interaction: Interaction,
) -> InteractionAssessment:
    outcomes = []
    for i, realizer in enumerate(realizers):
        basis = dict(interface)
        basis[f"candidate_{i}"] = realizer.observation(carrier)
        outcomes.append(minimum_query_cost(carrier, basis, constructors, interaction.query))
    outcomes_t = tuple(outcomes)
    blocks = _partition(outcomes_t)
    # Prefer more outcome blocks, then smaller worst-case surviving block, then
    # smaller total pair ambiguity.  All terms are deterministic integers.
    largest = max((len(b) for b in blocks), default=0)
    pair_ambiguity = sum(len(b) * (len(b) - 1) // 2 for b in blocks)
    score = (len(blocks), -largest, -pair_ambiguity)
    return InteractionAssessment(interaction, outcomes_t, blocks, score)


def choose_interaction(
    carrier: Tuple[Hashable, ...],
    interface: Mapping[str, Observation],
    realizers: Sequence[Expression],
    constructors: SynthesisGrammar,
    interactions: Sequence[Interaction],
) -> InteractionAssessment:
    if not realizers:
        raise ValueError("interaction selection requires a nonempty version space")
    if not interactions:
        raise ValueError("interaction selection requires at least one interaction")
    assessed = [
        assess_interaction(carrier, interface, realizers, constructors, interaction)
        for interaction in interactions
    ]
    # Stable deterministic tie break by interaction name.
    return max(assessed, key=lambda a: (a.score, tuple(-ord(c) for c in a.interaction.name)))


def contract_version_space(
    assessment: InteractionAssessment,
    observed_outcome: Optional[int],
) -> Tuple[int, ...]:
    return tuple(i for i, outcome in enumerate(assessment.outcomes) if outcome == observed_outcome)


def decide_from_verifier(
    assessment: InteractionAssessment,
    verifier_outcome: Optional[int],
) -> InteractionDecision:
    contracted = contract_version_space(assessment, verifier_outcome)
    if not contracted:
        raise ValueError("verifier outcome is inconsistent with all live realizers")
    return InteractionDecision(assessment, contracted, verifier_outcome)
