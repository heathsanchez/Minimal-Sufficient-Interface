from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, Iterable, Mapping, Tuple

State = Hashable


@dataclass(frozen=True)
class Equivalence:
    """Finite equivalence relation represented by a canonical class id per state.

    This is the concrete Eq(X) realization of the MSI meet kernel.  Class labels
    are intentionally non-semantic; only equality of labels matters.
    """

    classes: Mapping[State, int]

    @staticmethod
    def indiscrete(states: Iterable[State]) -> "Equivalence":
        return Equivalence({x: 0 for x in states})

    @staticmethod
    def from_signatures(signatures: Mapping[State, Tuple[Hashable, ...]]) -> "Equivalence":
        ids: Dict[Tuple[Hashable, ...], int] = {}
        out: Dict[State, int] = {}
        for x, sig in signatures.items():
            if sig not in ids:
                ids[sig] = len(ids)
            out[x] = ids[sig]
        return Equivalence(out)

    def equivalent(self, x: State, y: State) -> bool:
        return self.classes[x] == self.classes[y]

    def refines(self, other: "Equivalence") -> bool:
        """Return True iff self <= other in the MSI refinement order."""
        states = tuple(self.classes)
        return all(
            not self.equivalent(x, y) or other.equivalent(x, y)
            for x in states
            for y in states
        )

    def num_classes(self) -> int:
        return len(set(self.classes.values()))


def meet_equivalence(a: Equivalence, b: Equivalence) -> Equivalence:
    """Intersection/meet of two finite equivalence relations."""
    if set(a.classes) != set(b.classes):
        raise ValueError("meet requires the same carrier")
    signatures = {x: (a.classes[x], b.classes[x]) for x in a.classes}
    return Equivalence.from_signatures(signatures)
