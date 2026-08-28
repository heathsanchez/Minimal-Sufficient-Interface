from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, Iterable, Sequence

from .interface import CompiledInterface
from .kernel import Equivalence


@dataclass(frozen=True)
class TraceRow:
    state: Hashable
    context: Hashable
    outcome: Hashable


@dataclass(frozen=True)
class TraceCoverage:
    states: tuple[Hashable, ...]
    contexts: tuple[Hashable, ...]
    observed_cells: int
    required_cells: int

    @property
    def complete(self) -> bool:
        return self.observed_cells == self.required_cells


def compile_anonymous_trace_interface(
    name: str,
    rows: Iterable[TraceRow],
    *,
    context_order: Sequence[Hashable] | None = None,
) -> tuple[CompiledInterface, TraceCoverage]:
    """Compile an MSI quotient from an anonymous complete outcome matrix.

    The compiler receives only opaque state ids, opaque context ids, and opaque
    outcomes.  It does not receive host semantic class labels.  Missing cells
    fail closed because absence of an observation is not evidence of equality.
    """
    rows = tuple(rows)
    states = tuple(dict.fromkeys(r.state for r in rows))
    if context_order is None:
        contexts = tuple(dict.fromkeys(r.context for r in rows))
    else:
        contexts = tuple(context_order)

    cell: Dict[tuple[Hashable, Hashable], Hashable] = {}
    for row in rows:
        key = (row.state, row.context)
        if key in cell and cell[key] != row.outcome:
            raise ValueError(f"conflicting verifier outcomes for cell {key!r}")
        cell[key] = row.outcome

    required = len(states) * len(contexts)
    coverage = TraceCoverage(states, contexts, len(cell), required)
    missing = [(s, c) for s in states for c in contexts if (s, c) not in cell]
    if missing:
        raise ValueError(f"incomplete protected continuation matrix: {len(missing)} cells missing")

    signatures = {s: tuple(cell[(s, c)] for c in contexts) for s in states}
    eqv = Equivalence.from_signatures(signatures)
    interface = CompiledInterface(
        name=name,
        protected=tuple(str(c) for c in contexts),
        class_of=dict(eqv.classes),
        equivalence=eqv,
    )
    return interface, coverage
