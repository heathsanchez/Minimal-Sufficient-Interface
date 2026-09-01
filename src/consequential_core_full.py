"""Minimal executable core for consequential distinction."""

from dataclasses import dataclass, replace
from typing import Hashable, Iterable, Optional, Tuple

Partition = Tuple[Tuple[int, ...], ...]
Column = Tuple[Hashable, ...]
StateMap = Tuple[int, ...]


def canon_partition(blocks: Iterable[Iterable[int]]) -> Partition:
    return tuple(sorted(tuple(sorted(block)) for block in blocks))


def block_index(p: Partition) -> dict[int, int]:
    out = {}
    for i, block in enumerate(p):
        for x in block:
            out[x] = i
    return out


def equivalent(p: Partition, x: int, y: int) -> bool:
    idx = block_index(p)
    return idx[x] == idx[y]


def refines(new: Partition, old: Partition) -> bool:
    old_idx = block_index(old)
    return all(old_idx[x] == old_idx[y] for block in new for x in block for y in block)


def kernel(column: Column) -> Partition:
    groups: dict[Hashable, list[int]] = {}
    for i, value in enumerate(column):
        groups.setdefault(value, []).append(i)
    return canon_partition(groups.values())


def meet_partitions(parts: Iterable[Partition], carrier: Tuple[int, ...]) -> Partition:
    parts = tuple(parts)
    if not parts:
        return (tuple(carrier),)
    idxs = [block_index(p) for p in parts]
    groups: dict[Tuple[int, ...], list[int]] = {}
    for x in carrier:
        sig = tuple(idx[x] for idx in idxs)
        groups.setdefault(sig, []).append(x)
    return canon_partition(groups.values())


def compose(f: StateMap, g: StateMap) -> StateMap:
    return tuple(f[g[x]] for x in range(len(g)))


def action_closure(generators: Tuple[StateMap, ...], carrier: Tuple[int, ...]) -> Tuple[StateMap, ...]:
    identity = tuple(carrier)
    seen = {identity}
    frontier = [identity]
    while frontier:
        current = frontier.pop()
        for g in generators:
            nxt = compose(g, current)
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return tuple(sorted(seen))


def observe_after(column: Column, action: StateMap) -> Column:
    return tuple(column[action[x]] for x in range(len(action)))


@dataclass(frozen=True)
class FiniteObservationLanguage:
    observations: Tuple[Column, ...]
    dynamics: Tuple[StateMap, ...]

    def closure_actions(self, carrier: Tuple[int, ...]) -> Tuple[StateMap, ...]:
        return action_closure(self.dynamics, carrier)

    def closure_observations(self, carrier: Tuple[int, ...]) -> Tuple[Column, ...]:
        cols = {
            observe_after(obs, action)
            for obs in self.observations
            for action in self.closure_actions(carrier)
        }
        return tuple(sorted(cols, key=repr))

    def induced_representation(self, carrier: Tuple[int, ...]) -> Partition:
        return meet_partitions((kernel(col) for col in self.closure_observations(carrier)), carrier)

    def extend_observation(self, column: Column) -> "FiniteObservationLanguage":
        if not column:
            raise ValueError("empty observation")
        return replace(self, observations=self.observations + (column,))


@dataclass(frozen=True)
class Provenance:
    identifier: str
    parent: "DevelopmentState"
    repair_kind: str


@dataclass(frozen=True)
class DevelopmentState:
    carrier: Tuple[int, ...]
    representation: Partition
    language: FiniteObservationLanguage
    provenance: Optional[Provenance] = None

    @staticmethod
    def from_language(carrier: Tuple[int, ...], language: FiniteObservationLanguage) -> "DevelopmentState":
        return DevelopmentState(carrier, language.induced_representation(carrier), language)


@dataclass(frozen=True)
class Residual:
    pair: Tuple[int, int]
    consequence: Optional[Column]
    certified: bool
    closure_exhausted: bool


def certify_residual(state: DevelopmentState, pair: Tuple[int, int], consequence: Optional[Column] = None) -> Residual:
    x, y = pair
    if not equivalent(state.representation, x, y):
        raise ValueError("pair is already distinguished")
    if not all(col[x] == col[y] for col in state.language.closure_observations(state.carrier)):
        raise ValueError("closure already distinguishes pair")
    if consequence is not None and consequence[x] == consequence[y]:
        raise ValueError("consequence does not separate pair")
    return Residual(pair, consequence, True, True)


@dataclass(frozen=True)
class RepresentationRepair:
    new_representation: Partition
    residual_pair: Tuple[int, int]


@dataclass(frozen=True)
class CapabilityRepair:
    observation: Column
    residual_pair: Tuple[int, int]


