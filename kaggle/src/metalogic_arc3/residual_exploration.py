"""Compile unresolved action obligations through the same observed future graph.

A route to a frontier is a candidate experiment, not a proof of goal progress
or safety. Only actual observations enter the historical warrant graph. The
fixed inherited action-grounding language is retained as an explicit boundary.
"""
from __future__ import annotations
import json
from typing import Callable
from .developmental_controller import DevelopmentalController, ProgressDecision, ProgressMemory
from .runtime import ActionToken, Observation



def _emit_frontier(memory, obs, current, value, key, edges, remaining_actions):
    if remaining_actions is not None and value > remaining_actions:
        memory._residual('insufficient_probe_budget',source=current,
                         needed=value,remaining=remaining_actions)
        return None
    if key[0] not in obs.available_actions:
        memory._residual('changed_probe_legal_interface',source=current)
        return None
    source = 'crystal_probe_route' if edges else 'crystal_probe'
    decision = ProgressDecision(
        ActionToken(*key,source=source),value,
        tuple(sorted({s for e in edges for s in e.support_refs})),
        tuple(sorted({e.target for e in edges})))
    memory._residual('unobserved_action_consequence',source=current,
                     action=list(key),remaining_probe_rank=value)
    # Do not compare an unknown probe outcome with a nonexistent prediction.
    memory._pending = decision if edges else None
    memory.stats['residual_decisions'] = memory.stats.get('residual_decisions',0)+1
    if not edges:
        memory.stats['probe_actions'] = memory.stats.get('probe_actions',0)+1
    return decision



def frontier_continuation(
    memory: ProgressMemory,
    obs: Observation,
    catalog: Callable[[Observation], tuple[ActionToken, ...]],
    *,
    remaining_actions: int | None = None,
) -> ProgressDecision | None:
    """Regress to a reachable unobserved action, charging its final probe.

    Exists action / all observed successors reach an unresolved experiment.
    Ties use the inherited action order, not game-specific rewards or features.
    No successor is invented for the unobserved probe. Exhausting this finite
    interface is UNKNOWN, never a universal impossibility claim.
    """
    if obs.state in ('WIN', 'GAME_OVER'):
        return None
    _machine, source_states, groups, actions = memory._compile()
    states = dict(source_states)
    current = memory.state_id(obs, memory._history)
    states[current] = memory._obs_data(obs)
    rank: dict[str, int] = {}
    policy = {}
    eligible = {s for s, data in states.items()
                if data['state'] not in ('WIN', 'GAME_OVER') and
                data['levels_completed'] == obs.levels_completed}
    attempted = {}
    for (source,label) in groups:
        attempted.setdefault(source,set()).add(actions[label])
    # Every routed experiment costs at least two actions. A local unobserved
    # probe costs one, so it is already minimal in this exact finite algebra.
    # Avoid enumerating unrelated catalogs when that decisive bound applies.
    for token in catalog(obs):
        key = memory._action(token)
        if key not in attempted.get(current,set()):
            return _emit_frontier(memory,obs,current,1,key,(),remaining_actions)
    for state in sorted(eligible - {current}):
        data = dict(states[state])
        data['available_actions'] = tuple(data['available_actions'])
        for token in catalog(Observation(**data)):
            key = memory._action(token)
            if key in attempted.get(state,set()):
                continue
            rank[state] = 1
            # One final unresolved action. Its outcomes are deliberately absent.
            policy[state] = (1,key,(),state,key)
            break
    for _ in range(len(eligible)):
        changed = False
        for (source,label), edges in sorted(groups.items()):
            if source not in eligible or rank.get(source) == 1:
                continue
            targets = {e.target for e in edges}
            if not targets or not all(t in rank for t in targets):
                continue
            value = 1 + max(rank[t] for t in targets)
            key = actions[label]
            previous = policy.get(source)
            if previous is not None and (value,key) >= previous[:2]:
                continue
            rank[source] = value
            # An observation-conditioned experiment may end at distinct
            # residuals on different branches; replan after every observation.
            policy[source] = (value,key,tuple(edges),None,None)
            changed = True
        if not changed:
            break
    row = policy.get(current)
    if row is None:
        memory._residual('observed_frontier_exhausted_not_impossible',source=current,
                         action_language='inherited_bounded_legal_catalog',
                         history_bound=memory.max_history)
        return None
    value,key,edges,frontier,probe = row
    return _emit_frontier(memory,obs,current,value,key,edges,remaining_actions)



