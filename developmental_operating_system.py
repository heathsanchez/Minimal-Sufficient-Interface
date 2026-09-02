"""Cumulative developmental operating system for verified recursive discovery.

Restores and operationalizes the original flowchart machinery around JOIN/REIFY:
Lawbook, Obstruction Atlas, Action Queue, installed-vs-active capabilities,
opportunistic wake-up, suppression, typed residual routing, live budget debiting,
developmental macros, and invariant guard.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import hashlib, json
from typing import Any

CONSTITUTION = (
    'external-verification', 'target-fidelity', 'provenance',
    'honest-terminal-states', 'bounded-resources'
)
RESIDUAL_TYPES = (
    'SEARCH', 'REPRESENTATION', 'OBSERVABLE', 'OPERATOR',
    'COMPOSITION', 'SCOPE', 'VERIFIER', 'DERIVATION', 'INFRA', 'UNKNOWN'
)

@dataclass(frozen=True)
class Law:
    id: str; statement: str; scope: str; activation: tuple[str, ...]
    dependencies: tuple[str, ...]; evidence: dict[str, Any]; cost: float = 1.0

@dataclass(frozen=True)
class Obstruction:
    id: str; route: str; reason: str; scope: str
    certificate: dict[str, Any]; rules_out: tuple[str, ...] = ()

@dataclass(frozen=True)
class Action:
    id: str; mode: str; question: str; trigger_ids: tuple[str, ...]
    expected_information: float; expected_upside: float; cost: float
    risk: float = 0.0; suppressed_by: tuple[str, ...] = ()
    residual_types: tuple[str, ...] = ()
    @property
    def utility(self) -> float:
        return (self.expected_information + self.expected_upside) / max(self.cost * (1.0 + self.risk), 1e-9)

@dataclass(frozen=True)
class Capability:
    id: str; scope: str; activation: tuple[str, ...]; cost: float; provenance: tuple[str, ...]

@dataclass(frozen=True)
class DevelopmentalMacro:
    id: str; pattern: tuple[str, ...]; consequence: str; support: tuple[str, ...]

@dataclass(frozen=True)
class LockState:
    problem: str; representation: str; installed_capabilities: tuple[str, ...]
    discovery_policy: str; verifier: str; budget: dict[str, float]
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
    residual_type: str = 'UNKNOWN'
    residual_type_scores: dict[str, int] = field(default_factory=dict)
    remaining_budget: dict[str, float] = field(default_factory=dict)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

class DevelopmentalOperatingSystem:
    def invariant_guard(self, state: DevelopmentalOSState) -> None:
        missing = set(CONSTITUTION) - set(state.lock.constitution)
        if missing: raise RuntimeError(f'constitutional invariant missing: {sorted(missing)}')
        if not state.target or not state.lock.verifier: raise RuntimeError('target/verifier must be frozen')
        if any(v < 0 for v in state.lock.budget.values()): raise RuntimeError('negative locked budget')
        if any(v < -1e-9 for v in state.remaining_budget.values()): raise RuntimeError('budget overspend')
        if state.residual_type not in RESIDUAL_TYPES: raise RuntimeError('unknown residual type')

    def classify_residual(self, residual: str) -> tuple[str, dict[str, int]]:
        """Deterministic, auditable residual typing. It is routing, not semantic proof."""
        text = residual.lower()
        lex = {
            'SEARCH': ('search','enumerate','try','candidate','find the smallest','explore'),
            'REPRESENTATION': ('representation','quotient','encode','state','signature','profile','phase','offset','distinction'),
            'OBSERVABLE': ('observe','observable','probe','measurement','separate','distinguish'),
            'OPERATOR': ('operator','operation','rule','transform','rewrite','action'),
            'COMPOSITION': ('compose','composition','chain','closure','transitive','cocycle'),
            'SCOPE': ('scope','finite','infinite','bound','domain','generalize'),
            'VERIFIER': ('verifier','proof-check','certificate','judge','replay'),
            'DERIVATION': ('prove','derive','theorem','lemma','symbolically','deduce','show that','equivalent','equivalence','from the laws','without exhaustive'),
            'INFRA': ('timeout','network','install','dependency','runner','infrastructure'),
        }
        scores = {k: sum(text.count(w) for w in words) for k, words in lex.items()}
        # DERIVATION is intentionally preferred on ties: once a representation has
        # already yielded an explicit theorem target, the controller should prove it
        # rather than re-enter representation search just because nouns like "phase"
        # or "representation" remain in the residual text.
        priority = {'DERIVATION': 0, 'VERIFIER': 1, 'INFRA': 2, 'REPRESENTATION': 3,
                    'OBSERVABLE': 4, 'COMPOSITION': 5, 'OPERATOR': 6, 'SCOPE': 7, 'SEARCH': 8}
        best = max(scores.items(), key=lambda kv: (kv[1], -priority[kv[0]]))
        return (best[0] if best[1] > 0 else 'UNKNOWN', scores)

    def ingest_verified_join_state(self, state: DevelopmentalOSState, join_state: dict[str, Any]) -> None:
        """A fact may be both a law and a boundary: truth and consequence are distinct axes."""
        for d in join_state.get('dots', []):
            kind, did, ev = d.get('kind', ''), d['id'], d.get('evidence', {})
            state.provenance_graph.append({'id': did, 'kind': kind, 'parents': d.get('parents', []), 'evidence': ev})
            if kind in {'verified-success','promoted-concept','verified-low-leverage','verified-frontier'}:
                state.lawbook.append(Law('law:'+did, d['statement'], 'current-task', tuple(d.get('tags',())), tuple(d.get('parents',())), ev))
            if kind in {'verified-failure','counterexample','obstruction','rejected-join'}:
                state.obstruction_atlas.append(Obstruction('obs:'+did, d['statement'], str(ev.get('reason', ev.get('verification','verified negative evidence'))), 'current-task', ev, tuple(d.get('tags',()))))
            elif kind == 'verified-low-leverage':
                state.obstruction_atlas.append(Obstruction('obs:low-leverage:'+did, d['statement'], 'verified true but non-consequential under the current residual', 'process-route', ev, ('repeat-low-leverage-route',)))
            elif kind == 'verified-frontier':
                state.obstruction_atlas.append(Obstruction('obs:frontier:'+did, d['statement'], 'verified frontier remains nonempty under the current route', 'current-representation', ev, ('coarse-frontier-only',)))
        for i, rej in enumerate(join_state.get('rejected', [])):
            state.obstruction_atlas.append(Obstruction(
                f'obs:join-rejection:{i}', rej.get('candidate',{}).get('relation','JOIN candidate'),
                rej.get('reason', rej.get('test',{}).get('reason','failed promotion gate')),
                'JOIN/reification', rej, (rej.get('candidate',{}).get('strategy','unknown-strategy'),)
            ))
        for p in join_state.get('promoted', []):
            r=p['reification']; cid='cap:'+r['name']
            if cid not in {c.id for c in state.installed_capabilities}:
                state.installed_capabilities.append(Capability(cid,'current-task',(r['object_type'],),1.0,tuple(p['candidate'].get('dot_ids',()))))
        state.residual = join_state.get('residual', state.residual)
        state.residual_type, state.residual_type_scores = self.classify_residual(state.residual)

    def suppress_dominated_actions(self, state: DevelopmentalOSState) -> None:
        ruled={x for o in state.obstruction_atlas for x in o.rules_out}
        state.action_queue=[a for a in state.action_queue if not (set(a.suppressed_by) | (set(a.trigger_ids)&ruled))]

    def wake_actions(self, state: DevelopmentalOSState) -> None:
        kinds={p['kind'] for p in state.provenance_graph}; triggers=tuple(p['id'] for p in state.provenance_graph[-8:])
        candidates=[
            Action('act:push','PUSH','Push the strongest currently active capability against the residual.',triggers,1.0,2.0,1.0,residual_types=('SEARCH','OPERATOR','COMPOSITION')),
            Action('act:discriminate','PROBE','Find the cheapest observation separating the live residual explanations.',triggers,3.0,1.0,1.0,residual_types=('OBSERVABLE','REPRESENTATION','UNKNOWN')),
        ]
        if state.residual_type == 'REPRESENTATION':
            candidates.append(Action('act:reframe','REFRAME','Construct the smallest representation change demanded by the certified residual.',triggers,3.5,3.5,1.4,residual_types=('REPRESENTATION',)))
        if state.residual_type == 'DERIVATION':
            candidates.append(Action('act:derive','DERIVE','Derive the target statement from the retained verified laws, isolate the smallest lemmas, and independently verify each implication before synthesis.',triggers,4.0,4.0,1.2,residual_types=('DERIVATION',)))
        if len(state.obstruction_atlas)>=2:
            candidates.append(Action('act:negative-join','JOIN','Join verified failures/boundaries to extract the common obstruction.',triggers,2.5,2.0,1.2,residual_types=('REPRESENTATION','SEARCH','UNKNOWN')))
        if 'verified-success' in kinds and state.obstruction_atlas:
            candidates.append(Action('act:contrast-join','JOIN','Join near-matched successes and failures/boundaries to isolate the smallest consequential distinction.',triggers,3.0,3.0,1.3,residual_types=('REPRESENTATION','OBSERVABLE','UNKNOWN')))
        if 'trajectory' in kinds:
            candidates.append(Action('act:trajectory','JOIN','Compress repeated residual transitions into a developmental macro.',triggers,2.0,2.5,1.0,residual_types=('REPRESENTATION','SEARCH','UNKNOWN')))
        existing={a.id for a in state.action_queue}; state.action_queue.extend(a for a in candidates if a.id not in existing)
        def routed_utility(a: Action) -> float:
            bonus = 1.35 if state.residual_type in a.residual_types else 1.0
            return a.utility * bonus
        state.action_queue.sort(key=lambda a:(-routed_utility(a),a.id))

    def activate_minimal(self, state: DevelopmentalOSState) -> None:
        words={w.lower().strip('.,:;()[]') for w in state.residual.split() if len(w)>3}
        ranked=[]
        for c in state.installed_capabilities:
            hay=(' '.join(c.activation)+' '+c.scope+' '+c.id).lower()
            ranked.append((sum(w in hay for w in words), -c.cost, c.id))
        ranked.sort(reverse=True)
        if not ranked: state.active_capabilities=[]; return
        best=ranked[0][0]; tier=[x[2] for x in ranked if x[0]==best]
        state.active_capabilities=tier[:2] if tier else [ranked[0][2]]

    def _init_budget(self, state: DevelopmentalOSState) -> None:
        if not state.remaining_budget:
            state.remaining_budget = dict(state.lock.budget)

    def action_feasible(self, state: DevelopmentalOSState, action: Action) -> bool:
        self._init_budget(state)
        if state.remaining_budget.get('search_steps', float('inf')) < 1.0: return False
        if action.mode in {'REFRAME','JOIN','META','DERIVE'} and state.remaining_budget.get('model_calls', float('inf')) < 1.0: return False
        return True

    def select_and_debit_next_action(self, state: DevelopmentalOSState) -> Action | None:
        """Selects the highest-ranked feasible action and immediately accounts for its resource use."""
        self._init_budget(state)
        for action in state.action_queue:
            if not self.action_feasible(state, action):
                continue
            if 'search_steps' in state.remaining_budget: state.remaining_budget['search_steps'] -= 1.0
            if action.mode in {'REFRAME','JOIN','META','DERIVE'} and 'model_calls' in state.remaining_budget:
                state.remaining_budget['model_calls'] -= 1.0
            state.action_history.append({'action_id': action.id, 'mode': action.mode, 'residual_type': state.residual_type, 'charged': True})
            self.invariant_guard(state)
            return action
        return None

    def learn_macros(self, state: DevelopmentalOSState) -> None:
        trajectories=[p for p in state.provenance_graph if p['kind']=='trajectory']
        if len(trajectories)>=2:
            state.macros.append(DevelopmentalMacro('macro:residual-driven-representation-escalation',('verified residual','retrieve evidence','JOIN','reify','verify'),'Use repeated residual->representation transitions as a reusable developmental procedure.',tuple(p['id'] for p in trajectories)))

    def diagnose_process(self, state: DevelopmentalOSState) -> None:
        if not state.obstruction_atlas: state.process_residuals.append('Obstruction Atlas empty: negative evidence is not yet feeding suppression or F+F joins.')
        if not state.action_queue: state.process_residuals.append('Action Queue empty: newly verified evidence is not waking future work.')
        if state.installed_capabilities and not state.active_capabilities: state.process_residuals.append('Installed capabilities exist but no minimal active subset was selected.')
        if len(state.installed_capabilities)>1 and len(state.active_capabilities)>=len(state.installed_capabilities): state.process_residuals.append('Active set is not minimized relative to installed capability set.')
        if state.residual_type == 'UNKNOWN': state.process_residuals.append('Residual could not be typed; controller lacks a verified routing distinction.')

    def cycle(self, state: DevelopmentalOSState, join_state: dict[str, Any]) -> DevelopmentalOSState:
        self._init_budget(state)
        self.invariant_guard(state)
        self.ingest_verified_join_state(state, join_state)
        self.wake_actions(state)
        self.suppress_dominated_actions(state)
        self.activate_minimal(state)
        self.learn_macros(state)
        self.diagnose_process(state)
        self.invariant_guard(state)
        return state
