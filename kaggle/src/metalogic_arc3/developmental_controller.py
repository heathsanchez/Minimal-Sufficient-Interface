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

    def __init__(self, max_history: int = 8, max_relative_depth: int = 32) -> None:
        if max_history < 1:
            raise ValueError('max_history must be positive')
        if max_relative_depth < 1:
            raise ValueError('max_relative_depth must be positive')
        self.max_history = int(max_history)
        self.max_relative_depth = int(max_relative_depth)
        self.history_depth = 0
        self.records: list[dict[str, Any]] = []
        self.revoked: dict[str, str] = {}
        self.residuals: list[dict[str, Any]] = []
        self.last_residual: dict[str, Any] | None = None
        self.relative_capabilities: dict[str, dict[str, Any]] = {}
        # Negative evidence is durable across environment RESETs. A failed
        # binding does not revoke the source mechanism globally; it rejects
        # only this capability in the observed target progress context.
        self.relative_rejections: dict[str, dict[str, Any]] = {}
        self.stats = dict(
            decisions=0, observed_progress=0, matched_predictions=0,
            prediction_mismatches=0, refinements=0, closure_builds=0,
            relative_capabilities_compiled=0, relative_capability_decisions=0,
            relative_capability_progress=0, relative_capability_mismatches=0,
            relative_context_rejections=0, relative_projection_rejections=0,
            relative_mechanism_rejections=0, relative_retry_suppressions=0,
        )
        self._record_ids: set[str] = set()
        self._history: tuple = ()
        self._current: Observation | None = None
        self._pending: ProgressDecision | None = None
        self._compiled = None
        self._policies: dict[int, Any] = {}
        self._segment_rows: list[dict[str, Any]] = []
        self._active_relative: dict[str, Any] | None = None
        self._relative_index = 0
        self._relative_pending: tuple[str, int, dict[str, Any]] | None = None
        self._relative_failed_caps: set[str] = set()

    @staticmethod
    def _obs_data(obs: Observation) -> dict[str, Any]:
        return asdict(obs)

    @staticmethod
    def _action(action: ActionToken) -> tuple:
        return action.action_id, action.x, action.y

    def _next_history(self, before: Observation, action: ActionToken) -> tuple:
        return (self._history + ((before.frame_digest, self._action(action)),))[-self.max_history:]

    @staticmethod
    def _interface(obs: Observation | dict[str, Any]) -> tuple[Any, ...]:
        if isinstance(obs, Observation):
            return (obs.state, obs.available_actions, obs.height, obs.width)
        return (
            str(obs['state']), tuple(obs['available_actions']),
            int(obs['height']), int(obs['width']),
        )

    @staticmethod
    def _stored_interface(value: list[Any] | tuple[Any, ...]) -> tuple[Any, ...]:
        return (str(value[0]), tuple(value[1]), int(value[2]), int(value[3]))

    @staticmethod
    def _interface_payload(obs: Observation) -> list[Any]:
        return [
            str(obs.state), list(obs.available_actions),
            int(obs.height), int(obs.width),
        ]

    @staticmethod
    def _relation(before: dict[str, Any], after: dict[str, Any], key: str) -> str:
        return 'same' if before[key] == after[key] else 'changed'

    @staticmethod
    def _relative_progress(before: Observation | dict[str, Any],
                           after: Observation | dict[str, Any]) -> bool:
        if isinstance(before, Observation):
            return after.levels_completed > before.levels_completed or (
                after.state == 'WIN' and before.state != 'WIN')
        return int(after['levels_completed']) > int(before['levels_completed']) or (
            after['state'] == 'WIN' and before['state'] != 'WIN')

    def reset_transient(self) -> None:
        self._history = ()
        self._current = None
        self._pending = None
        self._segment_rows = []
        self._active_relative = None
        self._relative_index = 0
        self._relative_pending = None
        self._relative_failed_caps = set()
        # Deliberately preserve relative_rejections. RESET is not evidence
        # that a disproved capability→goal binding became valid again.

    def begin(self, obs: Observation) -> None:
        self._history = ()
        self._current = obs
        self._pending = None
        self._segment_rows = []
        self._active_relative = None
        self._relative_index = 0
        self._relative_pending = None

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

    @staticmethod
    def _relative_context_key(capability_id: str, obs: Observation) -> str:
        # Progress level is used only as a local negative-evidence scope inside
        # one game/controller. It is not an applicability feature for positive
        # cross-context transfer.
        return f"{capability_id}|progress-level={int(obs.levels_completed)}"

    def _reject_relative_context(
        self,
        capability_id: str,
        before: Observation,
        *,
        failure_kind: str,
        step: int,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> None:
        key = self._relative_context_key(capability_id, before)
        if key not in self.relative_rejections:
            self.relative_rejections[key] = dict(
                capability=capability_id,
                progress_level=int(before.levels_completed),
                interface=self._interface_payload(before),
                failure_kind=failure_kind,
                step=int(step),
                expected=expected,
                actual=actual,
            )
            self.stats['relative_context_rejections'] += 1
            if failure_kind == 'projection':
                self.stats['relative_projection_rejections'] += 1
            else:
                self.stats['relative_mechanism_rejections'] += 1

    def _compile_relative(self, rows: list[dict[str, Any]]) -> None:
        if not rows or len(rows) > self.max_relative_depth:
            if rows:
                self._residual('relative_program_too_long',
                               observed_length=len(rows),
                               max_relative_depth=self.max_relative_depth)
            return
        start_level = int(rows[0]['before']['levels_completed'])
        end_level = int(rows[-1]['after']['levels_completed'])
        terminal_progress = rows[-1]['after']['state'] == 'WIN'
        target_delta = max(0, end_level - start_level)
        if target_delta <= 0 and not terminal_progress:
            return
        steps = []
        for row in rows:
            before_row, after_row = row['before'], row['after']
            steps.append(dict(
                interface=[
                    str(before_row['state']), list(before_row['available_actions']),
                    int(before_row['height']), int(before_row['width']),
                ],
                action=list(row['action']),
                board_relation=self._relation(before_row, after_row, 'board_digest'),
                frame_relation=self._relation(before_row, after_row, 'frame_digest'),
                progress=self._relative_progress(before_row, after_row),
            ))
        payload = dict(target_delta=target_delta, steps=steps)
        capability_id = content_id(payload, prefix='arc-relative-progress')
        support_refs = sorted({row['evidence'] for row in rows})
        existing = self.relative_capabilities.get(capability_id)
        if existing is None:
            self.relative_capabilities[capability_id] = dict(
                id=capability_id, target_delta=target_delta, steps=steps,
                source_levels=[start_level], support_refs=support_refs)
            self.stats['relative_capabilities_compiled'] += 1
        else:
            existing['source_levels'] = sorted(set(existing['source_levels']) | {start_level})
            existing['support_refs'] = sorted(set(existing['support_refs']) | set(support_refs))

    def _validate_relative_pending(
        self, before: Observation, action: ActionToken, after: Observation
    ) -> None:
        pending = self._relative_pending
        if pending is None:
            return
        capability_id, index, step = pending
        self._relative_pending = None
        if tuple(step['action']) != self._action(action):
            return
        progress = self._relative_progress(before, after)
        board_relation = 'same' if before.board_digest == after.board_digest else 'changed'
        frame_relation = 'same' if before.frame_digest == after.frame_digest else 'changed'
        capability = self.relative_capabilities.get(capability_id)
        next_interface_ok = True
        if capability is not None and index + 1 < len(capability['steps']):
            next_interface_ok = self._stored_interface(capability['steps'][index + 1]['interface']) == self._interface(after)
        matched = (
            board_relation == step['board_relation']
            and frame_relation == step['frame_relation']
            and bool(progress) == bool(step['progress'])
            and next_interface_ok
        )
        if not matched:
            self.stats['relative_capability_mismatches'] += 1
            self._relative_failed_caps.add(capability_id)
            self._active_relative = None
            self._relative_index = 0
            expected = dict(
                board_relation=step['board_relation'],
                frame_relation=step['frame_relation'],
                progress=bool(step['progress']),
                next_interface=(None if capability is None or index + 1 >= len(capability['steps'])
                                else capability['steps'][index + 1]['interface']),
            )
            actual = dict(
                board_relation=board_relation, frame_relation=frame_relation,
                progress=bool(progress), next_interface=self._interface_payload(after),
            )
            # If all observable mechanism effects still match and only the
            # terminal progress bit fails, preserve the mechanism and reject
            # just its target projection in this context. Otherwise the
            # mechanism binding itself is rejected here.
            projection_failure = (
                bool(step['progress'])
                and not bool(progress)
                and board_relation == step['board_relation']
                and frame_relation == step['frame_relation']
                and next_interface_ok
            )
            failure_kind = 'projection' if projection_failure else 'mechanism'
            self._reject_relative_context(
                capability_id, before, failure_kind=failure_kind, step=index,
                expected=expected, actual=actual)
            self._residual(
                'relative_projection_separator' if projection_failure
                else 'relative_mechanism_separator',
                capability=capability_id, step=index,
                failure_kind=failure_kind, expected=expected, actual=actual,
            )
        elif progress:
            self.stats['relative_capability_progress'] += 1
            self._active_relative = None
            self._relative_index = 0

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
        self._validate_relative_pending(before, action, after)
        record = dict(before=self._obs_data(before), after=self._obs_data(after),
                      action=self._action(action), history=self._history,
                      next_history=next_history, cost=1)
        evidence = content_id(record, prefix='arc-observation')
        segment_record = dict(record, evidence=evidence)
        if evidence not in self._record_ids:
            self.records.append(segment_record)
            self._record_ids.add(evidence)
            self._invalidate()
            self._refine()
        self._segment_rows.append(segment_record)
        progressed = self._relative_progress(before, after)
        if progressed:
            self.stats['observed_progress'] += 1
            self._compile_relative(self._segment_rows)
            self._segment_rows = []
        elif after.state == 'GAME_OVER':
            self._segment_rows = []
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

    def _live_relative_support(self, capability: dict[str, Any]) -> tuple[str, ...]:
        return tuple(sorted(
            ref for ref in capability['support_refs'] if ref not in self.revoked
        ))

    def _relative_candidate(self, obs: Observation) -> dict[str, Any] | None:
        if self._active_relative is not None:
            return self._active_relative
        candidates = []
        for capability in self.relative_capabilities.values():
            if capability['id'] in self._relative_failed_caps:
                continue
            if not any(obs.levels_completed > int(level) for level in capability['source_levels']):
                continue
            context_key = self._relative_context_key(capability['id'], obs)
            if context_key in self.relative_rejections:
                self.stats['relative_retry_suppressions'] += 1
                continue
            if not self._live_relative_support(capability):
                continue
            if not capability['steps']:
                continue
            if self._stored_interface(capability['steps'][0]['interface']) != self._interface(obs):
                continue
            candidates.append(capability)
        if not candidates:
            return None
        candidates.sort(key=lambda row: (
            -len(row['source_levels']), len(row['steps']), row['id']))
        self._active_relative = candidates[0]
        self._relative_index = 0
        return self._active_relative

    def _plan_relative(
        self, obs: Observation, *, remaining_actions: int | None = None
    ) -> ProgressDecision | None:
        capability = self._relative_candidate(obs)
        if capability is None:
            return None
        index = self._relative_index
        if index >= len(capability['steps']):
            self._active_relative = None
            self._relative_index = 0
            return None
        step = capability['steps'][index]
        if self._stored_interface(step['interface']) != self._interface(obs):
            self._relative_failed_caps.add(capability['id'])
            self._active_relative = None
            self._relative_index = 0
            self._residual('relative_applicability_separator',
                           capability=capability['id'], step=index,
                           expected=step['interface'],
                           actual=list(self._interface(obs)))
            return None
        remaining = len(capability['steps']) - index
        if remaining_actions is not None and remaining > remaining_actions:
            self._residual('insufficient_relative_action_budget',
                           capability=capability['id'],
                           needed=remaining, remaining=remaining_actions)
            return None
        action = tuple(step['action'])
        if action[0] not in obs.available_actions:
            self._relative_failed_caps.add(capability['id'])
            self._active_relative = None
            self._relative_index = 0
            self._residual('relative_changed_legal_interface',
                           capability=capability['id'], action=list(action))
            return None
        if action[0] == 6 and (
            action[1] is None or action[2] is None
            or not 0 <= int(action[1]) < obs.width
            or not 0 <= int(action[2]) < obs.height
        ):
            self._relative_failed_caps.add(capability['id'])
            self._active_relative = None
            self._relative_index = 0
            self._residual('relative_action_binding_out_of_bounds',
                           capability=capability['id'], action=list(action))
            return None
        token = ActionToken(*action, source='crystal_relative')
        self._relative_pending = (capability['id'], index, step)
        self._relative_index += 1
        self.stats['relative_capability_decisions'] += 1
        return ProgressDecision(
            token, remaining, self._live_relative_support(capability), (),
            status='CANDIDATE_RELATIVE_PROGRESS')

    def plan(self, obs: Observation, *, remaining_actions: int | None = None) -> ProgressDecision | None:
        self._pending = None
        if obs.state in ('WIN', 'GAME_OVER'):
            return None
        _rank, policy, actions = self._policy(obs.levels_completed)
        source = self.state_id(obs, self._history)
        row = policy.get(source)
        if row is None:
            relative = self._plan_relative(obs, remaining_actions=remaining_actions)
            if relative is not None:
                return relative
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
            max_relative_depth=self.max_relative_depth,
            history_depth=self.history_depth, records=self.records,
            revoked=self.revoked, residuals=self.residuals,
            last_residual=self.last_residual, stats=self.stats,
            relative_capabilities=self.relative_capabilities,
            relative_rejections=self.relative_rejections,
            segment_rows=self._segment_rows,
            history=self._history,
            current=None if self._current is None else self._obs_data(self._current),
            pending=None if self._pending is None else asdict(self._pending),
        )).decode()

    @classmethod
    def from_json(cls, text: str) -> 'ProgressMemory':
        data = json.loads(text)
        if data['schema'] != cls.SCHEMA:
            raise ValueError('unsupported continuation memory schema')
        result = cls(data['max_history'], data.get('max_relative_depth', 32))
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
        defaults = dict(result.stats)
        defaults.update(data['stats'])
        result.stats = defaults
        result.relative_capabilities = data.get('relative_capabilities', {})
        result.relative_rejections = data.get('relative_rejections', {})
        for rejection in result.relative_rejections.values():
            capability_id = rejection.get('capability')
            if capability_id not in result.relative_capabilities:
                raise ValueError('relative rejection refers to unknown capability')
            if rejection.get('failure_kind') not in ('mechanism', 'projection'):
                raise ValueError('invalid relative rejection kind')
        for capability_id, capability in result.relative_capabilities.items():
            payload = dict(target_delta=capability['target_delta'], steps=capability['steps'])
            if capability_id != content_id(payload, prefix='arc-relative-progress'):
                raise ValueError('relative capability identity mismatch')
            if not set(capability['support_refs']).issubset(result._record_ids):
                raise ValueError('relative capability has unknown support')
        result._segment_rows = data.get('segment_rows', [])
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
        max_relative_depth = int(kwargs.pop('max_relative_depth', 32))
        self.crystal = ProgressMemory(
            max_history=kwargs.get('max_history', 8),
            max_relative_depth=max_relative_depth,
        )
        super().__init__(*args, **kwargs)

    def reset_episode(self) -> None:
        super().reset_episode()
        self.crystal.reset_transient()

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
