from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
from typing import Iterable


@dataclass(frozen=True)
class FoundryConfig:
    seed: int = 0
    variants_per_family: int = 100
    split: str = "train"

    def __post_init__(self) -> None:
        if self.variants_per_family < 1:
            raise ValueError("variants_per_family must be positive")
        if self.split not in {"train", "holdout"}:
            raise ValueError("split must be train or holdout")


@dataclass(frozen=True)
class Transition:
    state: str
    action: str
    next_state: str


@dataclass(frozen=True)
class MicroWorld:
    world_id: str
    family: str
    states: tuple[str, ...]
    actions: tuple[str, ...]
    transitions: tuple[Transition, ...]

    def table(self) -> dict[tuple[str, str], str]:
        return {(row.state, row.action): row.next_state for row in self.transitions}


@dataclass(frozen=True)
class FoundryCorpus:
    worlds: tuple[MicroWorld, ...]

    @property
    def world_ids(self) -> tuple[str, ...]:
        return tuple(world.world_id for world in self.worlds)

    @property
    def transition_count(self) -> int:
        return sum(len(world.transitions) for world in self.worlds)


@dataclass(frozen=True)
class CompiledLaw:
    kind: str
    status: str
    support_worlds: int
    counterexamples: int
    family_scope: tuple[str, ...]
    evidence_world_ids: tuple[str, ...]


FAMILIES = ("cycle", "involution", "idempotent", "commuting", "noncommuting", "guarded")


def _opaque_labels(n: int, rng: random.Random, prefix: str) -> tuple[str, ...]:
    raw = [f"{prefix}{i}" for i in range(n)]
    rng.shuffle(raw)
    salt = rng.randrange(1 << 32)
    return tuple(
        hashlib.blake2b(f"{salt}:{item}".encode(), digest_size=6).hexdigest()
        for item in raw
    )


def _world_id(seed: int, split: str, family: str, index: int, transitions) -> str:
    payload = json.dumps(
        [seed, split, family, index, transitions],
        sort_keys=True, separators=(",", ":"),
    )
    return f"{split}:{family}:" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def _make_world(seed: int, split: str, family: str, index: int) -> MicroWorld:
    split_salt = 0 if split == "train" else 10_000_019
    rng = random.Random(seed * 1_000_003 + split_salt + index * 97 + FAMILIES.index(family) * 7919)

    if family == "cycle":
        n = rng.randint(3, 7)
        canonical_states = tuple(range(n))
        actions = ("a", "idle")
        step = lambda s, a: (s + 1) % n if a == "a" else s
    elif family == "involution":
        n = 8
        canonical_states = tuple(range(n))
        actions = ("a", "idle")
        step = lambda s, a: (s ^ 1) if a == "a" else s
    elif family == "idempotent":
        n = 8
        canonical_states = tuple(range(n))
        target = rng.randrange(n)
        actions = ("a", "idle")
        step = lambda s, a: target if a == "a" else s
    elif family == "commuting":
        n = 8
        canonical_states = tuple(range(n))
        actions = ("a", "b", "idle")
        def step(s, a):
            if a == "a":
                return s ^ 1
            if a == "b":
                return s ^ 2
            return s
    elif family == "noncommuting":
        n = 8
        canonical_states = tuple(range(n))
        actions = ("a", "b", "idle")
        def step(s, a):
            if a == "a":
                return (s + 1) % n
            if a == "b":
                return 0
            return s
    elif family == "guarded":
        # State = 3*mode + value. Action a is inert in mode 0 and advances
        # toward a fixed point in mode 1; b switches mode. There is no global
        # finite period for a, but its effect is conditional on a state guard.
        canonical_states = tuple(range(6))
        n = 6
        actions = ("a", "b", "idle")
        def step(s, a):
            mode, value = divmod(s, 3)
            if a == "a":
                return s if mode == 0 else 3 + min(2, value + 1)
            if a == "b":
                return (1 - mode) * 3 + value
            return s
    else:
        raise ValueError(family)

    labels = _opaque_labels(n, rng, family[0])
    action_labels = list(actions)
    rng.shuffle(action_labels)
    # Preserve no semantic meaning in action names: map canonical operators to
    # opaque per-world symbols.
    opaque_actions = _opaque_labels(len(actions), rng, "u")
    action_map = dict(zip(action_labels, opaque_actions))
    # action_labels was shuffled, so recover a deterministic bijection from
    # canonical names through its position in that shuffle.
    canonical_to_opaque = {name: action_map[name] for name in actions}

    rows = []
    canonical_rows = []
    for s in canonical_states:
        for action in actions:
            ns = step(s, action)
            rows.append(Transition(labels[s], canonical_to_opaque[action], labels[ns]))
            canonical_rows.append((s, action, ns))
    rows.sort(key=lambda row: (row.state, row.action, row.next_state))
    wid = _world_id(seed, split, family, index, canonical_rows)
    return MicroWorld(
        world_id=wid,
        family=family,
        states=tuple(sorted(labels)),
        actions=tuple(sorted(opaque_actions)),
        transitions=tuple(rows),
    )


