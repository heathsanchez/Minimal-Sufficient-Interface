"""Bounded option-compositional development without game-specific semantics.

Previously witnessed suffixes are candidate constructors, not universal rules.
Repetition is a generic program constructor. Every candidate is replayed via
public observations; only external progress promotes it. Primitive search stays
available and all experiments count against the training budget.
"""
from collections import deque
from multi_level_development import MultiLevelDevelopment, execute_stage
from restart_development import RestartDevelopment


def repetitions(programs, bound):
    """Enumerate repeated programs by primitive length, without duplicates."""
    candidates = set()
    for program in programs:
        program = tuple(program)
        if not program:
            continue
        for n in range(2, bound // len(program) + 1):
            candidates.add(program * n)
    return tuple(sorted(candidates, key=lambda p: (len(p), p)))


class OptionSearch(RestartDevelopment):
    def __init__(self, actions, options=(), max_depth=32):
        super().__init__(tuple(actions), max_depth=max_depth)
        self.options = tuple(dict.fromkeys(tuple(o) for o in options if 1 < len(o) <= max_depth))
        self.frontier = deque(dict.fromkeys(self.options + repetitions(self.options, max_depth)
                                             + tuple((a,) for a in self.actions)))
        self.seen = set()

    def propose(self):
        while True:
            p = super().propose()
            if p is None:
                return None
            if p not in self.seen:
                self.seen.add(p)
                return p

    def retain(self, program, result):
        verdict = super().retain(program, result)
        if verdict == 'NONTERMINAL_PREFIX':
            # Expand the program grammar, not a presumed game rule.
            additions = [tuple(program) + o for o in self.options
                         if len(program) + len(o) <= self.max_depth]
            additions += list(repetitions((program,), self.max_depth))
            self.frontier.extendleft(reversed(tuple(dict.fromkeys(additions))))
        return verdict


def discover_levels(factory, actions, budget=120, max_episodes=512,
                    max_depth=32, max_training_actions=3000, max_levels=5):
    d = MultiLevelDevelopment(tuple(actions), max_depth=max_depth)
    while len(d.stages) < max_levels:
        target = len(d.stages)
        search = OptionSearch(d.actions, d.options, max_depth=max_depth)
        advanced = False
        while d.training_episodes < max_episodes and d.training_actions < max_training_actions:
            suffix = search.propose()
            if suffix is None:
                break
            remaining = min(budget, max_training_actions - d.training_actions)
            if remaining <= len(d.prefix):
                d.status = 'TRAINING_BOUND_EXHAUSTED'
                return d
            result = execute_stage(factory(), d.prefix, suffix, target, remaining, d.checkpoint)
            d.training_episodes += 1
            d.training_actions += result['actions']
            if d.initial_sha256 is None:
                d.initial_sha256 = result['initial_sha256']
            if result['initial_sha256'] != d.initial_sha256 or result['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH', 'PREFIX_TERMINATED'):
                d.status = 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX'
                return d
            d.evidence.append({'target':target,'suffix':suffix,'status':result['status'],
                               'actions':result['actions'],'progress':result['progress'],
                               'terminal':result['terminal'],'trace_sha256':result['trace_sha256'],
                               'score':result['score']})
            if result['status'] == 'BUDGET_EXHAUSTED':
                d.status = 'TRAINING_BOUND_EXHAUSTED'
                return d
            local = dict(result, actions=result['actions']-len(d.prefix),
                         executed=result['executed'][len(d.prefix):])
            verdict = search.retain(suffix, local)
            if verdict == 'PROGRESS_WITNESSED':
                observed_suffix = local['executed']
                if observed_suffix not in d.options:
                    d.options.append(observed_suffix)
                d.prefix += observed_suffix
                d.checkpoint = result['final_sha256']
                d.stages.append({'level':target+1,'suffix':observed_suffix,
                                 'prefix':d.prefix,'actions':result['actions'],
                                 'trace_sha256':result['trace_sha256'],
                                 'checkpoint_sha256':d.checkpoint})
                advanced = True
                break
        if not advanced:
            d.status = 'NO_PROGRESS_WITHIN_BOUND'
            return d
        if d.training_episodes >= max_episodes or d.training_actions >= max_training_actions:
            d.status = 'TRAINING_BOUND_EXHAUSTED'
            return d
    d.status = 'ALL_LEVELS_WITNESSED'
    return d


def compare_levels(factory, actions, budget=120, max_episodes=512,
                   max_depth=32, max_training_actions=3000, max_levels=5):
    d = discover_levels(factory, actions, budget, max_episodes, max_depth,
                        max_training_actions, max_levels)
    cold = execute_stage(factory(), (), tuple(actions)*((budget+len(actions)-1)//len(actions)),
                         0, budget, stop_at_progress=False)
    warm = execute_stage(factory(), (), d.prefix, 0, budget, stop_at_progress=False)
    matched = cold['initial_sha256'] == warm['initial_sha256'] == d.initial_sha256
    better = warm['levels_completed'] > cold['levels_completed'] or (
        warm['levels_completed'] == cold['levels_completed'] > 0 and warm['actions'] < cold['actions'])
    return {'status':'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'development':d.snapshot(),'cold':cold,'warm':warm,
            'improved':bool(matched and better)}
