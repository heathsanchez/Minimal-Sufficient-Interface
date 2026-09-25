from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from collections import deque
from hashlib import sha256
import json
from typing import Hashable, Iterable, Mapping


def _canonical(value):
    if value is None:
        return ["none"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if is_dataclass(value):
        return [
            "dataclass",
            f"{type(value).__module__}.{type(value).__qualname__}",
            [
                [field.name, _canonical(getattr(value, field.name))]
                for field in fields(value)
            ],
        ]
    if isinstance(value, Mapping):
        entries = [(_canonical(key), _canonical(item)) for key, item in value.items()]
        entries.sort(key=lambda entry: _canonical_text(entry[0]))
        return ["map", entries]
    if isinstance(value, tuple):
        return ["tuple", [_canonical(item) for item in value]]
    if isinstance(value, list):
        return ["list", [_canonical(item) for item in value]]
    if isinstance(value, (set, frozenset)):
        items = [_canonical(item) for item in value]
        items.sort(key=_canonical_text)
        return ["set", items]
    raise TypeError(f"unsupported_canonical_type:{type(value).__module__}.{type(value).__qualname__}")


def _canonical_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def canonical_digest(value) -> str:
    payload = _canonical_text(_canonical(value)).encode("utf-8")
    return sha256(payload).hexdigest()


def _semantic_key(value) -> str:
    return _canonical_text(_canonical(value))


@dataclass(frozen=True)
class Transition:
    source: Hashable
    action: Hashable
    target: Hashable
    observation: Hashable
    effect: Hashable
    required_control: Hashable | None = None


@dataclass(frozen=True)
class ExplorationBoundary:
    actions: tuple[Hashable, ...]
    max_depth: int
    max_states: int

    def __post_init__(self):
        if self.max_depth < 0 or self.max_states <= 0:
            raise ValueError("invalid_exploration_boundary")


@dataclass(frozen=True)
class UnknownResidual:
    missing_interface: str
    reason: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class FiniteMachine:
    states: tuple[Hashable, ...]
    actions: tuple[Hashable, ...]
    transitions: tuple[Transition, ...]
    observations: tuple[tuple[Hashable, Hashable], ...]
    accepting: tuple[Hashable, ...]
    boundary: ExplorationBoundary
    content_id: str

    @classmethod
    def build(
        cls,
        *,
        states: Iterable[Hashable],
        actions: Iterable[Hashable],
        transitions: Iterable[Transition],
        observations: Mapping[Hashable, Hashable],
        accepting: Iterable[Hashable],
        boundary: ExplorationBoundary,
    ) -> FiniteMachine:
        state_tuple = tuple(sorted(set(states), key=_semantic_key))
        action_tuple = tuple(sorted(set(actions), key=_semantic_key))
        state_set = set(state_tuple)
        action_set = set(action_tuple)
        if set(boundary.actions) != action_set:
            raise ValueError("boundary_action_mismatch")
        if set(observations) != state_set:
            raise ValueError("observation_domain_mismatch")
        accepting_tuple = tuple(sorted(set(accepting), key=_semantic_key))
        if not set(accepting_tuple).issubset(state_set):
            raise ValueError("unknown_accepting_state")

        by_key: dict[tuple[Hashable, Hashable], Transition] = {}
        for transition in transitions:
            if transition.source not in state_set or transition.target not in state_set:
                raise ValueError("unknown_transition_state")
            if transition.action not in action_set:
                raise ValueError("unknown_transition_action")
            key = transition.source, transition.action
            previous = by_key.get(key)
            if previous is not None and previous != transition:
                raise ValueError("nondeterministic_transition")
            by_key[key] = transition
        transition_tuple = tuple(sorted(by_key.values(), key=_semantic_key))
        observation_tuple = tuple(
            sorted(observations.items(), key=lambda item: _semantic_key(item[0]))
        )
        normalized_boundary = ExplorationBoundary(
            tuple(sorted(set(boundary.actions), key=_semantic_key)),
            boundary.max_depth,
            boundary.max_states,
        )
        meaning = {
            "states": state_tuple,
            "actions": action_tuple,
            "transitions": transition_tuple,
            "observations": observation_tuple,
            "accepting": accepting_tuple,
            "boundary": normalized_boundary,
        }
        return cls(
            states=state_tuple,
            actions=action_tuple,
            transitions=transition_tuple,
            observations=observation_tuple,
            accepting=accepting_tuple,
            boundary=normalized_boundary,
            content_id=canonical_digest(meaning),
        )


@dataclass(frozen=True)
class FutureQuotient:
    classes: tuple[tuple[Hashable, ...], ...]
    transition_classes: tuple[
        tuple[int, Hashable, int, Hashable, Hashable, Hashable | None], ...
    ]
    witnesses: tuple[tuple[Hashable, Hashable, tuple[Hashable, ...]], ...]
    congruent: bool
    quotient_id: str
    residual: UnknownResidual | None = None

    def class_of(self, state: Hashable) -> int:
        for index, block in enumerate(self.classes):
            if state in block:
                return index
        raise KeyError(state)


def _machine_maps(machine: FiniteMachine):
    observations = dict(machine.observations)
    transitions = {
        (transition.source, transition.action): transition
        for transition in machine.transitions
    }
    return observations, transitions


def _blocks_from_signatures(signatures: Mapping[Hashable, Hashable]):
    grouped: dict[str, list[Hashable]] = {}
    for state, signature in signatures.items():
        grouped.setdefault(_semantic_key(signature), []).append(state)
    blocks = [tuple(sorted(states, key=_semantic_key)) for states in grouped.values()]
    return tuple(sorted(blocks, key=_semantic_key))


def _class_map(classes: tuple[tuple[Hashable, ...], ...]):
    return {
        state: index
        for index, block in enumerate(classes)
        for state in block
    }


def check_congruence(
    machine: FiniteMachine,
    classes: tuple[tuple[Hashable, ...], ...],
) -> bool:
    observations, transitions = _machine_maps(machine)
    state_class = _class_map(classes)
    accepting = set(machine.accepting)
    for block in classes:
        state_signatures = {
            (_semantic_key(observations[state]), state in accepting)
            for state in block
        }
        if len(state_signatures) != 1:
            return False
        for action in machine.actions:
            outcomes = set()
            for state in block:
                transition = transitions.get((state, action))
                if transition is None:
                    return False
                outcomes.add(
                    (
                        state_class[transition.target],
                        _semantic_key(transition.observation),
                        _semantic_key(transition.effect),
                        _semantic_key(transition.required_control),
                    )
                )
            if len(outcomes) != 1:
                return False
    return True


def shortest_separator(
    machine: FiniteMachine,
    left: Hashable,
    right: Hashable,
) -> tuple[Hashable, ...] | None:
    if left not in machine.states or right not in machine.states:
        raise KeyError("unknown_separator_state")
    observations, transitions = _machine_maps(machine)
    accepting = set(machine.accepting)

    def immediately_different(first, second) -> bool:
        return (
            observations[first] != observations[second]
            or (first in accepting) != (second in accepting)
        )

    if immediately_different(left, right):
        return ()
    queue = deque([((left, right), ())])
    seen = {(left, right)}
    for_pair_actions = tuple(sorted(machine.actions, key=_semantic_key))
    while queue:
        (first, second), word = queue.popleft()
        if len(word) >= machine.boundary.max_depth:
            continue
        for action in for_pair_actions:
            first_transition = transitions.get((first, action))
            second_transition = transitions.get((second, action))
            if first_transition is None or second_transition is None:
                continue
            next_word = word + (action,)
            if (
                first_transition.observation != second_transition.observation
                or first_transition.effect != second_transition.effect
                or first_transition.required_control != second_transition.required_control
                or immediately_different(first_transition.target, second_transition.target)
            ):
                return next_word
            pair = first_transition.target, second_transition.target
            if pair not in seen:
                seen.add(pair)
                queue.append((pair, next_word))
    return None


def refine_partition(machine: FiniteMachine) -> FutureQuotient:
    observations, transitions = _machine_maps(machine)
    missing = tuple(
        (state, action)
        for state in machine.states
        for action in machine.actions
        if (state, action) not in transitions
    )
    accepting = set(machine.accepting)
    signatures = {
        state: (observations[state], state in accepting)
        for state in machine.states
    }
    classes = _blocks_from_signatures(signatures)

    for _ in range(machine.boundary.max_depth if not missing else 0):
        state_class = _class_map(classes)
        refined = _blocks_from_signatures(
            {
                state: (
                    signatures[state],
                    tuple(
                        (
                            action,
                            transitions[(state, action)].observation,
                            transitions[(state, action)].effect,
                            transitions[(state, action)].required_control,
                            state_class[transitions[(state, action)].target],
                        )
                        for action in machine.actions
                    ),
                )
                for state in machine.states
            }
        )
        if refined == classes:
            break
        classes = refined
        signatures = {
            state: (
                signatures[state],
                tuple(
                    (
                        action,
                        transitions[(state, action)].observation,
                        transitions[(state, action)].effect,
                        transitions[(state, action)].required_control,
                        state_class[transitions[(state, action)].target],
                    )
                    for action in machine.actions
                ),
            )
            for state in machine.states
        }

    congruent = not missing and check_congruence(machine, classes)
    transition_classes: list[
        tuple[int, Hashable, int, Hashable, Hashable, Hashable | None]
    ] = []
    if congruent:
        state_class = _class_map(classes)
        for source_class, block in enumerate(classes):
            representative = block[0]
            for action in machine.actions:
                transition_classes.append(
                    (
                        source_class,
                        action,
                        state_class[transitions[(representative, action)].target],
                        transitions[(representative, action)].observation,
                        transitions[(representative, action)].effect,
                        transitions[(representative, action)].required_control,
                    )
                )

    witnesses = []
    for left_index, left in enumerate(machine.states):
        for right in machine.states[left_index + 1:]:
            separator = shortest_separator(machine, left, right)
            if separator is not None:
                witnesses.append((left, right, separator))
    witnesses_tuple = tuple(sorted(witnesses, key=_semantic_key))
    residual = None
    if missing:
        residual = UnknownResidual(
            "exploration.incomplete@1",
            "missing_declared_transitions",
            tuple(f"{_semantic_key(state)}:{_semantic_key(action)}" for state, action in missing),
        )
    elif not congruent:
        residual = UnknownResidual(
            "exploration.depth-bound@1",
            "declared_depth_does_not_close_future_partition",
            (f"max_depth={machine.boundary.max_depth}",),
        )
    identity = canonical_digest(
        {
            "machine": machine.content_id,
            "classes": classes,
            "transitions": tuple(transition_classes),
            "witnesses": witnesses_tuple,
            "congruent": congruent,
            "residual": residual,
        }
    )
    return FutureQuotient(
        classes=classes,
        transition_classes=tuple(transition_classes),
        witnesses=witnesses_tuple,
        congruent=congruent,
        quotient_id=identity,
        residual=residual,
    )


@dataclass(frozen=True)
class CompiledCapability:
    interface_id: str
    capability_id: str
    quotient_id: str
    start_class: int
    accepting_classes: tuple[int, ...]
    program: tuple[Hashable, ...]
    preserves: tuple[str, ...]
    lineage: tuple[str, ...]
    control_program: tuple[Hashable, ...] = ()


def shortest_accepting_program(
    machine: FiniteMachine,
    quotient: FutureQuotient,
    start: Hashable,
) -> tuple[Hashable, ...] | None:
    if start not in machine.states:
        raise KeyError(start)
    if quotient.residual is not None or not quotient.congruent:
        return None
    start_class = quotient.class_of(start)
    accepting_classes = {quotient.class_of(state) for state in machine.accepting}
    if start_class in accepting_classes:
        return ()
    transitions = {
        (source, action): target
        for source, action, target, _, _, _ in quotient.transition_classes
    }
    queue = deque([(start_class, ())])
    visited = {start_class}
    actions = tuple(sorted(machine.actions, key=_semantic_key))
    while queue:
        current, word = queue.popleft()
        for action in actions:
            target = transitions.get((current, action))
            if target is None:
                continue
            candidate = word + (action,)
            if target in accepting_classes:
                return candidate
            if target not in visited:
                visited.add(target)
                queue.append((target, candidate))
    return None


def _flatten_lineage(value) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (tuple, list)):
        return tuple(leaf for item in value for leaf in _flatten_lineage(item))
    raise TypeError("lineage_leaves_must_be_strings")


