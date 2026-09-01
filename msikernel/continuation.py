from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Mapping, Sequence, Tuple

from .kernel import Equivalence

State = Hashable
Outcome = Hashable


@dataclass(frozen=True)
class Continuation:
    """A protected future observation c : X -> O_c."""

    name: str
    observe: Callable[[State], Outcome]


def induced_equivalence(states: Iterable[State], continuations: Sequence[Continuation]) -> Equivalence:
    """E_B = intersection_{c in B} ker(c), represented by outcome signatures."""
    states = tuple(states)
    signatures: Mapping[State, Tuple[Outcome, ...]] = {
        x: tuple(c.observe(x) for c in continuations) for x in states
    }
    return Equivalence.from_signatures(signatures)


def first_separator(
    states: Iterable[State],
    current: Equivalence,
    continuations: Sequence[Continuation],
) -> tuple[State, State, Continuation] | None:
    """Return the first future that separates a pair still merged by current."""
    states = tuple(states)
    for i, x in enumerate(states):
        for y in states[i + 1 :]:
            if not current.equivalent(x, y):
                continue
            for c in continuations:
                if c.observe(x) != c.observe(y):
                    return x, y, c
    return None
