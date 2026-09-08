"""Replay prior verified discoveries through the existing shared controller.

This is archive transfer, not a new solve. Candidate programs come exclusively
from a pinned prior experiment, never from game implementation or fixture rules.
Every accepted stage is freshly executed and promoted by the existing Lean gate.
"""
import argparse
import json
import logging
from pathlib import Path
from collections import deque

import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F

ARCHIVE_RUN = 34192005884
ARCHIVE_COMMIT = 'c65201683d0eccd8a03e07abb9ba35409419cf14'
ARCHIVE_SHA256 = '820aafb2e9b676d4565dcbe6c8324c6d1dd91b8d7a16caca3a7e0f45c8c48403'


def select_archive(report, source, actions):
    """Validate provenance and return only the archived executed suffixes."""
    if report.get('status') != 'COMPARABLE' or report.get('model_calls') != 0:
        raise ValueError('Unqualified archive')
    if report.get('competition_submission') or report.get('game') != 'bt33-a7c3f9d18b4e':
        raise ValueError('Archive scope mismatch')
    if report.get('initial_sha256') != source.get('initial_sha256'):
        raise ValueError('Initial observation mismatch')
    policy = report['selected_policy']
    record = report['policies'][policy]
    if record.get('status') != 'COMPARABLE':
        raise ValueError('Selected policy is not comparable')
    stages = record['development']['stages']
    if not stages or record['development']['initial_sha256'] != report['initial_sha256']:
        raise ValueError('Missing development evidence')
    prior = ()
    alphabet = set(map(F.atom, actions))
    for level, stage in enumerate(stages, 1):
        prefix = tuple(map(F.atom, stage['prefix']))
        suffix = tuple(map(F.atom, stage['suffix']))
        if (stage['level'] != level or not suffix or prefix != prior + suffix
                or any(a not in alphabet for a in suffix)
                or not stage.get('checkpoint_sha256')):
            raise ValueError('Malformed archived stage')
        prior = prefix
    warm = record['warm']
    if (tuple(map(F.atom, warm['executed'])) != prior
            or warm['final_sha256'] != stages[-1]['checkpoint_sha256']
            or warm['levels_completed'] != len(stages)):
        raise ValueError('Archive deployment does not match its witnesses')
    first = source['source_development']['stages'][0]
    if (tuple(map(F.atom, first['prefix'])) != tuple(map(F.atom, stages[0]['prefix']))
            or first['checkpoint_sha256'] != stages[0]['checkpoint_sha256']):
        raise ValueError('Archive does not extend the accepted source')
    return stages


def archive_search(stages):
    """Adapt existing certified candidates to the frozen search interface."""
    class ArchiveSearch:
        def __init__(self, actions, options=(), max_depth=32):
            self.frontier = deque()
            prefix = tuple(a for option in options for a in option)
            for stage in stages:
                full = tuple(map(F.atom, stage['prefix']))
                suffix = tuple(map(F.atom, stage['suffix']))
                if full[:len(prefix)] == prefix and len(full) > len(prefix):
                    if len(suffix) <= max_depth and full == prefix + suffix:
                        self.frontier.append(suffix)
                    break
        def propose(self):
            return self.frontier.popleft() if self.frontier else None
        def retain(self, program, result):
            return 'NO_PROGRESS_WITHIN_BOUND'
    return ArchiveSearch


def run(factory, actions, source, report, execute_stage, output,
        max_training_actions=160, max_episodes=24, gate=T.run_lean_gate):
    stages = select_archive(report, source, actions)
    result = M.continue_verified(
        factory, actions, source, archive_search(stages), execute_stage, output,
        max_training_actions=max_training_actions, max_episodes=max_episodes,
        max_depth=32, budget=120, max_levels=len(stages), gate=gate)
    result.update(archive_run=ARCHIVE_RUN, archive_commit=ARCHIVE_COMMIT,
                  archive_policy=report['selected_policy'],
                  archive_training_actions=report['policies'][report['selected_policy']]['development']['training_actions'],
                  archive_training_episodes=report['policies'][report['selected_policy']]['development']['training_episodes'],
                  transfer_kind='replay_of_prior_witnesses', new_discoveries=0)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-evidence', required=True)
    p.add_argument('--archive-evidence', required=True)
    p.add_argument('--frozen-dir', required=True)
    p.add_argument('--environments-dir', required=True)
    p.add_argument('--game', default='bt33-a7c3f9d18b4e')
    p.add_argument('--output', default='arc3-archive-transfer.json')
    a = p.parse_args()
    _, _, grounding, _, multilevel = T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('arc3-archive-transfer')
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade = Arcade(operation_mode=OperationMode.OFFLINE,
                        environments_dir=a.environments_dir, logger=logger)
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
    source = json.loads(Path(a.source_evidence).read_text())
    report = json.loads(Path(a.archive_evidence).read_text())
    result = run(factory, actions, source, report, multilevel.execute_stage,
                 Path(a.output).parent / 'archive-gate')
    result.update(game=a.game, mode='offline', unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM, source_blobs=T.SOURCE_BLOBS)
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
    print('ARC3_ARCHIVE_TRANSFER=' + json.dumps({k:result.get(k) for k in
          ('status','training_actions','levels_witnessed','installed_options','terminal_win')}, sort_keys=True))

if __name__ == '__main__':
    main()
