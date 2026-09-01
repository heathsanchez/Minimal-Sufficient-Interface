"""Domain-independent compiler for consequence-driven representation change.

The compiler takes only a finite carrier plus declared observations, protected
consequences, candidate realization coordinates, and optional operational cost
profiles.  It computes the current quotient, certified residual witnesses, the
canonical meet repair, lawful realization candidates, factorization status, and
one licensed compiled transition using the existing consequential_core trust
boundary.

No domain-specific repair logic belongs here.  Constitutional, IRL, graph,
proof-search, or other experiments should enter only through CompilerSpec data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Hashable, Mapping, Optional, Tuple

from consequential_core import (
    CertifiedRepair,
    DevelopmentState,
    EquivalenceRelation,
    PairResidual,
    ProvenanceToken,
    RefineRepresentation,
    ablate,
    certify_repair,
    compile_repair,
)

Observation = Callable[[Hashable], Hashable]


@dataclass(frozen=True)
class CompilerSpec:
    name: str
    carrier: Tuple[Hashable, ...]
    interface: Mapping[str, Observation]
    protected: Mapping[str, Observation]
    realizers: Mapping[str, Observation]
    future_queries: Mapping[str, Observation] = None
    realization_costs: Mapping[str, Mapping[str, int]] = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("compiler spec must be named")
        if not self.carrier:
            raise ValueError("compiler carrier must be nonempty")
        if not self.interface:
            raise ValueError("compiler requires at least one interface observation")
        if not self.protected:
            raise ValueError("compiler requires at least one protected consequence")
        if self.future_queries is None:
            object.__setattr__(self, "future_queries", {})
        if self.realization_costs is None:
            object.__setattr__(self, "realization_costs", {})


@dataclass(frozen=True)
class ResidualWitness:
    protected_name: str
    left: Hashable
    right: Hashable
    left_value: Hashable
    right_value: Hashable


@dataclass(frozen=True)
class CompilerReport:
    name: str
    current: EquivalenceRelation
    required: EquivalenceRelation
    residuals: Tuple[ResidualWitness, ...]
    strict_repair: bool
    lawful_realizers: Tuple[str, ...]
    protected_factors_before: Mapping[str, bool]
    protected_factors_after: Mapping[str, bool]
    future_factors_before: Mapping[str, bool]
    future_factors_after: Mapping[str, bool]
    lawful_cost_profiles: Mapping[str, Mapping[str, int]]
    before_state: DevelopmentState
    certified_repair: Optional[CertifiedRepair]
    after_state: DevelopmentState
    provenance: Optional[ProvenanceToken]
    exact_ablation_ok: bool


def kernel(carrier: Tuple[Hashable, ...], observations: Mapping[str, Observation]) -> EquivalenceRelation:
    names = tuple(observations)

    def signature(x: Hashable):
        return tuple(observations[name](x) for name in names)

    return EquivalenceRelation.from_observation(carrier, signature)


def meet(*relations: EquivalenceRelation) -> EquivalenceRelation:
    if not relations:
        raise ValueError("meet requires at least one relation")
    carrier = relations[0].carrier
    if any(r.carrier != carrier for r in relations):
        raise ValueError("cannot meet relations on different carriers")
    pairs = frozenset.intersection(*(r.pairs for r in relations))
    return EquivalenceRelation(carrier, pairs)


def factors_through(representation: EquivalenceRelation, observation: Observation) -> bool:
    return all(
        (not representation.same(x, y)) or observation(x) == observation(y)
        for x in representation.carrier
        for y in representation.carrier
    )


def residual_witnesses(
    representation: EquivalenceRelation,
    protected: Mapping[str, Observation],
) -> Tuple[ResidualWitness, ...]:
    out = []
    xs = representation.carrier
    for name, observation in protected.items():
        for i, x in enumerate(xs):
            for y in xs[i + 1 :]:
                if representation.same(x, y) and observation(x) != observation(y):
                    out.append(ResidualWitness(name, x, y, observation(x), observation(y)))
    return tuple(out)


def compile_consequences(spec: CompilerSpec) -> CompilerReport:
    current = kernel(spec.carrier, spec.interface)
    protected_kernels = tuple(
        EquivalenceRelation.from_observation(spec.carrier, observation)
        for observation in spec.protected.values()
    )
    required = meet(current, *protected_kernels)
    residuals = residual_witnesses(current, spec.protected)

    protected_before = {
        name: factors_through(current, observation)
        for name, observation in spec.protected.items()
    }
    protected_after = {
        name: factors_through(required, observation)
        for name, observation in spec.protected.items()
    }
    future_before = {
        name: factors_through(current, observation)
        for name, observation in spec.future_queries.items()
    }
    future_after = {
        name: factors_through(required, observation)
        for name, observation in spec.future_queries.items()
    }

    lawful = []
    for name, candidate in spec.realizers.items():
        realized = kernel(spec.carrier, {**dict(spec.interface), "__candidate__": candidate})
        if realized == required:
            lawful.append(name)
    lawful = tuple(lawful)

    lawful_costs: Dict[str, Mapping[str, int]] = {
        name: dict(spec.realization_costs[name])
        for name in lawful
        if name in spec.realization_costs
    }

    before = DevelopmentState(spec.carrier, active_representation=current)
    certified = None
    after = before
    provenance = None
    exact_ablation_ok = True

    if residuals:
        first = residuals[0]
        pair_residual = PairResidual(
            first.left,
            first.right,
            current,
            first.left_value,
            first.right_value,
        )
        repair = RefineRepresentation(required)

        def resolves(_state, proposed, motivating):
            return (
                isinstance(proposed, RefineRepresentation)
                and isinstance(motivating, PairResidual)
                and not proposed.new_representation.same(motivating.left, motivating.right)
            )

        certified = certify_repair(
            before,
            pair_residual,
            repair,
            resolves,
            attachment="canonical meet of current interface kernel and protected consequence kernels",
        )
        after, provenance = compile_repair(before, certified)
        exact_ablation_ok = ablate(after, provenance) == before

    return CompilerReport(
        spec.name,
        current,
        required,
        residuals,
        required.strictly_refines(current),
        lawful,
        protected_before,
        protected_after,
        future_before,
        future_after,
        lawful_costs,
        before,
        certified,
        after,
        provenance,
        exact_ablation_ok,
    )