def compile_capability(
    machine: FiniteMachine,
    start: Hashable,
    preserves: Iterable[str],
    *,
    lineage=("protected-future-compiler@1",),
) -> CompiledCapability | UnknownResidual:
    quotient = refine_partition(machine)
    if quotient.residual is not None:
        return quotient.residual
    if not quotient.congruent:
        return UnknownResidual(
            "quotient.control-congruence@1",
            "partition_does_not_factor_actions",
        )
    program = shortest_accepting_program(machine, quotient, start)
    if program is None:
        return UnknownResidual(
            "terminal.oracle@1",
            "no_reachable_accepting_class",
        )
    start_class = quotient.class_of(start)
    accepting_classes = tuple(
        sorted({quotient.class_of(state) for state in machine.accepting})
    )
    preservation = tuple(sorted(set(preserves)))
    flat_lineage = _flatten_lineage(lineage)
    quotient_transitions = {
        (source, action): (target, required_control)
        for source, action, target, _, _, required_control in quotient.transition_classes
    }
    current_class = start_class
    controls = []
    for action in program:
        target_class, required_control = quotient_transitions[(current_class, action)]
        controls.append(action if required_control is None else required_control)
        current_class = target_class
    control_program = tuple(controls)
    meaning = {
        "interface": "program.protected-future-quotient@1",
        "quotient": quotient.quotient_id,
        "start": start_class,
        "accepting": accepting_classes,
        "program": program,
        "control_program": control_program,
        "preserves": preservation,
        "lineage": flat_lineage,
    }
    return CompiledCapability(
        interface_id="program.protected-future-quotient@1",
        capability_id=canonical_digest(meaning),
        quotient_id=quotient.quotient_id,
        start_class=start_class,
        accepting_classes=accepting_classes,
        program=program,
        preserves=preservation,
        lineage=flat_lineage,
        control_program=control_program,
    )
