"""Cumulative developmental operating system for verified recursive discovery.

Restores the original flowchart machinery around the JOIN/REIFY core:
Lawbook, Obstruction Atlas, Action Queue, installed-vs-active capabilities,
opportunistic wake-up, suppression, developmental macros, and invariant guard.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import hashlib, json
from typing import Any, Iterable

CONSTITUTION = (
    'external-verification', 'target-fidelity', 'provenance',
    'honest-terminal-states', 'bounded-resources'
)

@dataclass(frozen=True)
class Law:
    id: str
    statement: str
    scope: str
    activation: tuple[str, ...]
    dependencies: tuple[str, ...]
    evidence: dict[str, Any]
    cost: float = 1.0

@dataclass(frozen=True)
class Obstruction:
    id: str
    route: str
    reason: str
    scope: str
    certificate: dict[str, Any]
    rules_out: tuple[str, ...] = ()

@dataclass(frozen=True)
class Action:
    id: str
    mode: str
    question: str
    trigger_ids: tuple[str, ...]
    expected_information: float
    expected_upside: float
    cost: float
    risk: float = 0.0
    suppressed_by: tuple[str, ...] = ()

    @property
    def utility(self) -> float:
        return (self.expected_information + self.expected_upside) / max(self.cost * (1.0 + self.risk), 1e-9)

@dataclass(frozen=True)
class Capability:
    id: str
    scope: str
    activation: tuple[str, ...]
    cost: float
    provenance: tuple[str, ...]

@dataclass(frozen=True)
class DevelopmentalMacro:
    id: str
    pattern: tuple[str, ...]
    consequence: str
    support: tuple[str, ...]

@dataclass(frozen=True)
class LockState:
    problem: str
    representation: str
    installed_capabilities: tuple[str, ...]
    discovery_policy: str
    verifier: str
    budget: dict[str, float]
    constitution: tuple[str, ...] = CONSTITUTION

@dataclass
class DevelopmentalOSState:
    target: str
    residual: str
    lock: LockState
    lawbook: list[Law] = field(default_factory=list)
    obstruction_atlas: list[Obstruction] = field(default_factory=list)
    action_queue: list[Action] = field(default_factory=list)
    installed_capabilities: list[Capability] = field(default_factory=list)
    active_capabilities: list[str] = field(default_factory=list)
    macros: list[DevelopmentalMacro] = field(default_factory=list)
    provenance_graph: list[dict[str, Any]] = field(default_factory=list)
    process_residuals: list[str] = field(default_factory=list)

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

class DevelopmentalOperatingSystem:
    def invariant_guard(self, state: DevelopmentalOSState) -> None:
        missing = set(CONSTITUTION) - set(state.lock.constitution)
        if missing:
            raise RuntimeError(f'constitutional invariant missing: {sorted(missing)}')
        if not state.target or not state.lock.verifier:
            raise RuntimeError('target/verifier must be frozen')
        if any(v < 0 for v in state.lock.budget.values()):
            raise RuntimeError('negative budget')

    def ingest_verified_join_state(self, state: DevelopmentalOSState, join_state: dict[str, Any]) -> None:
        """Compile successes AND failures into different persistent stores."""
        for d in join_state.get('dots', []):
            kind = d.get('kind', '')
            did = d['id']
            state.provenance_graph.append({'id': did, 'kind': kind, 'parents': d.get('parents', []), 'evidence': d.get('evidence', {})})
            if kind in {'verified-success', 'promoted-concept', 'verified-low-leverage', 'verified-frontier'}:
                state.lawbook.append(Law(
                    id='law:' + did, statement=d['statement'], scope='current-task',
                    activation=tuple(d.get('tags', ())), dependencies=tuple(d.get('parents', ())), evidence=d.get('evidence', {})
                ))
            if kind in {'verified-failure', 'counterexample', 'obstruction', 'rejected-join'}:
                ev = d.get('evidence', {})
                state.obstruction_atlas.append(Obstruction(
                    id='obs:' + did, route=d['statement'], reason=str(ev.get('reason', ev.get('verification', 'verified negative evidence'))),
                    scope='current-task', certificate=ev, rules_out=tuple(d.get('tags', ()))
                ))
        for i, rej in enumerate(join_state.get('rejected', [])):
            state.obstruction_atlas.append(Obstruction(
                id=f'obs:join-rejection:{i}', route=rej.get('candidate', {}).get('relation', 'JOIN candidate'),
                reason=rej.get('reason', rej.get('test', {}).get('reason', 'failed promotion gate')),
                scope='JOIN/reification', certificate=rej,
                rules_out=(rej.get('candidate', {}).get('strategy', 'unknown-strategy'),)
            ))
        for p in join_state.get('promoted', []):
            r = p['reification']
            cid = 'cap:' + r['name']
            if cid not in {c.id for c in state.installed_capabilities}:
                state.installed_capabilities.append(Capability(
                    id=cid, scope='current-task', activation=(r['object_type'],), cost=1.0,
                    provenance=tuple(p['candidate'].get('dot_ids', ()))
                ))
        state.residual = join_state.get('residual', state.residual)

    def suppress_dominated_actions(self, state: DevelopmentalOSState) -> None:
        ruled = {x for o in state.obstruction_atlas for x in o.rules_out}
        out = []
        for a in state.action_queue:
            hits = tuple(sorted(set(a.suppressed_by) | (set(a.trigger_ids) & ruled)))
            if hits:
                continue
            out.append(a)
        state.action_queue = out

    def wake_actions(self, state: DevelopmentalOSState) -> None:
        """Opportunistically wake actions from the present residual and evidence mix."""
        kinds = {p['kind'] for p in state.provenance_graph}
        triggers = tuple(p['id'] for p in state.provenance_graph[-8:])
        candidates = [
            Action('act:push', 'PUSH', 'Push the strongest currently installed capability against the residual.', triggers, 1.0, 2.0, 1.0),
            Action('act:discriminate', 'PROBE', 'Find the cheapest observation separating the live residual explanations.', triggers, 3.0, 1.0, 1.0),
        ]
        if 'verified-failure' in kinds or state.obstruction_atlas:
            candidates.append(Action('act:negative-join', 'JOIN', 'Join verified failures/counterexamples to extract the common obstruction.', triggers, 2.5, 2.0, 1.2))
        if 'verified-success' in kinds and ('verified-failure' in kinds or state.obstruction_atlas):
            candidates.append(Action('act:contrast-join', 'JOIN', 'Join near-matched successes and failures to isolate the smallest consequential distinction.', triggers, 3.0, 3.0, 1.3))
        if any(p['kind'] == 'trajectory' for p in state.provenance_graph):
            candidates.append(Action('act:trajectory', 'JOIN', 'Compress repeated residual transitions into a developmental macro.', triggers, 2.0, 2.5, 1.0))
        existing = {a.id for a in state.action_queue}
        state.action_queue.extend(a for a in candidates if a.id not in existing)
        state.action_queue.sort(key=lambda a: (-a.utility, a.id))

    def activate_minimal(self, state: DevelopmentalOSState) -> None:
        """Activate the cheapest sufficient-looking subset; installed != active."""
        words = {w.lower().strip('.,:;()[]') for w in state.residual.split() if len(w) > 3}
        ranked = []
        for c in state.installed_capabilities:
            hay = (' '.join(c.activation) + ' ' + c.scope).lower()
            relevance = sum(w in hay for w in words)
            ranked.append((relevance, -c.cost, c.id))
        ranked.sort(reverse=True)
        state.active_capabilities = [x[2] for x in ranked[:max(1, min(3, len(ranked)))]] if ranked else []

    def learn_macros(self, state: DevelopmentalOSState) -> None:
        trajectories = [p for p in state.provenance_graph if p['kind'] == 'trajectory']
        if len(trajectories) >= 2:
            ids = tuple(p['id'] for p in trajectories)
            state.macros.append(DevelopmentalMacro(
                id='macro:residual-driven-representation-escalation',
                pattern=('verified residual', 'retrieve evidence', 'JOIN', 'reify', 'verify'),
                consequence='Use repeated residual->representation transitions as a reusable developmental procedure.',
                support=ids,
            ))

    def diagnose_process(self, state: DevelopmentalOSState) -> None:
        if not state.obstruction_atlas:
            state.process_residuals.append('Obstruction Atlas empty: negative evidence is not yet feeding suppression or F+F joins.')
        if not state.action_queue:
            state.process_residuals.append('Action Queue empty: newly verified evidence is not waking future work.')
        if state.installed_capabilities and not state.active_capabilities:
            state.process_residuals.append('Installed capabilities exist but no minimal active subset was selected.')
        if len(state.installed_capabilities) > 3 and len(state.active_capabilities) >= len(state.installed_capabilities):
            state.process_residuals.append('Active set is not minimized relative to installed capability set.')

    def cycle(self, state: DevelopmentalOSState, join_state: dict[str, Any]) -> DevelopmentalOSState:
        self.invariant_guard(state)
        self.ingest_verified_join_state(state, join_state)
        self.wake_actions(state)
        self.suppress_dominated_actions(state)
        self.activate_minimal(state)
        self.learn_macros(state)
        self.diagnose_process(state)
        self.invariant_guard(state)
        return state
