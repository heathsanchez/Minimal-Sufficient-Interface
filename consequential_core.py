"""Shared formal objects for consequential distinction and verified development.

The core is intentionally small and restrictive. It distinguishes three kinds
of developmental change instead of hiding them behind a generic state update:

- representation refinement E' ⊂ E,
- executable language extension C' ⊃ C,
- developmental policy change D' != D.

A repair must be certified against a concrete residual before it can compile.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, FrozenSet, Hashable, Iterable, Optional, Tuple


Pair = Tuple[Hashable, Hashable]


@dataclass(frozen=True)
class EquivalenceRelation:
    carrier: Tuple[Hashable, ...]
    pairs: FrozenSet[Pair]

    def __post_init__(self):
        xs = self.carrier
        ps = self.pairs
        for x in xs:
            if (x, x) not in ps:
                raise ValueError("relation is not reflexive")
        for x in xs:
            for y in xs:
                if ((x, y) in ps) != ((y, x) in ps):
                    raise ValueError("relation is not symmetric")
        for x in xs:
            for y in xs:
                for z in xs:
                    if (x, y) in ps and (y, z) in ps and (x, z) not in ps:
                        raise ValueError("relation is not transitive")

    def same(self, x: Hashable, y: Hashable) -> bool:
        return (x, y) in self.pairs

    def refines(self, older: "EquivalenceRelation") -> bool:
        if self.carrier != older.carrier:
            return False
        return self.pairs <= older.pairs

    def strictly_refines(self, older: "EquivalenceRelation") -> bool:
        return self.refines(older) and self.pairs < older.pairs

    @classmethod
    def from_partition(cls, carrier: Iterable[Hashable], blocks: Iterable[Iterable[Hashable]]):
        carrier = tuple(carrier)
        block_list = [frozenset(b) for b in blocks]
        flat = frozenset(x for b in block_list for x in b)
        if flat != frozenset(carrier):
            raise ValueError("partition does not cover carrier exactly")
        if sum(len(b) for b in block_list) != len(carrier):
            raise ValueError("partition blocks overlap")
        pairs = frozenset((x, y) for b in block_list for x in b for y in b)
        return cls(carrier, pairs)

    @classmethod
    def from_observation(cls, carrier: Iterable[Hashable], observation: Callable[[Hashable], Hashable]):
        carrier = tuple(carrier)
        pairs = frozenset((x, y) for x in carrier for y in carrier if observation(x) == observation(y))
        return cls(carrier, pairs)


@dataclass(frozen=True)
class Residual:
    left: Hashable
    right: Hashable
    representation: EquivalenceRelation
    consequence_left: Hashable
    consequence_right: Hashable
    verifier_tag: str = "verified"

    def __post_init__(self):
        if not self.representation.same(self.left, self.right):
            raise ValueError("residual endpoints are already distinguished")
        if self.consequence_left == self.consequence_right:
            raise ValueError("protected consequence does not distinguish residual endpoints")
        if self.verifier_tag != "verified":
            raise ValueError("residual is not verifier-certified")


@dataclass(frozen=True)
class ClosureCertificate:
    interactions: Tuple[Any, ...]
    complete: bool
    regime: str

    def __post_init__(self):
        if not self.regime:
            raise ValueError("closure certificate must name its resource regime")


@dataclass(frozen=True)
class DevelopmentState:
    representation: EquivalenceRelation
    language: Tuple[Hashable, ...] = ()
    policy: Any = None


@dataclass(frozen=True)
class RefineRepresentation:
    new_representation: EquivalenceRelation


@dataclass(frozen=True)
class ExtendLanguage:
    delta: Hashable


@dataclass(frozen=True)
class UpdatePolicy:
    new_policy: Any


@dataclass(frozen=True)
class CoupledRepair:
    new_representation: Optional[EquivalenceRelation] = None
    language_delta: Optional[Hashable] = None
    new_policy: Any = None
    changes_policy: bool = False


Repair = RefineRepresentation | ExtendLanguage | UpdatePolicy | CoupledRepair


@dataclass(frozen=True)
class CertifiedRepair:
    repair: Repair
    residual: Residual
    attachment: str
    verifier_tag: str

    def __post_init__(self):
        if not self.attachment:
            raise ValueError("repair has no residual attachment certificate")
        if self.verifier_tag != "verified":
            raise ValueError("repair is not verifier-licensed")


@dataclass(frozen=True)
class ProvenanceToken:
    before: DevelopmentState
    after: DevelopmentState
    repair: Repair
    attachment: str


def conservative(state: DevelopmentState, repair: Repair) -> bool:
    if isinstance(repair, RefineRepresentation):
        return repair.new_representation.refines(state.representation)
    if isinstance(repair, ExtendLanguage):
        return repair.delta not in state.language
    if isinstance(repair, UpdatePolicy):
        return repair.new_policy != state.policy
    if isinstance(repair, CoupledRepair):
        if repair.new_representation is not None and not repair.new_representation.refines(state.representation):
            return False
        if repair.language_delta is not None and repair.language_delta in state.language:
            return False
        if repair.changes_policy and repair.new_policy == state.policy:
            return False
        return any((
            repair.new_representation is not None,
            repair.language_delta is not None,
            repair.changes_policy,
        ))
    raise TypeError(type(repair))


def residual_resolved_by_representation(residual: Residual, representation: EquivalenceRelation) -> bool:
    return not representation.same(residual.left, residual.right)


def certify_repair(
    state: DevelopmentState,
    residual: Residual,
    repair: Repair,
    resolves: Callable[[DevelopmentState, Repair, Residual], bool],
    *,
    attachment: str,
    verifier_tag: str = "verified",
) -> CertifiedRepair:
    if residual.representation != state.representation:
        raise ValueError("residual was not generated from this state representation")
    if not conservative(state, repair):
        raise ValueError("repair violates conservative-development constraints")
    if not resolves(state, repair, residual):
        raise ValueError("repair does not resolve the motivating residual")
    return CertifiedRepair(repair, residual, attachment, verifier_tag)


def compile_repair(state: DevelopmentState, certified: CertifiedRepair) -> tuple[DevelopmentState, ProvenanceToken]:
    repair = certified.repair
    representation = state.representation
    language = state.language
    policy = state.policy

    if isinstance(repair, RefineRepresentation):
        representation = repair.new_representation
    elif isinstance(repair, ExtendLanguage):
        language = language + (repair.delta,)
    elif isinstance(repair, UpdatePolicy):
        policy = repair.new_policy
    elif isinstance(repair, CoupledRepair):
        if repair.new_representation is not None:
            representation = repair.new_representation
        if repair.language_delta is not None:
            language = language + (repair.language_delta,)
        if repair.changes_policy:
            policy = repair.new_policy
    else:
        raise TypeError(type(repair))

    after = DevelopmentState(representation, language, policy)
    token = ProvenanceToken(state, after, repair, certified.attachment)
    return after, token


def ablate(state: DevelopmentState, token: ProvenanceToken) -> DevelopmentState:
    """Exact counterfactual ablation of one compiled contribution.

    This intentionally requires the current state to equal the provenance token's
    recorded post-state. It cannot silently erase unrelated later changes.
    """
    if state != token.after:
        raise ValueError("cannot exact-ablate after unrelated state changes")
    return token.before


def quotient_admissible(action: Callable[[Hashable], Hashable], representation: EquivalenceRelation) -> bool:
    xs = representation.carrier
    return all(
        (not representation.same(x, y))
        or representation.same(action(x), action(y))
        for x in xs
        for y in xs
    )
