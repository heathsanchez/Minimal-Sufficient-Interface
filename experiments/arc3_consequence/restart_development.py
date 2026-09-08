"""Source-blind restart development. Failed episodes are evidence, not amnesia.

The controller searches action programs through the public interface. A prefix
is expanded only after its replay is nonterminal. Progress is the only success
criterion; survival is a secondary experimental resource, not a game goal.
No game state, motion rule, or successful sequence is supplied in advance.
"""
from collections import deque
from dataclasses import dataclass, field
from agent import observation, terminal
from finite_consequence import digest, freeze


def execute(env, program, budget):
    frame = env.observation_space
    if frame is None: frame = env.reset()
    initial = observation(frame)
    trace = []
    for action in tuple(program)[:budget]:
        if terminal(observation(frame)): break
        before = observation(frame)
        frame = env.step(action)
        if frame is None: raise RuntimeError('Missing external observation')
        after = observation(frame)
        trace.append((action, after['levels_completed'], after['state']))
        if after['levels_completed'] > initial['levels_completed']: break
    final = observation(frame)
    return {'initial_sha256':digest(initial), 'actions':len(trace),
            'progress':final['levels_completed']-initial['levels_completed'],
            'state':final['state'], 'terminal':terminal(final),
            'trace_sha256':digest(trace), 'executed':tuple(x[0] for x in trace),
            'final':final}


@dataclass
class RestartDevelopment:
    actions: tuple
    max_depth: int = 8
    frontier: object = field(default_factory=deque)
    evidence: list = field(default_factory=list)
    successful: list = field(default_factory=list)
    rejected: set = field(default_factory=set)
    expanded: set = field(default_factory=set)

    def __post_init__(self):
        self.actions = tuple(self.actions)
        if not self.frontier:
            self.frontier = deque((a,) for a in self.actions)

    def propose(self):
        while self.frontier:
            p = self.frontier.popleft()
            if p not in self.rejected: return p
        return None

    def retain(self, program, result):
        program = tuple(program)
        record = {'program':program, 'progress':result['progress'],
                  'terminal':result['terminal'], 'actions':result['actions'],
                  'initial_sha256':result['initial_sha256'],
                  'trace_sha256':result['trace_sha256']}
        self.evidence.append(record)
        if result['progress'] > 0:
            p = result['executed']
            if p not in self.successful: self.successful.append(p)
            return 'PROGRESS_WITNESSED'
        if result['terminal']:
            self.rejected.add(program)
            return 'TERMINAL_PREFIX'
        if result['actions'] != len(program):
            return 'INCONCLUSIVE'
        if len(program) < self.max_depth and program not in self.expanded:
            self.expanded.add(program)
            self.frontier.extend(program+(a,) for a in self.actions)
        return 'NONTERMINAL_PREFIX'

    def snapshot(self):
        return {'episodes':len(self.evidence), 'frontier':len(self.frontier),
                'terminal_prefixes':len(self.rejected), 'nonterminal_prefixes':len(self.expanded),
                'successful_programs':len(self.successful), 'evidence_sha256':digest(self.evidence)}


def discover(factory, actions, episode_budget=120, max_episodes=128, max_depth=8):
    d = RestartDevelopment(tuple(actions),max_depth=max_depth)
    initial_sha = None
    total_actions = 0
    for _ in range(max_episodes):
        p = d.propose()
        if p is None: break
        result = execute(factory(),p,episode_budget)
        if initial_sha is None: initial_sha = result['initial_sha256']
        if result['initial_sha256'] != initial_sha:
            return {'status':'INCONCLUSIVE_UNMATCHED_START', 'development':d,
                    'training_actions':total_actions}
        total_actions += result['actions']
        status = d.retain(p,result)
        if status == 'PROGRESS_WITNESSED':
            return {'status':status,'development':d,'program':d.successful[-1],
                    'training_actions':total_actions,'initial_sha256':initial_sha}
    return {'status':'NO_PROGRESS_WITHIN_BOUND','development':d,
            'training_actions':total_actions,'initial_sha256':initial_sha}


def compare(factory, actions, budget=120, max_episodes=128, max_depth=8):
    """Fresh-start qualification; a training success is never a holdout success."""
    learned = discover(factory,actions,budget,max_episodes,max_depth)
    d = learned['development']
    candidate = learned.get('program')
    # No promoted program means no claim of improvement. Retain the negative.
    if candidate is None:
        return {'status':learned['status'],'training_actions':learned['training_actions'],
                'development':d.snapshot(),'improved':False}
    baseline = execute(factory(),tuple(actions) * ((budget+len(actions)-1)//len(actions)),budget)
    proposed = execute(factory(),candidate,budget)
    matched = baseline['initial_sha256'] == proposed['initial_sha256'] == learned['initial_sha256']
    better = proposed['progress'] > baseline['progress'] or (proposed['progress'] == baseline['progress'] and proposed['progress'] > 0 and proposed['actions'] < baseline['actions'])
    return {'status':'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'training_actions':learned['training_actions'], 'development':d.snapshot(),
            'candidate':candidate,'baseline':baseline,'proposed':proposed,
            'improved':bool(matched and better), 'qualification':'VERIFIED_IMPROVEMENT' if matched and better else 'REJECTED_OR_INCONCLUSIVE'}
