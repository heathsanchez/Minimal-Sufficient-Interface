"""Source-blind checkpoint quotient with bounded, reversible search.

Classes are local observations, not universal action laws. Recompute at every
checkpoint; retain the full alphabet and count every measurement and replay.
"""
from collections import defaultdict
from multi_level_development import MultiLevelDevelopment, execute_stage
from compositional_development import OptionSearch
from finite_consequence import digest

BAD = ('INCONCLUSIVE_PREFIX_MISMATCH', 'PREFIX_TERMINATED')


def measure(factory, actions, prefix, target, checkpoint, budget, horizon=4,
            remaining_actions=20000, remaining_episodes=2048):
    if not actions or horizon < 1:
        raise ValueError('Nonempty alphabet and positive horizon required')
    groups = defaultdict(list)
    rows = []
    spent = episodes = 0
    initial = None
    for action in actions:
        if (len(prefix)+horizon > budget or episodes >= remaining_episodes
                or spent+len(prefix)+horizon > remaining_actions):
            return {'status':'BOUND_EXHAUSTED','rows':rows,'actions':spent,
                    'episodes':episodes,'initial_sha256':initial}
        result = execute_stage(factory(), prefix, (action,)*horizon, target,
                               len(prefix)+horizon, checkpoint, stop_at_progress=False)
        spent += result['actions']; episodes += 1
        if initial is None: initial = result['initial_sha256']
        if result['initial_sha256'] != initial or result['status'] in BAD:
            return {'status':'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX','rows':rows,
                    'actions':spent,'episodes':episodes,'initial_sha256':initial}
        # Action identity is excluded. The external consequence, including
        # early termination, determines the observed equivalence class.
        key = digest((result['actions']-len(prefix), result['progress'],
                      result['state'], result['final_sha256']))
        groups[key].append(action)
        rows.append({'action':action,'consequence':key,'trace_sha256':result['trace_sha256']})
    classes = [{'representative':members[0], 'members':members} for members in groups.values()]
    return {'status':'OBSERVED_QUOTIENT','classes':classes,'rows':rows,
            'actions':spent,'episodes':episodes,'initial_sha256':initial,
            'evidence_sha256':digest(rows),'horizon':horizon}


def discover(factory, actions, budget=120, max_episodes=2048, max_depth=32,
             max_training_actions=20000, max_levels=5, horizon=4,
             reduced_fraction=0.75):
    if not actions or not 0 < reduced_fraction < 1:
        raise ValueError('Nonempty alphabet and a genuine fallback reserve required')
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
        # Reserve part of the remaining budget for the original alphabet.
        available = max_training_actions-d.training_actions
        available_episodes = max_episodes-d.training_episodes
        reduced_limit = d.training_actions+int(available*reduced_fraction)
        reduced_episode_limit = d.training_episodes+int(available_episodes*reduced_fraction)
        for name, alphabet, limit, episode_limit in (
                ('reduced',reduced,reduced_limit,reduced_episode_limit),
                ('full',d.actions,max_training_actions,max_episodes)):
            search = OptionSearch(alphabet, d.options, max_depth=max_depth)
            while d.training_episodes < episode_limit and d.training_actions < limit:
                suffix = search.propose()
                if suffix is None: break
                remaining = min(budget, limit-d.training_actions)
                if remaining <= len(d.prefix): break
                result = execute_stage(factory(), d.prefix, suffix, target, remaining, d.checkpoint)
                d.training_episodes += 1; d.training_actions += result['actions']
                if result['initial_sha256'] != d.initial_sha256 or result['status'] in BAD:
                    d.status = 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX'
                    return d, quotients
                d.evidence.append({'target':target,'alphabet':name,'suffix':suffix,
                                   'status':result['status'],'actions':result['actions'],
                                   'trace_sha256':result['trace_sha256']})
                if result['status'] == 'BUDGET_EXHAUSTED':
                    break
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
