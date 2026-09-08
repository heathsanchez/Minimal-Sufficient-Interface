"""Generic one-step probe consequences for survival-aware experiment selection.

This does not encode motion, objects, goals, or game-specific actions. Level
progress remains the protected objective. Probe consequences only determine
which experiment to try next when sparse progress has supplied no guidance.
The same finite MSI repair kernel refines probe state when identical abstract
state/action pairs produce different probe consequences.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'convergence'))
from finite_consequence import freeze, synthesize, conflict_count
from agent import Transition, observation
from consequence_selection import ConsequenceController, flat


def probe_consequence(r):
    """Dense observable consequence; no semantic interpretation is attached."""
    src = flat(r.source); dst = flat(r.target)
    changed_cells = sum(a != b for a, b in zip(src, dst)) if len(src) == len(dst) else None
    return (
        r.target.get('state') in ('WIN', 'GAME_OVER'),
        freeze(src) != freeze(dst),
        changed_cells,
    )


@dataclass(frozen=True)
class ProbeEvidence:
    action: object
    state: object
    consequence: object


class ProbeController(ConsequenceController):
    """Develop the experiment policy from immediate public consequences."""
    def __init__(self, actions, probe_enabled=True, **kw):
        super().__init__(tuple(actions), enabled=False, **kw)
        self.probe_enabled = probe_enabled
        self.probe_features = ()
        self.probe_repairs = []
        self.probe_log = []
        self.probe_confirmations = 2

    def probe_state(self, obs, history):
        r = Transition(obs, history, -1, obs, (0, obs['state']))
        return tuple(freeze(c.evaluate(r)) for c in self.probe_features)

    def _probe_key(self, r):
        return (r.action,) + tuple(freeze(c.evaluate(r)) for c in self.probe_features)

    def refresh_probe(self):
        if not self.probe_enabled or len(self.records) < 2:
            return None
        rows = self.records[-self.evidence_limit:]
        target = probe_consequence
        before = conflict_count(rows, self._probe_key, target)
        if not before:
            return None
        existing = {c.name for c in self.probe_features}
        pool = tuple(c for c in self.grammar.candidates(rows, self._probe_key, target)
                     if c.name not in existing)
        repair = synthesize(rows, self._probe_key, target, pool,
                            max_features=2, max_combinations=5000)
        record = {'status': repair.status, 'before': before, 'after': repair.after,
                  'features': [c.name for c in repair.features],
                  'evidence_sha256': repair.evidence_sha256}
        self.probe_repairs.append(record)
        if repair.status == 'FINITE_ADEQUATE':
            self.probe_features += repair.features
        return repair

    def observe(self, before, action, after):
        r = super().observe(before, action, after)
        if self.probe_enabled:
            p = probe_consequence(r)
            self.probe_log.append({'action': action,
                                   'state': freeze(self.probe_state(r.source, r.history)),
                                   'terminal': bool(p[0]), 'changed': bool(p[1]),
                                   'changed_cells': p[2]})
            self.refresh_probe()
        return r

    def _probe_table(self, obs):
        state = freeze(self.probe_state(obs, self.history))
        table = defaultdict(list)
        for r in self.records:
            if freeze(self.probe_state(r.source, r.history)) == state:
                table[r.action].append(probe_consequence(r))
        return state, table

    def choose(self, frame):
        if not self.probe_enabled:
            return super().choose(frame)
        obs = observation(frame)
        # Preserve any externally verified successful program/route first.
        if self.active_script or (not self.history and self._script_candidates(obs)):
            return super().choose(frame)
        state, table = self._probe_table(obs)
        if not table:
            return self.actions[0]

        # Catastrophic observed outcomes are never preferred over a witnessed
        # nonterminal alternative. This is empirical retention, not a game rule.
        safe = []
        for a, outcomes in table.items():
            terminal = sum(int(o[0]) for o in outcomes)
            changed = sum(int(o[1]) for o in outcomes)
            effects = Counter(freeze(o) for o in outcomes)
            repeatability = effects.most_common(1)[0][1] / len(outcomes)
            safe.append((terminal > 0, -changed / len(outcomes), -repeatability,
                         -len(outcomes), self.actions.index(a), a))
        safe.sort()
        best = safe[0]
        best_action = best[-1]
        best_outcomes = table[best_action]

        # Confirm a nonterminal informative experiment before risking an unseen
        # action. Once confirmed, admit one unseen action to gather new evidence.
        if not any(o[0] for o in best_outcomes) and any(o[1] for o in best_outcomes):
            if len(best_outcomes) < self.probe_confirmations:
                return best_action
            unseen = [a for a in self.actions if a not in table]
            if unseen:
                return unseen[0]
            return best_action

        unseen = [a for a in self.actions if a not in table]
        if unseen:
            return unseen[0]
        return best_action

    def snapshot(self):
        return dict(super().snapshot(), probe_enabled=self.probe_enabled,
                    probe_features=[c.name for c in self.probe_features],
                    probe_repairs=self.probe_repairs, probe_log=self.probe_log)
