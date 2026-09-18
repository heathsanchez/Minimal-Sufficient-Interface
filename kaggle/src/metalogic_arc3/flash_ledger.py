
from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from hashlib import sha256
import json
from typing import Any, Iterable

ACTIVE = "ACTIVE"
RESERVE = "RESERVE"
REVOKED = "REVOKED"
PENDING = "PENDING"
EXECUTED = "EXECUTED"
CANCELLED = "CANCELLED"
SETTLED = "SETTLED"
OPEN = "OPEN"


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (set, frozenset)):
        return [_plain(v) for v in sorted(value, key=lambda x: json.dumps(_plain(x), sort_keys=True))]
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_id(prefix: str, payload: Any) -> str:
    return f"{prefix}-{sha256(canonical_json(payload).encode()).hexdigest()[:20]}"


@dataclass(frozen=True)
class EvidenceRef:
    game: str
    kind: str
    artifact_or_run: str
    local_key: str
    sha256: str | None = None


@dataclass
class GlobalCapability:
    capability_id: str
    kind: str
    source_games: set[str]
    scope: dict[str, Any]
    consequence_signature: tuple[Any, ...]
    exact_witnesses: list[EvidenceRef]
    protected_effect: tuple[Any, ...] | None
    acquisition_cost: int
    authority: str
    destination_status: dict[str, str] = field(default_factory=dict)
    state: str = ACTIVE
    dependencies: set[str] = field(default_factory=set)
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Residual:
    residual_id: str
    game: str
    kind: str
    estimated_cost: int
    potential_consequences: set[str]
    status: str = OPEN
    settled_by: str | None = None
    demand_key: str | None = None


@dataclass
class Probe:
    probe_id: str
    game: str
    exact_context: str | None
    intervention: tuple[Any, ...]
    residuals_addressed: set[str]
    proposal_score: float
    expected_cost: int
    status: str = PENDING
    original_reason: str = ""
    cancellation_conditions: set[str] = field(default_factory=set)
    cancellation_event: str | None = None
    cancellation_evidence: list[str] = field(default_factory=list)
    acquisition_actions_avoided: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlashEvent:
    event_id: str
    source_probe: str | None
    new_evidence: list[str] = field(default_factory=list)
    closure_iterations: int = 0
    capabilities_promoted: list[str] = field(default_factory=list)
    capabilities_reserved: list[str] = field(default_factory=list)
    capabilities_revoked: list[str] = field(default_factory=list)
    quotients_created: list[str] = field(default_factory=list)
    quotients_split: list[str] = field(default_factory=list)
    routes_compiled: list[str] = field(default_factory=list)
    fatal_regions_added: list[str] = field(default_factory=list)
    transfer_proposals_created: list[str] = field(default_factory=list)
    transfer_proposals_verified: list[str] = field(default_factory=list)
    transfer_proposals_refuted: list[str] = field(default_factory=list)
    probes_cancelled: list[str] = field(default_factory=list)
    residuals_settled: list[str] = field(default_factory=list)
    estimated_future_actions_eliminated: int = 0
    active_capabilities_before: int = 0
    active_capabilities_after: int = 0
    notes: dict[str, Any] = field(default_factory=dict)