def generate_corpus(config: FoundryConfig) -> FoundryCorpus:
    worlds = tuple(
        _make_world(config.seed, config.split, family, index)
        for family in FAMILIES
        for index in range(config.variants_per_family)
    )
    return FoundryCorpus(worlds)


def _compose(table, state, first, second):
    return table[(table[(state, first)], second)]


def _least_uniform_period(world: MicroWorld, action: str) -> int | None:
    table = world.table()
    for period in range(1, len(world.states) + 1):
        good = True
        for state in world.states:
            cursor = state
            for _ in range(period):
                cursor = table[(cursor, action)]
            if cursor != state:
                good = False
                break
        if good:
            return period
    return None


def _is_idempotent(world: MicroWorld, action: str) -> bool:
    table = world.table()
    return all(
        table[(table[(state, action)], action)] == table[(state, action)]
        for state in world.states
    )


def _guard_signature(world: MicroWorld, action: str) -> bool:
    table = world.table()
    changed = [state for state in world.states if table[(state, action)] != state]
    fixed = [state for state in world.states if table[(state, action)] == state]
    # Candidate only: mixed fixed/changing behavior is a signal that an
    # applicability guard may exist, not proof of what that guard is.
    return bool(changed and fixed)


def compile_laws(corpus: FoundryCorpus) -> tuple[CompiledLaw, ...]:
    support: dict[tuple[str, str], set[str]] = {}
    families: dict[tuple[str, str], set[str]] = {}

    def note(kind: str, world: MicroWorld) -> None:
        key = (kind, "all")
        support.setdefault(key, set()).add(world.world_id)
        families.setdefault(key, set()).add(world.family)

    for world in corpus.worlds:
        table = world.table()
        actions = world.actions
        for action in actions:
            period = _least_uniform_period(world, action)
            if period is not None and period > 1:
                note("uniform_period", world)
                if period == 2:
                    note("involution", world)
            if _is_idempotent(world, action):
                # Exclude pure identity from the useful idempotent capability.
                if any(table[(state, action)] != state for state in world.states):
                    note("idempotent", world)
            if _guard_signature(world, action):
                note("guarded_effect", world)

        for i, first in enumerate(actions):
            for second in actions[i + 1:]:
                commutes = all(
                    _compose(table, state, first, second)
                    == _compose(table, state, second, first)
                    for state in world.states
                )
                note("commutes" if commutes else "noncommutes", world)

    out = []
    for (kind, _), ids in sorted(support.items()):
        scope = tuple(sorted(families[(kind, "all")]))
        status = "CANDIDATE" if kind == "guarded_effect" else "WARRANTED_BOUNDED"
        out.append(CompiledLaw(
            kind=kind,
            status=status,
            support_worlds=len(ids),
            counterexamples=0,
            family_scope=scope,
            evidence_world_ids=tuple(sorted(ids)),
        ))
    return tuple(out)
