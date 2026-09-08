"""Source-blind bounded multi-level development through the public interface.

Each stage replays the previously witnessed prefix from a fresh environment.
Prior successful suffixes are candidate options, never assumed rules. Only an
observed level increment promotes a program. No hidden state or game solutions.
"""
from collections import deque
from dataclasses import dataclass, field
from agent import observation, terminal
from finite_consequence import digest
from restart_development import RestartDevelopment


def execute_stage(env, prefix, suffix, target, budget, checkpoint=None,
                  stop_at_progress=True):
    """Replay a certified prefix, then test a suffix or a complete deployment."""
    prefix, suffix = tuple(prefix), tuple(suffix)
    frame = env.observation_space
    if frame is None:
        frame = env.reset()
    initial = observation(frame)
    trace = []
    def result(status, point=None):
        final = observation(frame)
        close = getattr(env, 'close', None)
        card = close() if callable(close) else None
        if hasattr(card, 'model_dump'):
            card = card.model_dump(mode='json')
        if isinstance(card, dict):
            card.pop('api_key', None)
        return {'status': status, 'initial_sha256': digest(initial),
                'checkpoint_sha256': point, 'final_sha256': digest(final),
                'actions': len(trace), 'progress': max(0, final['levels_completed'] - target),
                'levels_completed': final['levels_completed'], 'state': final['state'],
                'terminal': terminal(final), 'executed': tuple(x[0] for x in trace),
                'trace_sha256': digest(trace), 'scorecard': card,
                'score': card.get('score') if isinstance(card, dict) else None}
    for action in prefix:
        if len(trace) >= budget:
            return result('BUDGET_EXHAUSTED')
        if terminal(observation(frame)):
            return result('PREFIX_TERMINATED')
        frame = env.step(action)
        if frame is None:
            raise RuntimeError('Missing external observation')
        after = observation(frame)
        trace.append((action, after['levels_completed'], after['state']))
    point = digest(observation(frame))
    if observation(frame)['levels_completed'] != target or (checkpoint is not None and point != checkpoint):
        return result('INCONCLUSIVE_PREFIX_MISMATCH', point)
    if target and terminal(observation(frame)):
        return result('PREFIX_TERMINATED', point)
    for action in suffix:
        if len(trace) >= budget:
            return result('BUDGET_EXHAUSTED', point)
        if terminal(observation(frame)):
            break
        frame = env.step(action)
        if frame is None:
            raise RuntimeError('Missing external observation')
        after = observation(frame)
        trace.append((action, after['levels_completed'], after['state']))
        if stop_at_progress and after['levels_completed'] > target:
            break
    return result('PROGRESS_WITNESSED' if observation(frame)['levels_completed'] > target else 'OBSERVED', point)


@dataclass
class MultiLevelDevelopment:
    actions: tuple
    max_depth: int = 8
    prefix: tuple = ()
    checkpoint: object = None
    stages: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    options: list = field(default_factory=list)
    initial_sha256: object = None
    training_actions: int = 0
    training_episodes: int = 0
    status: str = 'NOT_STARTED'

    def snapshot(self):
        return {'status': self.status, 'prefix': self.prefix,
                'levels_witnessed': len(self.stages), 'stages': self.stages,
                'options': self.options, 'training_actions': self.training_actions,
                'training_episodes': self.training_episodes,
                'evidence_sha256': digest(self.evidence),
                'initial_sha256': self.initial_sha256}


def discover_levels(factory, actions, budget=120, max_episodes=512,
                    max_depth=8, max_training_actions=3000, max_levels=5):
    """Return the best witnessed prefix, including on bounded failure."""
    d = MultiLevelDevelopment(tuple(actions), max_depth=max_depth)
    while len(d.stages) < max_levels:
        target = len(d.stages)
        search = RestartDevelopment(d.actions, max_depth=max_depth)
        # Transfer is a hypothesis: test previously successful programs first.
        seeds = [tuple(o) for o in reversed(d.options) if len(o) <= max_depth]
        search.frontier = deque(dict.fromkeys(seeds + list(search.frontier)))
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
            d.evidence.append({'target': target, 'suffix': suffix,
                               'status': result['status'], 'actions': result['actions'],
                               'progress': result['progress'], 'terminal': result['terminal'],
                               'trace_sha256': result['trace_sha256'], 'score': result['score']})
            if result['status'] == 'BUDGET_EXHAUSTED':
                d.status = 'TRAINING_BOUND_EXHAUSTED'
                return d
            local = dict(result, actions=result['actions'] - len(d.prefix),
                         executed=result['executed'][len(d.prefix):])
            verdict = search.retain(suffix, local)
            if verdict == 'PROGRESS_WITNESSED':
                observed_suffix = local['executed']
                if observed_suffix not in d.options:
                    d.options.append(observed_suffix)
                d.prefix += observed_suffix
                d.checkpoint = result['final_sha256']
                d.stages.append({'level': target + 1, 'suffix': observed_suffix,
                                 'prefix': d.prefix, 'actions': result['actions'],
                                 'trace_sha256': result['trace_sha256'],
                                 'checkpoint_sha256': d.checkpoint})
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
                   max_depth=8, max_training_actions=3000, max_levels=5):
    d = discover_levels(factory, actions, budget, max_episodes, max_depth,
                        max_training_actions, max_levels)
    # Both deployments are fresh; the ablation uses the same primitive alphabet.
    cold = execute_stage(factory(), (), tuple(actions) * ((budget + len(actions) - 1)//len(actions)), 0, budget, stop_at_progress=False)
    warm = execute_stage(factory(), (), d.prefix, 0, budget, stop_at_progress=False)
    matched = cold['initial_sha256'] == warm['initial_sha256'] == d.initial_sha256
    better = warm['levels_completed'] > cold['levels_completed'] or (
        warm['levels_completed'] == cold['levels_completed'] > 0 and warm['actions'] < cold['actions'])
    return {'status': 'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'development': d.snapshot(), 'cold': cold, 'warm': warm,
            'improved': bool(matched and better)}
