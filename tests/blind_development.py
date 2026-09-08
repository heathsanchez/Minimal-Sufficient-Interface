"""A target-blind, bounded version-space developer.

This module knows no target names, recurrence equations or proof templates.
The environment owns prediction, observation and certification. An accepted
certificate is not inferred from finite agreement.
"""
from dataclasses import dataclass
from collections import Counter

BASES = ('zero', 'one', 'input')
SOURCE_BOUND = 3
QUERY_DOMAIN = tuple((x, y) for x in range(4) for y in range(5))

@dataclass(frozen=True)
class Program:
    base: str
    step: str
    def source(self):
        return ('iterate', ('step', self.step), ('base', self.base))

@dataclass(frozen=True)
class State:
    steps: tuple[str, ...]
    bound: int = SOURCE_BOUND

@dataclass(frozen=True)
class Observation:
    x: int
    y: int
    value: int

@dataclass(frozen=True)
class Discovery:
    program: Program | None
    certificate: object | None
    observations: tuple[Observation, ...]
    eliminated: tuple
    remaining: tuple[Program, ...]
    checks: int
    reason: str


def candidates(state):
    if state.bound != SOURCE_BOUND or len(set(state.steps)) != len(state.steps):
        raise ValueError('Invalid fixed-grammar state')
    return tuple(Program(b, s) for s in state.steps for b in BASES)


def discover(state, oracle, budget=20, domain=QUERY_DOMAIN):
    """Select separating queries without receiving a target recurrence."""
    if budget < 0:
        raise ValueError('Negative budget')
    remaining = candidates(state)
    observations = []
    eliminated = []
    checks = 0
    while remaining:
        if len(remaining) == 1:
            p = remaining[0]
            decision = oracle.check(p)
            checks += 1
            if decision.accepted:
                return Discovery(p, decision.certificate, tuple(observations),
                                 tuple(eliminated), remaining, checks, 'certified')
            if decision.witness is None:
                return Discovery(None, None, tuple(observations), tuple(eliminated),
                                 remaining, checks, 'unresolved_verifier')
            x, y, value = decision.witness
            observation = Observation(x, y, value)
        else:
            if len(observations) >= budget:
                return Discovery(None, None, tuple(observations), tuple(eliminated),
                                 remaining, checks, 'budget')
            used = {(o.x, o.y) for o in observations}
            choices = []
            for x, y in domain:
                if (x, y) in used:
                    continue
                counts = Counter(oracle.predict(p, x, y) for p in remaining)
                if len(counts) > 1:
                    choices.append((max(counts.values()), -len(counts), x, y))
            if not choices:
                return Discovery(None, None, tuple(observations), tuple(eliminated),
                                 remaining, checks, 'indistinguishable')
            _, _, x, y = min(choices)
            observation = Observation(x, y, oracle.query(x, y))
        if (observation.x, observation.y) in {(o.x, o.y) for o in observations}:
            return Discovery(None, None, tuple(observations), tuple(eliminated),
                             remaining, checks, 'repeated_witness')
        observations.append(observation)
        survivors = []
        for p in remaining:
            if oracle.predict(p, observation.x, observation.y) == observation.value:
                survivors.append(p)
            else:
                eliminated.append((p, observation))
        remaining = tuple(survivors)
    return Discovery(None, None, tuple(observations), tuple(eliminated), (),
                     checks, 'exhausted')
