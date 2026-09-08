"""Resume stage four from verified evidence; never infer a game solution from pixels.

The old source and search grammar remain frozen. Prior observations nominate
experiments, not rules. Fresh execution and the existing Lean gate own promotion.
"""
import argparse
import hashlib
import json
import logging
from collections import deque
from pathlib import Path

import arc3_stage4_probe as P
import arc3_archive_transfer as A
import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F

RESIDUAL_RUN = 34277495372
RESIDUAL_SHA256 = '9c0ae1e1efbd4cbe269e7b619370a65c579bc25f2a7a83c980800763c2572197'


def separator_programs(source, report, transfer, evidence, residual, actions, bound=16):
    """Choose shortest representatives of distinct actual effects, not target labels."""
    entry = P.verified_entry(source, report, transfer, evidence, actions)
    checkpoint = F.digest(entry)
    stages = A.select_archive(report, source, actions)
    if (residual.get('source_run') != M.SOURCE_RUN
            or residual.get('archive_run') != A.ARCHIVE_RUN
            or residual.get('transfer_run') != P.TRANSFER_RUN
            or residual.get('source_commit') != T.FROZEN
            or residual.get('initial_sha256') != source['initial_sha256']
            or residual.get('checkpoint_sha256') != checkpoint
            or residual.get('levels_witnessed') != len(stages)
            or residual.get('new_discoveries') != 0
            or residual.get('status') not in ('NO_PROGRESS_WITHIN_BOUND', 'TRAINING_BOUND_EXHAUSTED')
            or residual.get('terminal_win')
            or len(residual.get('accepted', ())) != len(stages)
            or residual.get('warm') != transfer['warm']):
        raise ValueError('Unqualified residual source')
    # Independent replays can have different evidence/certificate identities.
    # Preserve the protected consequence, and require a gate record in each run.
    for old, new in zip(transfer['accepted'], residual['accepted']):
        for key in ('level', 'prefix', 'suffix', 'checkpoint_sha256'):
            if old.get(key) != new.get(key):
                raise ValueError('Archived protected consequence changed')
        if not old.get('promotion') or not new.get('promotion') or not old.get('gate_source_sha256') or not new.get('gate_source_sha256'):
            raise ValueError('Missing archived promotion evidence')
    # The prior experiment extended the old alphabet using public pixels.
    # Verify that constructor, rather than silently treating it as an old action.
    alphabet = set(map(F.atom, actions))
    alphabet.update(P.component_actions(entry, entry['available_actions']))
    groups = {}
    for row in residual.get('diagnostic_rows', ()):
        program = tuple(map(F.atom, row['program']))
        observations = row['observations']
        hashes = tuple(map(F.digest, observations))
        if (not program or any(a not in alphabet for a in program)
                or len(observations) != len(program) + 1
                or tuple(row['observed_hashes']) != hashes
                or hashes[0] != checkpoint
                or row['changed'] != (len(set(hashes)) > 1)):
            raise ValueError('Malformed observed consequence')
        after = observations[-1]
        if after['levels_completed'] != len(stages) or after['state'] != 'NOT_FINISHED':
            raise ValueError('Unexpected protected consequence')
        if len(program) == 1 and hashes[-1] != checkpoint:
            groups.setdefault(hashes[-1], set()).add(program)
    representatives = tuple(min(group, key=lambda p: (len(p), p))
                            for _, group in sorted(groups.items(), key=lambda kv: (len(kv[1]), kv[0])))[:4]
    programs = []
    for p in representatives:
        programs.extend(p * n for n in (1, 2, 4, 8, 16) if len(p) * n <= bound)
    for i, a in enumerate(representatives):
        for b in representatives[i+1:]:
            for p in (a+b, b+a):
                programs.extend(p*n for n in (1, 2, 4) if len(p)*n <= bound)
    return representatives, tuple(dict.fromkeys(programs))


