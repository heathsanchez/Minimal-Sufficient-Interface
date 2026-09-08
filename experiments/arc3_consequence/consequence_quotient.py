"""Source-blind, bounded consequence quotient and staged search.

An equivalence class is local to a checkpoint and probe horizon. It is never
assumed to be a universal action law. Every stage remeasures the full alphabet;
failed reduced search reopens the original alphabet. All probes count.
"""
from collections import defaultdict, deque
from multi_level_development import MultiLevelDevelopment, execute_stage
from compositional_development import OptionSearch
from finite_consequence import digest

BAD = ('INCONCLUSIVE_PREFIX_MISMATCH', 'PREFIX_TERMINATED')


def measure(factory, actions, prefix, target, checkpoint, budget, horizon=4,
            remaining_actions=20000, remaining_episodes=2048):
    """Return an observed quotient, or an explicit incomplete measurement."""
    groups = defaultdict(list)
    rows = []
    spent = episodes = 0
    initial = None
    for action in actions:
        if episodes >= remaining_episodes or spent + len(prefix) + horizon > remaining_actions:
            return {'status':'BOUND_EXHAUSTED','rows':rows,'actions':spent,
                    'episodes':episodes,'initial_sha256':initial}
        # The entire observed suffix is part of the consequence. This avoids
        # conflating a terminal or early-progress trace with a full probe.
        result = execute_stage(factory(), prefix, (action,)*horizon, target,
                               min(budget, len(prefix)+horizon), checkpoint,
                               stop_at_progress=False)
        spent += result['actions']; episodes += 1
        if initial is None: initial = result['initial_sha256']
        if result['initial_sha256'] != initial or result['status'] in BAD:
            return {'status':'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX','rows':rows,
                    'actions':spent,'episodes':episodes,'initial_sha256':initial}
        key = digest((result['executed'][len(prefix):], result['progress'],
                      result['state'], result['final_sha256']))
        # Action identities are intentionally removed from the consequence:
        # only execution length, progress, terminal state and final observation
        # determine the class. The execution trace remains in the evidence.
        key = digest((result['actions']-len(prefix), result['progress'],
                      result['state'], result['final_sha256']))
        groups[key].append(action)
        rows.append({'action':action,'consequence':key,'trace_sha256':result['trace_sha256']})
    classes = [{'representative':members[0], 'members':members} for members in groups.values()]
    return {'status':'OBSERVED_QUOTIENT','classes':classes,'rows':rows,
            'actions':spent,'episodes':episodes,'initial_sha256':initial,
            'evidence_sha256':digest(rows),'horizon':horizon}


def discover(factory, actions, budget=120, max_episodes=2048, max_depth=32,
             max_training_actions=20000, max_levels=5, horizon=4):
    d = MultiLevelDevelopment(tuple(actions), max_depth=max_depth)
    quotients = []
    while len(d.stages) < max_levels:
        target = len(d.stages)
        q = measure(factory, d.actions, d.prefix, target, d.checkpoint, budget,
                    horizon, max_training_actions-d.training_actions,
                    max_episodes-d.training_episodes)
        d.training_actions += q['actions']; d.training_episodes += q['episodes']
        if d.initial_sha256 is None: d.initial_sha256 = q['initial_sha256']
        if q['initial_sha256'] != d.initial_sha256 or q['status'].startswith('INCONCLUSIVE'):
            d.status = 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX'; break
        if q['status'] != 'OBSERVED_QUOTIENT':
            d.status = 'TRAINING_BOUND_EXHAUSTED'; break
        quotients.append(q)
        reduced = tuple(c['representative'] for c in q['classes'])
        advanced = False
        # Reduced first, then the original alphabet. No class is permanently
        # deleted, and a new checkpoint gets a new measurement.
        for alphabet in (reduced, d.actions):
            search = OptionSearch(alphabet, d.options, max_depth=max_depth)
            while d.training_episodes < max_episodes and d.training_actions < max_training_actions:
                suffix = search.propose()
                if suffix is None: break
                remaining = min(budget, max_training_actions-d.training_actions)
                if remaining <= len(d.prefix): break
                result = execute_stage(factory(), d.prefix, suffix, target, remaining, d.checkpoint)
                d.training_episodes += 1; d.training_actions += result['actions']
                if result['initial_sha256'] != d.initial_sha256 or result['status'] in BAD:
                    d.status = 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX'
                    return d, quotients
                d.evidence.append({'target':target,'suffix':suffix,'status':result['status'],
                                   'actions':result['actions'],'trace_sha256':result['trace_sha256']})
                if result['status'] == 'BUDGET_EXHAUSTED':
                    d.status = 'TRAINING_BOUND_EXHAUSTED'; return d, quotients
                local = dict(result, actions=result['actions']-len(d.prefix),
                             executed=result['executed'][len(d.prefix):])
                verdict = search.retain(suffix, local)
                if verdict == 'PROGRESS_WITNESSED':
                    observed = local['executed']
                    if observed not in d.options: d.options.append(observed)
                    d.prefix += observed; d.checkpoint = result['final_sha256']
                    d.stages.append({'level':target+1,'suffix':observed,'prefix':d.prefix,
                                     'actions':result['actions'],'trace_sha256':result['trace_sha256'],
                                     'checkpoint_sha256':d.checkpoint})
                    advanced = True; break
            if advanced: break
        if not advanced:
            d.status = ('TRAINING_BOUND_EXHAUSTED' if d.training_actions >= max_training_actions
                        or d.training_episodes >= max_episodes else 'NO_PROGRESS_WITHIN_BOUND')
            break
    else:
        d.status = 'ALL_LEVELS_WITNESSED'
    return d, quotients


def compare(factory, actions, **kwargs):
    d, quotients = discover(factory, actions, **kwargs)
    budget = kwargs.get('budget',120)
    cold = execute_stage(factory(), (), tuple(actions)*((budget+len(actions)-1)//len(actions)),
                         0,budget,stop_at_progress=False)
    warm = execute_stage(factory(), (), d.prefix,0,budget,stop_at_progress=False)
    matched = cold['initial_sha256'] == warm['initial_sha256'] == d.initial_sha256
    better = warm['levels_completed'] > cold['levels_completed'] or (
        warm['levels_completed'] == cold['levels_completed'] > 0 and warm['actions'] < cold['actions'])
    return {'status':'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'development':d.snapshot(),'quotients':quotients,'cold':cold,'warm':warm,
            'improved':bool(matched and better)}
