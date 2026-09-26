"""Compile unresolved action obligations through the same observed future graph.

A route to a frontier is a candidate experiment, not a proof of goal progress
or safety. Only actual observations enter the historical warrant graph. The
fixed inherited action-grounding language is retained as an explicit boundary.
"""
from __future__ import annotations
from typing import Callable
from .developmental_controller import DevelopmentalController, ProgressDecision, ProgressMemory
from .runtime import ActionToken, Observation


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
    for state in sorted(eligible):
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


class ResidualController(DevelopmentalController):
    """Progress reuse plus first-goal experiments; old controllers are ablations."""

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        decision = frontier_continuation(self.crystal,obs,self._action_catalog)
        if decision is not None:
            return decision.action
        return super()._next_retained(obs)