def separator_search(stages, programs, representatives, diagnostics=None):
    """The existing search interface, with evidence-selected bounded programs."""
    if diagnostics is None:
        diagnostics = []
    class Search:
        def __init__(self, actions, options=(), max_depth=16):
            self.max_depth = max_depth
            self.seen = set()
            self.frontier = deque()
            self.effects = set()
            prefix = tuple(a for option in options for a in option)
            for stage in stages:
                full = tuple(map(F.atom, stage['prefix']))
                suffix = tuple(map(F.atom, stage['suffix']))
                if full[:len(prefix)] == prefix and len(full) > len(prefix):
                    if full == prefix + suffix and len(suffix) <= max_depth:
                        self.frontier.append(suffix)
                    return
            if prefix == tuple(map(F.atom, stages[-1]['prefix'])):
                self.frontier = deque(p for p in programs if len(p) <= max_depth)
        def propose(self):
            while self.frontier:
                p = self.frontier.popleft()
                if p not in self.seen:
                    self.seen.add(p)
                    return p
            return None
        def retain(self, program, result):
            if result.get('progress', 0) > 0:
                return 'PROGRESS_WITNESSED'
            if result.get('terminal'):
                return 'TERMINAL_PREFIX'
            actual = tuple(result['executed'])
            observations = result.get('suffix_observations', ())
            if not actual or len(observations) != len(actual) + 1:
                return 'INCONCLUSIVE'
            hashes = tuple(map(F.digest, observations))
            diagnostics.append({'program': actual, 'observed_hashes': hashes,
                                'observations': observations})
            new = set(hashes[1:]) - {hashes[0]} - self.effects
            self.effects.update(hashes[1:])
            if new:
                additions = [actual * n for n in (2, 4) if len(actual)*n <= self.max_depth]
                for other in representatives:
                    additions.extend((actual+other, other+actual))
                self.frontier.extendleft(reversed([p for p in dict.fromkeys(additions)
                                                   if len(p) <= self.max_depth and p not in self.seen]))
            return 'NONTERMINAL_PREFIX'
    return Search


def run(factory, actions, source, report, transfer, evidence, residual, execute_stage, output,
        max_training_actions=1200, max_episodes=64, gate=T.run_lean_gate):
    representatives, programs = separator_programs(source, report, transfer, evidence, residual, actions)
    stages = A.select_archive(report, source, actions)
    diagnostics = []
    search = separator_search(stages, programs, representatives, diagnostics)
    result = M.continue_verified(factory, actions, source, search, P.observed_stage(execute_stage), output,
                                 max_training_actions=max_training_actions, max_episodes=max_episodes,
                                 max_depth=16, budget=120, max_levels=4, gate=gate)
    result.update(residual_run=RESIDUAL_RUN, archive_run=A.ARCHIVE_RUN, transfer_run=P.TRANSFER_RUN,
                  transfer_kind='replay_of_prior_witnesses_then_separator',
                  residual_training_actions=residual.get('training_actions'),
                  representatives=representatives, candidate_programs=programs,
                  diagnostic_rows=diagnostics, archived_levels=len(stages),
                  new_discoveries=max(0, len(result.get('accepted', ())) - len(stages)))
    warm = result.get('warm', {})
    result['improved_over_archive'] = bool(warm.get('initial_sha256') == source['initial_sha256']
                                           and T.quality(warm) > T.quality(transfer['warm']))
    return result


def main():
    p = argparse.ArgumentParser()
    for name in ('source', 'archive', 'transfer', 'stage', 'residual'):
        p.add_argument('--'+name+'-evidence', required=True)
    p.add_argument('--frozen-dir', required=True)
    p.add_argument('--environments-dir', required=True)
    p.add_argument('--game', default='bt33-a7c3f9d18b4e')
    p.add_argument('--output', default='arc3-stage4-separator.json')
    a = p.parse_args()
    _, _, grounding, _, multilevel = T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('arc3-stage4-separator')
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=a.environments_dir, logger=logger)
        env = arcade.make(a.game)
        if env is None:
            raise RuntimeError('Environment unavailable')
        class Adapter:
            @property
            def observation_space(self): return env.observation_space
            @property
            def action_space(self): return env.action_space
            def reset(self): return env.reset()
            def step(self, action):
                kind, data = grounding.decode(action)
                return env.step(kind, data=data)
            def close(self): return arcade.close_scorecard()
        return Adapter()
    first = factory()
    actions, unsupported = grounding.action_catalog(first.action_space, first.observation_space, 8, 256)
    first.close()
    def read(path): return json.loads(Path(path).read_text())
    if hashlib.sha256(Path(a.residual_evidence).read_bytes()).hexdigest() != RESIDUAL_SHA256:
        raise ValueError('Residual evidence SHA256 mismatch')
    result = run(factory, actions, read(a.source_evidence), read(a.archive_evidence),
                 read(a.transfer_evidence), read(a.stage_evidence), read(a.residual_evidence),
                 multilevel.execute_stage, Path(a.output).parent/'separator-gate')
    result.update(game=a.game, mode='offline', unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM, source_blobs=T.SOURCE_BLOBS)
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str)+'\n')
    print('ARC3_STAGE4_SEPARATOR='+json.dumps({k:result.get(k) for k in
          ('status','training_actions','training_episodes','levels_witnessed',
           'installed_options','new_discoveries','improved_over_archive','terminal_win')},sort_keys=True))

if __name__ == '__main__':
    main()
