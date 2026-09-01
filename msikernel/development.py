from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Hashable, Iterable, Sequence

from .continuation import Continuation, first_separator
from .interface import CompiledInterface, compile_interface
from .kernel import Equivalence

State = Hashable


@dataclass(frozen=True)
class Residual:
    x: State
    y: State
    separator: str


class Admission(str, Enum):
    CANDIDATE = "candidate"
    CAUSAL = "causal"
    TRANSFERRED = "transferred"
    ADMITTED = "admitted"
    REVOKED = "revoked"


@dataclass
class InterfaceRecord:
    interface: CompiledInterface
    status: Admission = Admission.CANDIDATE
    provenance: tuple[str, ...] = ()
    cost_delta: int | None = None
    ablation_restores_residual: bool | None = None


@dataclass
class InterfaceRegistry:
    """Explicit developmental state above the frozen MSI kernel."""

    records: Dict[str, InterfaceRecord] = field(default_factory=dict)

    def install_candidate(
        self,
        name: str,
        states: Iterable[State],
        continuations: Sequence[Continuation],
        provenance: Sequence[str] = (),
    ) -> InterfaceRecord:
        interface = compile_interface(name, states, continuations)
        record = InterfaceRecord(interface=interface, provenance=tuple(provenance))
        self.records[name] = record
        return record

    def promote(
        self,
        name: str,
        *,
        cost_delta: int,
        ablation_restores_residual: bool,
        transferred: bool,
    ) -> Admission:
        record = self.records[name]
        record.cost_delta = cost_delta
        record.ablation_restores_residual = ablation_restores_residual
        if cost_delta >= 0 or not ablation_restores_residual:
            record.status = Admission.CANDIDATE
        elif transferred:
            record.status = Admission.ADMITTED
        else:
            record.status = Admission.CAUSAL
        return record.status

    def revoke(self, name: str) -> None:
        self.records[name].status = Admission.REVOKED

    def active(self) -> tuple[CompiledInterface, ...]:
        return tuple(
            r.interface
            for r in self.records.values()
            if r.status is Admission.ADMITTED
        )


def residual_against(
    states: Iterable[State],
    current: Equivalence,
    protected: Sequence[Continuation],
) -> Residual | None:
    sep = first_separator(states, current, protected)
    if sep is None:
        return None
    x, y, c = sep
    return Residual(x=x, y=y, separator=c.name)