def partitions(xs: Tuple[int, ...]):
    if not xs:
        yield ()
        return
    first, rest = xs[0], xs[1:]
    for p in partitions(rest):
        yield ((first,),) + p
        for i in range(len(p)):
            q = [tuple(block) for block in p]
            q[i] = tuple(sorted(q[i] + (first,)))
            yield tuple(q)


def invariant(p: Partition, dynamics: Tuple[StateMap, ...]) -> bool:
    return all(not equivalent(p, x, y) or equivalent(p, g[x], g[y]) for g in dynamics for x in range(len(g)) for y in range(len(g)))


def representation_version_space(state: DevelopmentState, residual: Residual) -> Tuple[RepresentationRepair, ...]:
    if not (residual.certified and residual.closure_exhausted):
        raise ValueError("uncertified residual")
    x, y = residual.pair
    lawful = []
    for raw in partitions(state.carrier):
        p = canon_partition(raw)
        if refines(p, state.representation) and not equivalent(p, x, y) and invariant(p, state.language.dynamics):
            lawful.append(p)
    if not lawful:
        return ()
    minimum_blocks = min(len(p) for p in lawful)
    minima = sorted({p for p in lawful if len(p) == minimum_blocks})
    return tuple(RepresentationRepair(p, residual.pair) for p in minima)


def discriminating_pairs(repairs: Tuple[RepresentationRepair, ...]) -> Tuple[Tuple[int, int], ...]:
    pairs = set()
    for i in range(len(repairs)):
        for j in range(i + 1, len(repairs)):
            p, q = repairs[i].new_representation, repairs[j].new_representation
            xs = sorted({x for block in p for x in block})
            for x in xs:
                for y in xs:
                    if x < y and equivalent(p, x, y) != equivalent(q, x, y):
                        pairs.add((x, y))
    return tuple(sorted(pairs))


def select_by_verified_pair(repairs: Tuple[RepresentationRepair, ...], pair: Tuple[int, int], should_be_equal: bool) -> Tuple[RepresentationRepair, ...]:
    x, y = pair
    return tuple(r for r in repairs if equivalent(r.new_representation, x, y) == should_be_equal)


def certify_capability_repair(state: DevelopmentState, residual: Residual, observation: Column) -> CapabilityRepair:
    if not (residual.certified and residual.closure_exhausted):
        raise ValueError("uncertified residual")
    if len(observation) != len(state.carrier):
        raise ValueError("observation arity mismatch")
    x, y = residual.pair
    old_kernels = {kernel(col) for col in state.language.closure_observations(state.carrier)}
    if kernel(observation) in old_kernels:
        raise ValueError("capability is not novel")
    if observation[x] == observation[y]:
        raise ValueError("capability does not attach")
    return CapabilityRepair(observation, residual.pair)


def compile_representation(state: DevelopmentState, repair: RepresentationRepair, identifier: str) -> DevelopmentState:
    if not refines(repair.new_representation, state.representation):
        raise ValueError("repair merges prior distinctions")
    x, y = repair.residual_pair
    if equivalent(repair.new_representation, x, y) or not invariant(repair.new_representation, state.language.dynamics):
        raise ValueError("unlawful or unattached representation repair")
    return DevelopmentState(state.carrier, repair.new_representation, state.language, Provenance(identifier, state, "representation"))


def compile_capability(state: DevelopmentState, repair: CapabilityRepair, identifier: str) -> DevelopmentState:
    extended = state.language.extend_observation(repair.observation)
    induced = extended.induced_representation(state.carrier)
    if not refines(induced, state.representation):
        raise ValueError("capability compilation erased prior distinctions")
    x, y = repair.residual_pair
    if equivalent(induced, x, y):
        raise ValueError("compiled capability failed to resolve residual")
    return DevelopmentState(state.carrier, induced, extended, Provenance(identifier, state, "capability"))


def ablate(state: DevelopmentState, identifier: str) -> DevelopmentState:
    if state.provenance is None or state.provenance.identifier != identifier:
        raise ValueError("provenance mismatch")
    return state.provenance.parent


def quotient_admissible(action: StateMap, representation: Partition) -> bool:
    return all(not equivalent(representation, x, y) or equivalent(representation, action[x], action[y]) for x in range(len(action)) for y in range(len(action)))


def orbit(g: StateMap, x: int) -> frozenset[int]:
    seen = set()
    y = x
    while y not in seen:
        seen.add(y)
        y = g[y]
    return frozenset(seen)


def residual_orbit_observation(state: DevelopmentState, residual: Residual, generator: StateMap) -> Column:
    x, y = residual.pair
    ox, oy = orbit(generator, x), orbit(generator, y)
    if not ox.isdisjoint(oy) or ox | oy != frozenset(state.carrier):
        raise ValueError("residual orbits do not form binary exhaustive separator")
    return tuple(0 if z in ox else 1 for z in state.carrier)
