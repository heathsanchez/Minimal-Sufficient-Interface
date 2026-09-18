from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((str(k), _freeze(v)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0])))
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_freeze(v) for v in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(v) for v in value)
    if hasattr(value, '__dataclass_fields__'):
        return _plain(asdict(value))
    return value


@dataclass(frozen=True, order=True)
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
    protected_effect: tuple[Any, ...] | None = None
    acquisition_cost: int = 0
    state: str = 'ACTIVE'
    destination_status: dict[str, str] = field(default_factory=dict)
    dependencies: set[str] = field(default_factory=set)
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.state == 'ACTIVE'


@dataclass
class Residual:
    residual_id: str
    game: str
    kind: str
    estimated_cost: int
    potential_consequences: set[str]
    status: str = 'OPEN'
    demand_signature: tuple[Any, ...] | None = None
    authority_required: str = 'destination_exact'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Probe:
    probe_id: str
    game: str
    exact_context: str | None
    intervention: tuple[Any, ...]
    residuals_addressed: set[str]
    proposal_score: float
    expected_cost: int
    status: str = 'PENDING'
    cancellation_conditions: set[str] = field(default_factory=set)
    original_reason: str = ''
    cancellation_evidence: list[str] = field(default_factory=list)
    closure_event: str | None = None
    acquisition_actions_avoided: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlashEvent:
    event_id: str
    source_probe: str | None
    new_evidence: list[str] = field(default_factory=list)
    closure_iterations: int = 0
    capabilities_promoted: list[str] = field(default_factory=list)
    capabilities_revoked: list[str] = field(default_factory=list)
    quotients_created: list[str] = field(default_factory=list)
    quotients_split: list[str] = field(default_factory=list)
    routes_compiled: list[str] = field(default_factory=list)
    fatal_regions_added: list[str] = field(default_factory=list)
    transfer_proposals_created: list[str] = field(default_factory=list)
    transfer_proposals_verified: list[str] = field(default_factory=list)
    transfer_proposals_refuted: list[str] = field(default_factory=list)
    probes_cancelled: list[str] = field(default_factory=list)
    estimated_future_actions_eliminated: int = 0
    notes: dict[str, Any] = field(default_factory=dict)


class GlobalLedger:
    """Persistent abstraction layer. Raw exact evidence is referenced, never rewritten."""

    def __init__(self, games: Iterable[str] = ()) -> None:
        self.games = set(games)
        self.raw_evidence: dict[str, EvidenceRef] = {}
        self.capabilities: dict[str, GlobalCapability] = {}
        self.residuals: dict[str, Residual] = {}
        self.probes: dict[str, Probe] = {}
        self.events: list[FlashEvent] = []
        self.obstructions: dict[str, dict[str, Any]] = {}
        self.meta: dict[str, Any] = {}

    def add_evidence(self, ref: EvidenceRef) -> str:
        key = f'{ref.game}:{ref.kind}:{ref.artifact_or_run}:{ref.local_key}'
        old = self.raw_evidence.get(key)
        if old is not None and old != ref:
            raise ValueError(f'evidence identity collision: {key}')
        self.raw_evidence[key] = ref
        self.games.add(ref.game)
        return key

    def add_capability(self, cap: GlobalCapability) -> bool:
        old = self.capabilities.get(cap.capability_id)
        if old is None:
            self.capabilities[cap.capability_id] = cap
            self.games.update(cap.source_games)
            return True
        if self._cap_fingerprint(old) != self._cap_fingerprint(cap):
            raise ValueError(f'capability identity collision: {cap.capability_id}')
        return False

    def revoke_capability(self, capability_id: str, *, reason: str) -> bool:
        cap = self.capabilities[capability_id]
        if cap.state == 'REVOKED':
            return False
        cap.state = 'REVOKED'
        cap.notes = dict(cap.notes)
        cap.notes['revocation_reason'] = reason
        return True

    def add_residual(self, residual: Residual) -> bool:
        if residual.residual_id not in self.residuals:
            self.residuals[residual.residual_id] = residual
            self.games.add(residual.game)
            return True
        return False

    def add_probe(self, probe: Probe) -> bool:
        if probe.probe_id not in self.probes:
            self.probes[probe.probe_id] = probe
            self.games.add(probe.game)
            return True
        return False

    def cancel_probe(self, probe_id: str, *, evidence: str, event_id: str) -> int:
        probe = self.probes[probe_id]
        if probe.status != 'PENDING':
            return 0
        probe.status = 'CANCELLED'
        probe.cancellation_evidence.append(evidence)
        probe.closure_event = event_id
        probe.acquisition_actions_avoided = max(0, int(probe.expected_cost))
        return probe.acquisition_actions_avoided

    def active_capabilities(self) -> list[GlobalCapability]:
        return sorted((c for c in self.capabilities.values() if c.active), key=lambda c: c.capability_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            'schema': 'qckn-flash-ledger-v1',
            'games': sorted(self.games),
            'raw_evidence': {k: _plain(v) for k, v in sorted(self.raw_evidence.items())},
            'capabilities': {k: _plain(v) for k, v in sorted(self.capabilities.items())},
            'residuals': {k: _plain(v) for k, v in sorted(self.residuals.items())},
            'probes': {k: _plain(v) for k, v in sorted(self.probes.items())},
            'events': [_plain(v) for v in self.events],
            'obstructions': _plain(self.obstructions),
            'meta': _plain(self.meta),
        }

    def content_hash(self) -> str:
        payload = json.dumps(self.snapshot(), sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _cap_fingerprint(cap: GlobalCapability) -> tuple[Any, ...]:
        return (
            cap.kind,
            tuple(sorted(cap.source_games)),
            _freeze(cap.scope),
            _freeze(cap.consequence_signature),
            tuple(sorted(cap.exact_witnesses)),
            _freeze(cap.protected_effect),
            int(cap.acquisition_cost),
            tuple(sorted(cap.dependencies)),
        )

    def assert_provenance(self) -> None:
        evidence_values = set(self.raw_evidence.values())
        for cap in self.capabilities.values():
            if not cap.exact_witnesses:
                raise AssertionError(f'capability has no exact witness: {cap.capability_id}')
            missing = [ref for ref in cap.exact_witnesses if ref not in evidence_values]
            if missing:
                raise AssertionError(f'capability witness missing from evidence bank: {cap.capability_id}')
            missing_deps = sorted(dep for dep in cap.dependencies if dep not in self.capabilities)
            if missing_deps:
                raise AssertionError(f'missing capability dependency {cap.capability_id}: {missing_deps}')
