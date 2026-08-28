from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Hashable, Iterable, Mapping, Sequence, Tuple

from .continuation import Continuation, induced_equivalence
from .kernel import Equivalence

State = Hashable


@dataclass(frozen=True)
class CompiledInterface:
    """A continuation-relative executable quotient.

    `class_of` is the runtime interface representation.  It is admitted only
    when it induces exactly the same equivalence as the protected continuation
    family on the frozen carrier.
    """

    name: str
    protected: Tuple[str, ...]
    class_of: Mapping[State, int]
    equivalence: Equivalence

    def ref(self, state: State) -> int:
        return self.class_of[state]

    def preserves(self, x: State, y: State) -> bool:
        return (self.ref(x) == self.ref(y)) == self.equivalence.equivalent(x, y)


def compile_interface(
    name: str,
    states: Iterable[State],
    continuations: Sequence[Continuation],
) -> CompiledInterface:
    """Compile the exact future-relative quotient for a frozen carrier.

    V0 deliberately performs no semantic naming.  The only runtime class
    identity comes from equality of protected future outcome signatures.
    """
    states = tuple(states)
    eqv = induced_equivalence(states, continuations)
    return CompiledInterface(
        name=name,
        protected=tuple(c.name for c in continuations),
        class_of=dict(eqv.classes),
        equivalence=eqv,
    )


def quotient_admissible(
    states: Iterable[State],
    interface: CompiledInterface,
    transition: Callable[[State], State],
) -> bool:
    """A transition descends iff it is congruent for the compiled quotient."""
    states = tuple(states)
    for x in states:
        for y in states:
            if interface.ref(x) == interface.ref(y):
                if interface.ref(transition(x)) != interface.ref(transition(y)):
                    return False
    return True