class FlashLedger:
    """Persistent global developmental state.

    Raw evidence references are immutable values. Global abstractions can be
    promoted/reserved/revoked, but they cannot mutate the local verifier or the
    referenced exact evidence.
    """

    schema = "qckn-flash-ledger-v1"

    def __init__(self) -> None:
        self.games: set[str] = set()
        self.raw_evidence: dict[str, EvidenceRef] = {}
        self.capabilities: dict[str, GlobalCapability] = {}
        self.residuals: dict[str, Residual] = {}
        self.probes: dict[str, Probe] = {}
        self.events: list[FlashEvent] = []
        self.provenance: dict[str, set[str]] = {}

    def add_game(self, game: str) -> None:
        self.games.add(game)

    def add_evidence(self, ref: EvidenceRef) -> str:
        evidence_id = stable_id("ev", ref)
        prior = self.raw_evidence.get(evidence_id)
        if prior is not None and prior != ref:
            raise AssertionError("immutable evidence id collision")
        self.raw_evidence[evidence_id] = ref
        self.games.add(ref.game)
        return evidence_id

    def add_capability(self, cap: GlobalCapability) -> None:
        if cap.capability_id in self.capabilities:
            prior = self.capabilities[cap.capability_id]
            if canonical_json(prior) != canonical_json(cap):
                raise AssertionError(f"capability id collision: {cap.capability_id}")
            return
        for witness in cap.exact_witnesses:
            eid = stable_id("ev", witness)
            if self.raw_evidence.get(eid) != witness:
                raise AssertionError(f"capability witness absent from raw evidence: {eid}")
        missing = cap.dependencies - set(self.capabilities)
        if missing:
            raise AssertionError(f"missing capability dependencies: {sorted(missing)}")
        self.capabilities[cap.capability_id] = cap
        self.games.update(cap.source_games)
        self.provenance[cap.capability_id] = {
            stable_id("ev", witness) for witness in cap.exact_witnesses
        } | set(cap.dependencies)

    def add_residual(self, residual: Residual) -> None:
        prior = self.residuals.get(residual.residual_id)
        if prior is not None and canonical_json(prior) != canonical_json(residual):
            raise AssertionError(f"residual id collision: {residual.residual_id}")
        self.residuals[residual.residual_id] = residual
        self.games.add(residual.game)

    def add_probe(self, probe: Probe) -> None:
        prior = self.probes.get(probe.probe_id)
        if prior is not None and canonical_json(prior) != canonical_json(probe):
            raise AssertionError(f"probe id collision: {probe.probe_id}")
        missing = probe.residuals_addressed - set(self.residuals)
        if missing:
            raise AssertionError(f"probe references unknown residuals: {sorted(missing)}")
        self.probes[probe.probe_id] = probe
        self.games.add(probe.game)

    def reserve_capability(self, capability_id: str) -> bool:
        cap = self.capabilities[capability_id]
        if cap.state != ACTIVE:
            return False
        cap.state = RESERVE
        return True

    def revoke_capability(self, capability_id: str) -> bool:
        cap = self.capabilities[capability_id]
        if cap.state == REVOKED:
            return False
        cap.state = REVOKED
        return True

    def settle_residual(self, residual_id: str, capability_id: str) -> bool:
        residual = self.residuals[residual_id]
        if residual.status == SETTLED and residual.settled_by == capability_id:
            return False
        residual.status = SETTLED
        residual.settled_by = capability_id
        return True

    def cancel_probe(
        self,
        probe_id: str,
        *,
        event_id: str,
        evidence_ids: Iterable[str],
        avoided_actions: int | None = None,
    ) -> bool:
        probe = self.probes[probe_id]
        if probe.status != PENDING:
            return False
        probe.status = CANCELLED
        probe.cancellation_event = event_id
        probe.cancellation_evidence = sorted(set(evidence_ids))
        probe.acquisition_actions_avoided = (
            int(probe.expected_cost) if avoided_actions is None else int(avoided_actions)
        )
        return True

    def mark_probe_executed(self, probe_id: str) -> None:
        probe = self.probes[probe_id]
        if probe.status != PENDING:
            raise AssertionError(f"probe not pending: {probe_id}")
        probe.status = EXECUTED

    def active_capability_ids(self) -> list[str]:
        return sorted(
            cid for cid, cap in self.capabilities.items() if cap.state == ACTIVE
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "games": sorted(self.games),
            "raw_evidence": {k: _plain(v) for k, v in sorted(self.raw_evidence.items())},
            "capabilities": {k: _plain(v) for k, v in sorted(self.capabilities.items())},
            "residuals": {k: _plain(v) for k, v in sorted(self.residuals.items())},
            "probes": {k: _plain(v) for k, v in sorted(self.probes.items())},
            "events": [_plain(v) for v in self.events],
            "provenance": {k: sorted(v) for k, v in sorted(self.provenance.items())},
        }

    def content_hash(self) -> str:
        return sha256(canonical_json(self.to_dict()).encode()).hexdigest()

    def write(self, path: str | Any) -> None:
        from pathlib import Path
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")
