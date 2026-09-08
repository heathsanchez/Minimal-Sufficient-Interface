"""Small, verifier-gated ARC-compatible controller; no model/API dependency.

A candidate is an action repeated for a bounded number of steps. The only
promotion signal is observed level advancement. A promotion is provisional,
not a proof of general game semantics. Contradictions revoke the active macro.
The controller never reads game source, hidden state, or reference solutions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json


def identity(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class Capability:
    action: int
    evidence: tuple
    identity: str


@dataclass
class Controller:
    actions: tuple
    probe_limit: int = 32
    archive: list = field(default_factory=list)
    rejected: set = field(default_factory=set)
    history: list = field(default_factory=list)
    active: int | None = None
    active_steps: int = 0
    start_level: int = 0
    promotions: int = 0
    revocations: int = 0
    model_calls: int = 0

    def __post_init__(self):
        self.actions = tuple(sorted(set(int(a) for a in self.actions)))
        if not self.actions or self.probe_limit < 1:
            raise ValueError('Nonempty actions and positive bound required')

    def select(self, level):
        if self.active is not None:
            return self.active
        for cap in reversed(self.archive):
            if cap.action not in self.rejected:
                self.active = cap.action
                self.active_steps = 0
                self.start_level = level
                return self.active
        for action in self.actions:
            if action not in self.rejected:
                self.active = action
                self.active_steps = 0
                self.start_level = level
                return action
        # A failed finite probe is not a proof that the action is useless.
        self.rejected.clear()
        self.active = self.actions[0]
        self.active_steps = 0
        self.start_level = level
        return self.active

    def observe(self, before, action, after, state='NOT_PLAYED'):
        if self.active != action:
            raise ValueError('Action does not match selected candidate')
        self.active_steps += 1
        event = (int(before), int(action), int(after), str(state))
        self.history.append(event)
        if after > before:
            evidence = tuple(self.history[-self.active_steps:])
            payload = ('repeat', action, evidence)
            cap = Capability(action, evidence, identity(payload))
            self.archive.append(cap)
            self.promotions += 1
            self.rejected.discard(action)
            self.active = None
            self.active_steps = 0
            return 'PROMOTED'
        if str(state).endswith('GAME_OVER') or self.active_steps >= self.probe_limit:
            self.rejected.add(action)
            if any(c.action == action for c in self.archive):
                self.revocations += 1
            self.active = None
            self.active_steps = 0
            return 'REJECTED_PROVISIONALLY'
        return 'CONTINUE'

    def reset_level(self, level):
        self.active = None
        self.active_steps = 0
        self.start_level = level

    def snapshot(self):
        return {'capabilities': len(self.archive), 'promotions': self.promotions,
                'revocations': self.revocations, 'observations': len(self.history),
                'model_calls': self.model_calls,
                'archive': [c.__dict__ for c in self.archive]}


def run_episode(env, controller, max_actions=300):
    """Use only the public step/observation interface. No hidden game access."""
    frame = env.observation_space
    actions = 0
    resets = 0
    while actions < max_actions:
        state = getattr(frame.state, 'name', str(frame.state))
        if state == 'WIN':
            break
        level = int(frame.levels_completed)
        if state == 'GAME_OVER':
            frame = env.reset()
            resets += 1
            controller.reset_level(int(frame.levels_completed))
            continue
        action = controller.select(level)
        frame = env.step(action)
        if frame is None:
            raise RuntimeError('Environment returned no observation')
        actions += 1
        controller.observe(level, action, int(frame.levels_completed),
                           getattr(frame.state, 'name', str(frame.state)))
    return {'actions': actions, 'levels_completed': int(frame.levels_completed),
            'state': getattr(frame.state, 'name', str(frame.state)), 'resets': resets,
            **controller.snapshot()}
