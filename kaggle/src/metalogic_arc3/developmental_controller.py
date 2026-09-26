"""Live observed-continuation compilation, refinement and guarded execution.

The imported core is an exact pinned dependency slice, not a second kernel.
WARRANTED applies only to logged observations. Planning is CANDIDATE: finite
observational agreement cannot establish complete dynamics or safe exploration.
Every proposed next observation is checked; a separator earns history refinement.
No game name, solved action sequence, pixel reward, or hidden state is consulted.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
from typing import Any

from .continuation_core import (
    ContinuationStatus, ProtectedContinuation, ProtectedContinuationMachine,
    canonical_bytes, content_id,
)
from .memory_controller import MemoryGraphController
from .runtime import ActionToken, Observation, normalize_frame


@dataclass(frozen=True)
class ProgressDecision:
    action: ActionToken
    rank: int
    support_refs: tuple[str, ...]
    expected_targets: tuple[str, ...]
    status: str = 'CANDIDATE'


class ProgressMemory:
    """Bounded observed transition algebra with counterexample-driven state.

    Historical records, refusals and support revocations survive reset. The
    finite planner regresses from actual progress using exists-action/for-all-
    observed-outcomes ranks. Unobserved outcomes remain outside its guarantee.
    """

    SCHEMA = 'arc.live-observed-continuations@1'

    def __init__(self, max_history: int = 8) -> None:
        if max_history < 1:
            raise ValueError('max_history must be positive')
        self.max_history = int(max_history)
        self.history_depth = 0
        self.records: list[dict[str, Any]] = []
        self.revoked: dict[str, str] = {}
        self.residuals: list[dict[str, Any]] = []
        self.last_residual: dict[str, Any] | None = None
        self.stats = dict(decisions=0, observed_progress=0, matched_predictions=0,
                          prediction_mismatches=0, refinements=0, closure_builds=0)
        self._record_ids: set[str] = set()
        self._history: tuple = ()
        self._current: Observation | None = None
        self._pending: ProgressDecision | None = None
        self._compiled = None
        self._policies: dict[int, Any] = {}

    @staticmethod
    def _obs_data(obs: Observation) -> dict[str, Any]:
        return asdict(obs)

    @staticmethod
    def _action(action: ActionToken) -> tuple:
        return action.action_id, action.x, action.y

    def _next_history(self, before: Observation, action: ActionToken) -> tuple:
        return (self._history + ((before.frame_digest, self._action(action)),))[-self.max_history:]

    def begin(self, obs: Observation) -> None:
        self._history = ()
        self._current = obs
        self._pending = None

    def state_id(self, obs: Observation, history: tuple) -> str:
        return self._state_id(self._obs_data(obs), history, self.history_depth)

    @staticmethod
    def _state_id(obs: dict[str, Any], history: tuple | list, depth: int) -> str:
        # The queried action is never in a state. Past actions enter only when
        # an observed future separator requires them. Both endpoints use q.
        suffix = history[-depth:] if depth else ()
        return content_id((obs, suffix), prefix='arc-state')

    def _residual(self, reason: str, **details: Any) -> None:
        item = dict(status='UNKNOWN', reason=reason, **details)
        self.last_residual = item
        if item not in self.residuals:
            self.residuals.append(item)

    def _invalidate(self) -> None:
        self._compiled = None
        self._policies.clear()

    def observe(self, before: Observation, action: ActionToken, after: Observation) -> None:
        if self._current is None:
            self.begin(before)
        if self._current != before:
            raise ValueError('nonchronological observation; declare reset with begin')
        if action.action_id not in before.available_actions:
            raise ValueError('observed action is not in the exposed legal interface')
        if action.action_id == 6 and (action.x is None or action.y is None or
                not 0 <= action.x < before.width or not 0 <= action.y < before.height):
            raise ValueError('complex action coordinates outside exposed board')
        next_history = self._next_history(before, action)
        expected = self._pending
        if expected is not None and self._action(expected.action) == self._action(action):
            actual = self.state_id(after, next_history)
            if actual in expected.expected_targets:
                self.stats['matched_predictions'] += 1
            else:
                self.stats['prediction_mismatches'] += 1
                self._residual('live_continuation_separator',
                               source=self.state_id(before, self._history),
                               action=list(self._action(action)), actual=actual,
                               predicted=list(expected.expected_targets))
        self._pending = None
        record = dict(before=self._obs_data(before), after=self._obs_data(after),
                      action=self._action(action), history=self._history,
                      next_history=next_history, cost=1)
        evidence = content_id(record, prefix='arc-observation')
        if evidence not in self._record_ids:
            record['evidence'] = evidence
            self.records.append(record)
            self._record_ids.add(evidence)
            self._invalidate()
            self._refine()
        if after.levels_completed > before.levels_completed or (
                after.state == 'WIN' and before.state != 'WIN'):
            self.stats['observed_progress'] += 1
        self._history = next_history
        self._current = after

    def _conflicts(self, depth: int) -> set[tuple[str, str]]:
        predictions: dict[tuple[str, str], set[str]] = {}
        for row in self.records:
            if row['evidence'] in self.revoked:
                continue
            key = (self._state_id(row['before'], row['history'], depth),
                   json.dumps(row['action']))
            target = self._state_id(row['after'], row['next_history'], depth)
            predictions.setdefault(key, set()).add(target)
        return {key for key, targets in predictions.items() if len(targets) > 1}

    def _refine(self) -> None:
        conflicts = self._conflicts(self.history_depth)
        if not conflicts:
            return
        old = self.history_depth
        for depth in range(old + 1, self.max_history + 1):
            if not self._conflicts(depth):
                self.history_depth = depth
                self.stats['refinements'] += 1
                self._residual('history_separator_admitted', previous_depth=old,
                               history_depth=depth, conflicting_queries=len(conflicts))
                self._invalidate()
                return
        # Do not certify a complete model when the supplied history language
        # cannot separate it. The planner must respect all observed branches.
        self._residual('history_language_exhausted', history_bound=self.max_history,
                       conflicting_queries=len(conflicts))

    def revoke(self, support_ref: str, *, reason: str) -> None:
        if support_ref not in self._record_ids:
            raise KeyError(support_ref)
        if not reason:
            raise ValueError('revocation needs a reason')
        self.revoked[support_ref] = reason
        self._pending = None
        self._invalidate()

    def _compile(self):
        if self._compiled is not None:
            return self._compiled
        states = {}
        edges = []
        actions = {}
        for row in self.records:
            src = self._state_id(row['before'], row['history'], self.history_depth)
            dst = self._state_id(row['after'], row['next_history'], self.history_depth)
            states[src], states[dst] = row['before'], row['after']
            label = 'arc.observed-step@1:' + json.dumps(row['action'], separators=(',', ':'))
            actions[label] = tuple(row['action'])
            # Each edge warrants occurrence in the logged finite sample only.
            # Planning/transport of it is separately and explicitly CANDIDATE.
            edge = ProtectedContinuation(
                src, label,
                (row['after']['state'], str(row['after']['levels_completed']), 'cost=1'),
                ContinuationStatus.WARRANTED, dst,
                support_refs=(row['evidence'],), evidence_refs=(row['evidence'],))
            edges.append(edge)
        machine = ProtectedContinuationMachine(
            'arc:historical-observations-only@1', tuple(states), tuple(edges))
        live = self._record_ids - self.revoked.keys()
        groups = {}
        for edge in machine.continuations:
            if edge.is_live(live):
                groups.setdefault((edge.source, edge.continuation), []).append(edge)
        self._compiled = machine, states, groups, actions
        self.stats['closure_builds'] += 1
        return self._compiled

    def machine(self) -> ProtectedContinuationMachine:
        return self._compile()[0]

    def _policy(self, level: int):
        if level in self._policies:
            return self._policies[level]
        _machine, states, groups, actions = self._compile()
        rank = {s: 0 for s, obs in states.items()
                if obs['state'] != 'GAME_OVER' and
                (obs['levels_completed'] > level or obs['state'] == 'WIN')}
        policy = {}
        # Least fixed point: mere cycles, survival, and unknown exits never
        # become goals. Every selected edge decreases this finite-model rank.
        for _ in range(len(states)):
            changed = False
            for (src, label), edges in sorted(groups.items()):
                if states[src]['state'] in ('WIN', 'GAME_OVER') or rank.get(src) == 0:
                    continue
                targets = {e.target for e in edges}
                if not all(t in rank for t in targets):
                    continue
                candidate_rank = 1 + max(rank[t] for t in targets)
                candidate = (candidate_rank, label)
                previous = policy.get(src)
                if previous is not None and candidate >= previous[:2]:
                    continue
                rank[src] = candidate_rank
                policy[src] = (candidate_rank, label, tuple(edges))
                changed = True
            if not changed:
                break
        self._policies[level] = (rank, policy, actions)
        return self._policies[level]

    def plan(self, obs: Observation, *, remaining_actions: int | None = None) -> ProgressDecision | None:
        self._pending = None
        if obs.state in ('WIN', 'GAME_OVER'):
            return None
        _rank, policy, actions = self._policy(obs.levels_completed)
        source = self.state_id(obs, self._history)
        row = policy.get(source)
        if row is None:
            self._residual('no_supported_progress_continuation', source=source)
            return None
        rank, label, edges = row
        if remaining_actions is not None and rank > remaining_actions:
            self._residual('insufficient_remaining_action_budget', source=source,
                           needed=rank, remaining=remaining_actions)
            return None
        action = actions[label]
        if action[0] not in obs.available_actions:
            self._residual('changed_legal_interface', source=source)
            return None
        decision = ProgressDecision(
            ActionToken(*action, source='crystal_candidate'), rank,
            tuple(sorted({ref for e in edges for ref in e.support_refs})),
            tuple(sorted({e.target for e in edges})))
        self._pending = decision
        self.stats['decisions'] += 1
        return decision

    def to_json(self) -> str:
        return canonical_bytes(dict(
            schema=self.SCHEMA, max_history=self.max_history,
            history_depth=self.history_depth, records=self.records,
            revoked=self.revoked, residuals=self.residuals,
            last_residual=self.last_residual, stats=self.stats,
            history=self._history,
            current=None if self._current is None else self._obs_data(self._current),
            pending=None if self._pending is None else asdict(self._pending),
        )).decode()

    @classmethod
    def from_json(cls, text: str) -> 'ProgressMemory':
        data = json.loads(text)
        if data['schema'] != cls.SCHEMA:
            raise ValueError('unsupported continuation memory schema')
        result = cls(data['max_history'])
        if not 0 <= data['history_depth'] <= result.max_history:
            raise ValueError('invalid history depth')
        result.history_depth = data['history_depth']
        for row in data['records']:
            evidence = row['evidence']
            payload = {k: v for k, v in row.items() if k != 'evidence'}
            if evidence != content_id(payload, prefix='arc-observation'):
                raise ValueError('observation evidence identity mismatch')
            if row['cost'] != 1 or row['action'][0] not in row['before']['available_actions']:
                raise ValueError('invalid observed action or cost')
            if evidence in result._record_ids:
                raise ValueError('duplicate observation evidence')
            result._record_ids.add(evidence)
            result.records.append(row)
        if not set(data['revoked']).issubset(result._record_ids):
            raise ValueError('unknown revoked evidence')
        result.revoked = data['revoked']
        result.residuals = data['residuals']
        result.last_residual = data['last_residual']
        result.stats = data['stats']
        result._history = tuple(data['history'])
        if data['current'] is not None:
            current = data['current']
            current['available_actions'] = tuple(current['available_actions'])
            result._current = Observation(**current)
        if data['pending'] is not None:
            p = data['pending']
            result._pending = ProgressDecision(ActionToken(**p['action']), p['rank'],
                tuple(p['support_refs']), tuple(p['expected_targets']), p['status'])
        return result


class DevelopmentalController(MemoryGraphController):
    """Existing online discovery plus a live compiled continuation consumer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.crystal = ProgressMemory(max_history=kwargs.get('max_history', 8))
        super().__init__(*args, **kwargs)

    def reset_episode(self) -> None:
        super().reset_episode()
        self.crystal._current = None
        self.crystal._history = ()
        self.crystal._pending = None

    def _process_previous_outcome(self, obs: Observation) -> None:
        if self._previous is not None and self._last_action is not None:
            self.crystal.observe(self._previous, self._last_action, obs)
        elif self.crystal._current is None:
            self.crystal.begin(obs)
        super()._process_previous_outcome(obs)

    def _next_archive(self, obs: Observation) -> ActionToken | None:
        # Reuse the existing priority hook; the token retains CANDIDATE status.
        # The inherited baseline implementation itself remains byte-identical.
        decision = self.crystal.plan(obs)
        if decision is not None:
            return decision.action
        return super()._next_archive(obs)

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        # New online memory never falls back to the old start-only replay.
        # Existing cross-level constructor proposals retain their candidate role.
        return self._next_transfer(obs)

    def observe_terminal(self, frame: Any) -> None:
        obs = normalize_frame(frame)
        self._process_previous_outcome(obs)
        self._previous = obs
        self._last_action = None