class ResidualController(DevelopmentalController):
    """Exact replay, frozen structural plans, then unresolved experiments."""

    def reset_episode(self) -> None:
        super().reset_episode()
        self._cross_marker_level: int | None = None
        self._cross_marker_targets: dict[int, tuple[int, int]] = {}
        self._cross_marker_completed: set[int] = set()
        self._cross_marker_pending_switch: int | None = None

    def _clear_cross_marker(self, reason: str | None = None) -> None:
        if reason and self._cross_marker_targets:
            self.crystal._residual(
                reason,
                level=self._cross_marker_level,
                targets=[[k, *v] for k, v in sorted(self._cross_marker_targets.items())],
            )
        self._cross_marker_level = None
        self._cross_marker_targets = {}
        self._cross_marker_completed = set()
        self._cross_marker_pending_switch = None

    def _acquire_cross_marker_targets(self, obs: Observation) -> bool:
        if not obs.structural_targets:
            return False
        try:
            rows = json.loads(obs.structural_targets)
            targets = {
                int(color): (int(row), int(col))
                for color, row, col in rows
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        # The warranted source law has exactly two independently movable
        # cross/marker families. More or fewer is a different mechanic.
        if len(targets) != 2:
            return False
        if obs.structural_active_color not in targets:
            return False
        center = (obs.structural_center_r, obs.structural_center_c)
        if None in center:
            return False
        tr, tc = targets[int(obs.structural_active_color)]
        if (tr - int(center[0])) % 3 or (tc - int(center[1])) % 3:
            return False
        self._cross_marker_level = obs.levels_completed
        self._cross_marker_targets = targets
        self._cross_marker_completed = set()
        self._cross_marker_pending_switch = None
        self.crystal.stats["structural_plans_acquired"] = (
            self.crystal.stats.get("structural_plans_acquired", 0) + 1)
        return True

    def _cross_marker_action(self, obs: Observation) -> ActionToken | None:
        if obs.state in ("WIN", "GAME_OVER"):
            self._clear_cross_marker()
            return None
        if self._cross_marker_level is not None and self._cross_marker_level != obs.levels_completed:
            self._clear_cross_marker()
        if not self._cross_marker_targets:
            if not self._acquire_cross_marker_targets(obs):
                return None

        if (
            obs.structural_kind != "cross-marker-pose@2"
            or obs.structural_active_color is None
            or obs.structural_center_r is None
            or obs.structural_center_c is None
        ):
            self._clear_cross_marker("cross_marker_pose_separator")
            return None

        active = int(obs.structural_active_color)
        if self._cross_marker_pending_switch is not None:
            if active == self._cross_marker_pending_switch:
                self._clear_cross_marker("cross_marker_switch_failed")
                return None
            self._cross_marker_pending_switch = None

        target = self._cross_marker_targets.get(active)
        if target is None:
            self._clear_cross_marker("cross_marker_unbound_active_color")
            return None
        r, col = int(obs.structural_center_r), int(obs.structural_center_c)
        tr, tc = target
        dr, dc = tr - r, tc - col
        if dr % 3 or dc % 3:
            self._clear_cross_marker("cross_marker_lattice_separator")
            return None

        if dr == 0 and dc == 0:
            self._cross_marker_completed.add(active)
            if len(self._cross_marker_completed) == len(self._cross_marker_targets):
                # Reaching both frozen targets without progress falsifies this
                # capability on the current level. Do not guess a submit action.
                self._clear_cross_marker("cross_marker_targets_aligned_no_progress")
                return None
            if 5 not in obs.available_actions:
                self._clear_cross_marker("cross_marker_switch_unavailable")
                return None
            self._cross_marker_pending_switch = active
            self.crystal.stats["structural_decisions"] = (
                self.crystal.stats.get("structural_decisions", 0) + 1)
            return ActionToken(5, source="crystal_cross_marker")

        action = 1 if dr < 0 else 2 if dr > 0 else 3 if dc < 0 else 4
        if action not in obs.available_actions:
            self._clear_cross_marker("cross_marker_move_unavailable")
            return None
        self.crystal.stats["structural_decisions"] = (
            self.crystal.stats.get("structural_decisions", 0) + 1)
        return ActionToken(action, source="crystal_cross_marker")

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        # OnlineController has already offered exact archive/trace/continuation
        # evidence. A frozen structural plan therefore occupies the warranted-
        # candidate layer immediately before buying a new UNKNOWN probe.
        structural = self._cross_marker_action(obs)
        if structural is not None:
            return structural
        decision = frontier_continuation(self.crystal, obs, self._action_catalog)
        if decision is not None:
            return decision.action
        return super()._next_retained(obs)

