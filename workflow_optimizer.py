"""Minimal executable controller for verified recursive workflow experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable, Sequence


class ActionClass(str, Enum):
    PUSH = "PUSH"
    PROBE = "PROBE"
    REFRAME = "REFRAME"
    META = "META"


class TerminalState(str, Enum):
    SOLVED = "SOLVED"
    IMPROVED = "IMPROVED"
    REFUTED = "REFUTED"
    OBSTRUCTED = "OBSTRUCTED"
    FIXED = "FIXED"
    COMPILE = "COMPILE"
    INTERACT = "INTERACT"
    ESCALATE = "ESCALATE"
    UNKNOWN = "UNKNOWN"
    INFRA = "INFRA"


@dataclass(frozen=True)
class ProblemContract:
    target: str
    verifier: str
    budget: int
    success_criteria: str
    allowed_evidence: tuple[str, ...] = ()
    forbidden_leakage: tuple[str, ...] = ()


@dataclass(frozen=True)
class Proposal:
    id: str
    action_class: ActionClass
    cost: int
    target_value: int
    information_value: int = 0
    capability_value: int = 0
    licensed: bool = True

    @property
    def value_per_cost(self) -> float:
        return (
            self.target_value + self.information_value + self.capability_value
        ) / self.cost


@dataclass(frozen=True)
class Verification:
    passed: bool
    terminal: TerminalState
    target_progress: int
    residual: str | None = None


@dataclass
class DevelopmentMemory:
    active: list[str] = field(default_factory=list)
    provenance: list[dict] = field(default_factory=list)
    successes: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    promotions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    graph: list[dict] = field(default_factory=list)


@dataclass
class DevelopmentState:
    contract: ProblemContract
    workflow: str
    memory: DevelopmentMemory = field(default_factory=DevelopmentMemory)
    spent: int = 0
    terminal: TerminalState = TerminalState.UNKNOWN
    target_progress: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


Verifier = Callable[[Proposal], Verification]


class WorkflowController:
    """A deterministic controller whose policy is explicit and ablatable."""

    def __init__(self, name: str, directness_gate: bool):
        self.name = name
        self.directness_gate = directness_gate

    def rank(self, proposals: Sequence[Proposal]) -> list[Proposal]:
        admissible = [p for p in proposals if p.licensed]
        if self.directness_gate:
            priority = {
                ActionClass.PUSH: 0,
                ActionClass.PROBE: 1,
                ActionClass.REFRAME: 2,
                ActionClass.META: 3,
            }
            return sorted(
                admissible,
                key=lambda p: (priority[p.action_class], -p.value_per_cost, p.id),
            )
        return sorted(admissible, key=lambda p: (-p.value_per_cost, p.id))

    def run(
        self,
        state: DevelopmentState,
        proposals: Iterable[Proposal],
        verifier: Verifier,
    ) -> DevelopmentState:
        remaining = list(proposals)
        while remaining and state.spent < state.contract.budget:
            affordable = [
                p for p in remaining if p.cost <= state.contract.budget - state.spent
            ]
            if not affordable:
                break
            proposal = self.rank(affordable)[0]
            remaining.remove(proposal)
            result = verifier(proposal)
            state.spent += proposal.cost
            state.target_progress += result.target_progress
            state.terminal = result.terminal
            event = {
                "proposal": asdict(proposal),
                "verification": asdict(result),
                "spent_after": state.spent,
            }
            event["event_sha256"] = hashlib.sha256(
                json.dumps(event, sort_keys=True).encode()
            ).hexdigest()
            state.memory.provenance.append(event)
            if result.passed:
                state.memory.successes.append(proposal.id)
            else:
                state.memory.failures.append(proposal.id)
                if result.residual:
                    state.memory.open_questions.append(result.residual)
            if result.terminal in {
                TerminalState.SOLVED,
                TerminalState.REFUTED,
                TerminalState.OBSTRUCTED,
                TerminalState.FIXED,
                TerminalState.INFRA,
            }:
                break
        return state
