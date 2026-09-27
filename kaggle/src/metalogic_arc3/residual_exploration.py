"""Compile unresolved action obligations through the same observed future graph.

A route to a frontier is a candidate experiment, not a proof of goal progress
or safety. Only actual observations enter the historical warrant graph. The
fixed inherited action-grounding language is retained as an explicit boundary.
"""
from __future__ import annotations
from typing import Callable
from itertools import product
from .developmental_controller import DevelopmentalController, ProgressDecision, ProgressMemory
from .runtime import ActionToken, Observation
from .arc_crystal import ArcCrystal, CapabilityEvidence
from .protected_future_kernel import ProtectedFutureKernel, context as future_context



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
    """Progress reuse plus residual-driven bounded procedure genesis."""

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._genesis_level = None
        self._genesis_programs = ()
        self._genesis_index = 0
        self._genesis_step = 0
        self._genesis_start_level = None
        self._probe_spend_by_level = {}
        self._genesis_threshold = 24
        self._residual_crystal = ArcCrystal()
        self._pending_acquisition_role = None
        self._role_splits = set()
        # EXPAND is authority-gated: finite probe exhaustion is UNKNOWN, not an obstruction.
        self._expressive_obstructions = {}
        self._future_kernels = {}

    def reset_episode(self):
        super().reset_episode()
        self._genesis_level = None
        self._genesis_programs = ()
        self._genesis_index = 0
        self._genesis_step = 0
        self._genesis_start_level = None

    def certify_expressive_obstruction(self, level: int, support: str) -> None:
        """Admit EXPAND only after an independently named obstruction.

        The support string is provenance, not proof by itself; qualification
        must establish it at the declared current-class boundary.
        """
        self._expressive_obstructions[int(level)] = str(support)
        self.crystal.stats['expressive_obstructions'] = self.crystal.stats.get('expressive_obstructions',0)+1

    def _expansion_authorized(self, obs: Observation) -> bool:
        return obs.levels_completed in self._expressive_obstructions

    def _crystal_acquisition_next(self, obs: Observation) -> ActionToken | None:
        atoms = tuple(self._action_catalog(obs))[:8]
        if not atoms:
            return None
        hypotheses = tuple(f'p{i}' for i in range(len(atoms)))
        actions = tuple((a.action_id,a.x,a.y) for a in atoms)
        # Procedure hypotheses expose candidate role/action pairs. Start from
        # the smallest current observable role; Crystal, not this controller,
        # decides which UNKNOWN role is worth acquiring next.
        roles = {}
        for h in hypotheses:
            hi = int(h[1:])
            for a in actions:
                coarse = ('procedure-effect-v2',a[0],a[1],a[2],obs.levels_completed)
                # Begin at the consequence quotient. Hypothesis identity enters
                # only after the coarse role has witnessed conflicting futures.
                roles[(h,a)] = coarse + (('split-h',hi),) if coarse in self._role_splits else coarse
        wanted = ArcCrystal.next_acquisition(hypotheses,actions,roles,self._residual_crystal)
        if wanted is None:
            return None
        # The role encodes the real action whose consequence must be purchased.
        # v2 = (kind, action_id, x, y, level[, split]); split suffix is not an action.
        action = (wanted[1],wanted[2],wanted[3])
        if action[0] not in obs.available_actions:
            return None
        self._pending_acquisition_role = wanted
        self.crystal.stats['crystal_acquisitions'] = self.crystal.stats.get('crystal_acquisitions',0)+1
        return ActionToken(*action,source='crystal_acquire')

    def _genesis_next(self, obs: Observation) -> ActionToken | None:
        # EXPAND only over the inherited finite legal action substrate. Search
        # programs by length, then inherited catalog order: explicit minimum
        # construction cost, no game-specific reward shaping.
        if self._genesis_level != obs.levels_completed:
            atoms = tuple(self._action_catalog(obs))
            # Keep the declared expansion finite and consequentially cheap.
            atoms = atoms[:min(8,len(atoms))]
            self._genesis_programs = tuple(
                p for n in range(1,4) for p in product(atoms, repeat=n))
            self._genesis_level = obs.levels_completed
            self._genesis_index = 0
            self._genesis_step = 0
            self._genesis_start_level = obs.levels_completed
        while self._genesis_index < len(self._genesis_programs):
            p = self._genesis_programs[self._genesis_index]
            if self._genesis_step >= len(p):
                self._genesis_index += 1; self._genesis_step = 0; continue
            token = p[self._genesis_step]
            if token.action_id not in obs.available_actions:
                self._genesis_index += 1; self._genesis_step = 0; continue
            self._genesis_step += 1
            self.crystal.stats['genesis_actions'] = self.crystal.stats.get('genesis_actions',0)+1
            return ActionToken(token.action_id,token.x,token.y,source='crystal_genesis')
        self.crystal._residual('bounded_procedure_genesis_exhausted',
            level=obs.levels_completed,max_program_length=3,atom_bound=8)
        return None

    def _process_previous_outcome(self, obs: Observation) -> None:
        previous = self._previous
        last = self._last_action
        super()._process_previous_outcome(obs)
        if previous is not None and last is not None and last.source == 'crystal_acquire' and self._pending_acquisition_role is not None:
            outcome = repr((obs.state,obs.levels_completed-previous.levels_completed,obs.board_digest != previous.board_digest))
            role = self._pending_acquisition_role
            coarse = role[:5] if role and role[0]=='procedure-effect-v2' else role
            features = self._guard_features(self._last_causal_role)
            ctx = future_context(**features)
            support = f'live:{previous.board_digest}:{last.action_id}:{last.x}:{last.y}'
            kernel = self._future_kernels.setdefault(coarse, ProtectedFutureKernel())
            kernel.observe(outcome,support,ctx)
            before_conflict = self._residual_crystal.conflicted(role)
            self._residual_crystal.observe(CapabilityEvidence(
                role,outcome,source=support,
                consequence_grade=1 if obs.levels_completed>previous.levels_completed else 0))
            if self._residual_crystal.conflicted(role) and not before_conflict:
                # Collatz-style refinement: the conflict itself is the residual.
                # Admit only a witnessed causal coordinate that removes the
                # protected-future conflict; otherwise preserve the obstruction.
                candidates = tuple(sorted(features))
                sep = kernel.refine(candidates)
                if sep is not None:
                    self.crystal.stats['future_kernel_splits'] = self.crystal.stats.get('future_kernel_splits',0)+1
                    self.crystal._residual('protected_future_separator_admitted',
                        role=repr(coarse),separator=sep)
                elif kernel.expressive_obstruction:
                    support = 'protected-future-kernel:'+repr(coarse)
                    self.certify_expressive_obstruction(obs.levels_completed,support)
                    self.crystal._residual('protected_future_kernel_obstruction',
                        role=repr(coarse),candidate_language=list(candidates))
                # Keep the old hypothesis split only as an ablation lineage;
                # it is no longer the authority for developmental refinement.
                self._role_splits.add(coarse)
            self._pending_acquisition_role = None
        if previous is not None and last is not None and last.source == 'crystal_genesis':
            if obs.levels_completed > previous.levels_completed:
                self.crystal.stats['genesis_progress'] = self.crystal.stats.get('genesis_progress',0)+1
                # ProgressMemory has already observed the successful segment;
                # reset search so subsequent execution begins from compiled
                # consequence rather than continuing enumeration.
                self._genesis_level = None
                self._genesis_programs = ()
                self._genesis_index = self._genesis_step = 0

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        # CLOSE before INTERACT: after a candidate continuation is revoked,
        # reclose over every still-live inherited/retained capability before
        # purchasing another experiment. This preserves the baseline's
        # qualified continuation routes instead of probing through them.
        reused = super()._next_retained(obs)
        if reused is not None:
            return reused
        # The existing one-step frontier remains the cheapest decisive
        # experiment. Once its current finite interface is exhausted, EXPAND
        # into bounded guarded procedure construction rather than repeating
        # flat probes forever.
        spent = self._probe_spend_by_level.get(obs.levels_completed, 0)
        if spent >= self._genesis_threshold:
            token = self._crystal_acquisition_next(obs)
            if token is not None:
                return token
        decision = frontier_continuation(self.crystal,obs,self._action_catalog)
        if decision is not None:
            self._probe_spend_by_level[obs.levels_completed] = spent + 1
            return decision.action
        # MDA boundary: exhausting the admitted probe interface is UNKNOWN.
        # Bounded procedure genesis is lawful only after a separately certified
        # obstruction to the current reachable experiment class.
        if self._expansion_authorized(obs):
            self.crystal.stats['authorized_expansions'] = self.crystal.stats.get('authorized_expansions',0)+1
            return self._genesis_next(obs)
        self.crystal._residual('expressive_obstruction_required_before_expand',
            level=obs.levels_completed,
            current_class='inherited_bounded_legal_catalog')
        return None
