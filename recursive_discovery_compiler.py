"""Verified recursive discovery compiler.

The global controller owns target, residuals, synthesis and stopping. Workers receive
only a local packet; they cannot see the global target unless the packet includes it.
Verifier and consequence gates are separate: true-but-useless results need not be
promoted into active search state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class BlindPacket:
    id: str
    question: str
    facts: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    forbidden_context: tuple[str, ...] = ()
    verifier_id: str = ""
    role: str = "analysis"

    def public_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "question": self.question,
            "facts": list(self.facts),
            "constraints": list(self.constraints),
            "verifier_id": self.verifier_id,
        }


@dataclass(frozen=True)
class WorkerResult:
    packet_id: str
    answer: dict[str, Any]
    claims: tuple[str, ...]


@dataclass(frozen=True)
class VerificationResult:
    accepted: bool
    evidence: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class ConsequenceResult:
    consequential: bool
    score: int
    consequence: str
    next_residual: str


@dataclass
class KnowledgeState:
    global_target: str
    verified: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    low_leverage: list[dict[str, Any]] = field(default_factory=list)
    residuals: list[str] = field(default_factory=list)
    graph: list[dict[str, Any]] = field(default_factory=list)
    generations: list[dict[str, Any]] = field(default_factory=list)
    terminal: str = "UNKNOWN"

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data["state_sha256"] = self.digest()
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


Worker = Callable[[dict[str, Any]], WorkerResult]
Verifier = Callable[[BlindPacket, WorkerResult], VerificationResult]
ConsequenceGate = Callable[[KnowledgeState, BlindPacket, WorkerResult, VerificationResult], ConsequenceResult]
QuestionPolicy = Callable[[KnowledgeState], BlindPacket | None]


class RecursiveDiscoveryCompiler:
    def __init__(
        self,
        worker: Worker,
        verifiers: dict[str, Verifier],
        consequence_gate: ConsequenceGate,
        question_policy: QuestionPolicy,
        max_generations: int = 8,
    ) -> None:
        self.worker = worker
        self.verifiers = verifiers
        self.consequence_gate = consequence_gate
        self.question_policy = question_policy
        self.max_generations = max_generations

    def run(self, state: KnowledgeState) -> KnowledgeState:
        for generation in range(self.max_generations):
            if state.terminal != "UNKNOWN":
                break
            packet = self.question_policy(state)
            if packet is None:
                break
            worker_input = packet.public_view()
            serialized = json.dumps(worker_input)
            leaked = [token for token in packet.forbidden_context if token and token in serialized]
            if leaked:
                raise RuntimeError(f"context firewall failure: {sorted(leaked)}")
            result = self.worker(worker_input)
            if result.packet_id != packet.id:
                raise RuntimeError("worker returned result for wrong packet")
            verifier = self.verifiers[packet.verifier_id]
            checked = verifier(packet, result)
            event: dict[str, Any] = {
                "generation": generation,
                "packet": worker_input,
                "worker": asdict(result),
                "verification": asdict(checked),
            }
            if not checked.accepted:
                state.rejected.append(event)
                state.residuals.append(f"Rejected local result {packet.id}: {checked.reason}")
                state.generations.append(event)
                continue
            consequence = self.consequence_gate(state, packet, result, checked)
            event["consequence"] = asdict(consequence)
            event["event_sha256"] = hashlib.sha256(
                json.dumps(event, sort_keys=True).encode()
            ).hexdigest()
            if consequence.consequential:
                state.verified.append(event)
                state.graph.append({
                    "from": packet.id,
                    "to": consequence.next_residual,
                    "relation": consequence.consequence,
                })
            else:
                state.low_leverage.append(event)
            state.residuals.append(consequence.next_residual)
            state.generations.append(event)
        return state
