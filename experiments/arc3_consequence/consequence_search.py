"""Bounded, source-blind development of the search procedure.

A measured quotient orders experiments; it never deletes an action. Witnessed
programs supply reusable factors. Every candidate is executed through the
public interface, and only observed progress installs a new option. The
original controller is retained as an ablation.
"""
from collections import defaultdict
from heapq import heappush, heappop
from itertools import count
from math import ceil, log2
from multi_level_development import MultiLevelDevelopment, execute_stage
from restart_development import RestartDevelopment
from consequence_quotient import measure, BAD
from finite_consequence import digest


def ordered_actions(classes):
    """Fairly enumerate every member, favouring small observed classes first."""
    groups = [tuple(c['members']) for c in sorted(classes, key=lambda c: len(c['members']))]
    result = []
    for i in range(max(map(len, groups), default=0)):
        result.extend(g[i] for g in groups if i < len(g))
    return tuple(dict.fromkeys(tuple(a) if isinstance(a, list) else a for a in result))


def factors(program, bound=32):
    """Generic run and repeated-block factors, not inferred game rules."""
    p = tuple(program)
    out = set()
    if len(p) < 2:
        return ()
    i = 0
    while i < len(p):
        j = i + 1
        while j < len(p) and p[j] == p[i]:
            j += 1
        if j - i > 1:
            out.add(p[i:j])
        i = j
    for size in range(1, min(len(p)//2, bound) + 1):
        for start in range(len(p)-2*size+1):
            block = p[start:start+size]
            if p[start+size:start+2*size] == block:
                out.add(block)
                out.add(block*2)
    return tuple(sorted((x for x in out if 1 < len(x) <= bound), key=lambda x:(len(x),x)))


class RankedSearch(RestartDevelopment):
    """Search by program description cost, retaining the complete action set."""
    def __init__(self, actions, options=(), max_depth=32):
        super().__init__(tuple(actions), max_depth=max_depth)
        self.rank = {a:i for i,a in enumerate(self.actions)}
        self.options = tuple(dict.fromkeys(tuple(o) for o in options if 1 < len(o) <= max_depth))
        self.frontier = []
        self.best = {}
        self.seen = set()
        self.serial = count()
        for o in self.options:
            self._add(o, 1)
            for n in range(2, max_depth//len(o)+1):
                self._add(o*n, 2+ceil(log2(n)))
        for a in self.actions:
            self._add((a,), self.atom_cost(a))

    def atom_cost(self, action):
        return 1 + ceil(log2(self.rank[action]+1))

    def _add(self, program, cost):
        p = tuple(program)
        if not p or len(p) > self.max_depth or p in self.seen:
            return
        if cost < self.best.get(p, float('inf')):
            self.best[p] = cost
            heappush(self.frontier, (cost, len(p), next(self.serial), p))

    def propose(self):
        while self.frontier:
            cost, _, _, p = heappop(self.frontier)
            if p not in self.seen and self.best.get(p) == cost:
                self.seen.add(p)
                return p
        return None

    def retain(self, program, result):
        p = tuple(program)
        cost = self.best[p]
        verdict = super().retain(p, result)
        if verdict == 'NONTERMINAL_PREFIX':
            for o in self.options:
                self._add(p+o, cost+1)
            for n in range(2, self.max_depth//len(p)+1):
                self._add(p*n, cost+1+ceil(log2(n)))
            for a in self.actions:
                self._add(p+(a,), cost+self.atom_cost(a))
        return verdict


def discover(factory, actions, budget=120, max_episodes=2048, max_depth=32,
             max_training_actions=20000, max_levels=5, horizon=4):
    d = MultiLevelDevelopment(tuple(actions), max_depth=max_depth)
    quotients = []
    operators = []
    while len(d.stages) < max_levels:
        target = len(d.stages)
        q = measure(factory, d.actions, d.prefix, target, d.checkpoint, budget,
                    horizon, max_training_actions-d.training_actions,
                    max_episodes-d.training_episodes)
        d.training_actions += q['actions']; d.training_episodes += q['episodes']
        if d.initial_sha256 is None:
            d.initial_sha256 = q['initial_sha256']
        if q['initial_sha256'] != d.initial_sha256 or q['status'].startswith('INCONCLUSIVE'):
            d.status = 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX'
            break
        if q['status'] != 'OBSERVED_QUOTIENT':
            d.status = 'TRAINING_BOUND_EXHAUSTED'
            break
        quotients.append(q)
        alphabet = ordered_actions(q['classes'])
        # The only new operators are generic factor reuse and ranked expansion.
        # Their installation is provisional until the external comparison.
        options = tuple(dict.fromkeys(tuple(o) for o in d.options +
                                      [f for o in d.options for f in factors(o, max_depth)]))
        search = RankedSearch(alphabet, options, max_depth)
        operators.append({'target':target,'policy':'ranked-factor-v1',
                          'alphabet_size':len(alphabet),'options':len(options),
                          'quotient_sha256':q['evidence_sha256']})
        advanced = False
        while d.training_episodes < max_episodes and d.training_actions < max_training_actions:
            suffix = search.propose()
            if suffix is None:
                break
            remaining = min(budget, max_training_actions-d.training_actions)
            if remaining <= len(d.prefix):
                break
            result = execute_stage(factory(), d.prefix, suffix, target, remaining, d.checkpoint)
            d.training_episodes += 1
            d.training_actions += result['actions']
            if result['initial_sha256'] != d.initial_sha256 or result['status'] in BAD:
                d.status = 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX'
                return d, quotients, operators
            d.evidence.append({'target':target,'suffix':suffix,'status':result['status'],
                               'actions':result['actions'],'trace_sha256':result['trace_sha256']})
            if result['status'] == 'BUDGET_EXHAUSTED':
                break
            local = dict(result, actions=result['actions']-len(d.prefix),
                         executed=result['executed'][len(d.prefix):])
            verdict = search.retain(suffix, local)
            if verdict == 'PROGRESS_WITNESSED':
                observed = local['executed']
                if observed not in d.options:
                    d.options.append(observed)
                d.prefix += observed
                d.checkpoint = result['final_sha256']
                d.stages.append({'level':target+1,'suffix':observed,'prefix':d.prefix,
                                 'actions':result['actions'],'trace_sha256':result['trace_sha256'],
                                 'checkpoint_sha256':d.checkpoint})
                advanced = True
                break
        if not advanced:
            d.status = ('TRAINING_BOUND_EXHAUSTED' if d.training_actions >= max_training_actions
                        or d.training_episodes >= max_episodes else 'NO_PROGRESS_WITHIN_BOUND')
            break
    else:
        d.status = 'ALL_LEVELS_WITNESSED'
    return d, quotients, operators


def compare(factory, actions, **kwargs):
    d, quotients, operators = discover(factory, actions, **kwargs)
    budget = kwargs.get('budget',120)
    cold = execute_stage(factory(), (), tuple(actions)*((budget+len(actions)-1)//len(actions)),
                         0,budget,stop_at_progress=False)
    warm = execute_stage(factory(), (), d.prefix,0,budget,stop_at_progress=False)
    matched = cold['initial_sha256'] == warm['initial_sha256'] == d.initial_sha256
    better = warm['levels_completed'] > cold['levels_completed'] or (
        warm['levels_completed'] == cold['levels_completed'] > 0 and warm['actions'] < cold['actions'])
    return {'status':'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'development':d.snapshot(),'quotients':quotients,'operators':operators,
            'cold':cold,'warm':warm,'improved':bool(matched and better)}
