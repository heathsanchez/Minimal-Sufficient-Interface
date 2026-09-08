"""Inspect actual public consequences before proposing another ARC3 repair.

The previous two schedules both retained level one. This diagnostic keeps the
same immutable source, action catalog, and replay gate. It tests a small,
generic set of existing-option repetitions and primitive probes, preserving
full observations rather than only trace hashes. A changed observation is
not a general rule; it is evidence for the next distinction or experiment.
"""
import argparse
import json
import logging
from pathlib import Path
import subprocess

import numpy as np
import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F


def frame_delta(before, after):
    """Exact array differences; no assumptions about game objects or rules."""
    result = []
    for a, b in zip(before.get('frame', []), after.get('frame', [])):
        x, y = np.asarray(a), np.asarray(b)
        item = {'before_shape': list(x.shape), 'after_shape': list(y.shape)}
        if x.shape != y.shape:
            item['changed_elements'] = None
        else:
            positions = np.argwhere(x != y)
            item['changed_elements'] = int(len(positions))
            item['bounds'] = [[int(positions[:, i].min()), int(positions[:, i].max())]
                              for i in range(positions.shape[1])] if len(positions) else []
        result.append(item)
    return result


def probes(actions, option, max_depth=32, primitive_count=8):
    """Source-derived repetitions plus evenly spread public catalog entries."""
    option = tuple(option)
    if not actions or not option:
        raise ValueError('Nonempty actions and verified option required')
    repeats = [option * n for n in (1,) + F.repetition_counts(max_depth // len(option))]
    repeats = repeats[:8]
    indices = sorted(set(round(i * (len(actions) - 1) / max(1, primitive_count - 1))
                         for i in range(primitive_count)))
    return tuple(dict.fromkeys(repeats + [(actions[i],) for i in indices]))


def run(factory, actions, source, output, max_training_actions=320,
        max_episodes=32, max_depth=32, budget=120, gate=T.run_lean_gate):
    actions = tuple(actions)
    if not actions or min(max_training_actions, max_episodes, max_depth, budget) < 1:
        raise ValueError('Positive bounds and nonempty actions required')
    if source.get('status') != 'COMPARABLE' or source.get('source_commit') != T.FROZEN:
        raise ValueError('Unqualified source')
    if source.get('promotion', {}).get('status') != 'REPLAY_GATED_PROMOTION_PASS' or source['promotion'].get('identity') != M.SOURCE_IDENTITY:
        raise ValueError('Unqualified source promotion')
    stages = source['source_development']['stages']
    if len(stages) != 1 or source['source_development']['prefix'] != stages[0]['prefix']:
        raise ValueError('Unexpected source checkpoint')
    prefix = tuple(map(F.atom, stages[0]['prefix']))
    stage = dict(stages[0], prefix=prefix, suffix=prefix)
    initial, checkpoint = source['initial_sha256'], stage['checkpoint_sha256']
    if len(prefix) > budget or source['cold']['initial_sha256'] != initial:
        raise ValueError('Invalid source bounds or initial observation')
    if source['training_actions'] > max_training_actions:
        raise ValueError('Source exceeds cumulative bound')
    meter = M.ActionMeter(factory, source['training_actions'],
                          source['source_development']['training_episodes'],
                          max_training_actions, max_episodes)
    archive = F.FeedbackArchive()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result = {'status': 'NO_OBSERVATION_CHANGE_WITHIN_BOUND', 'source_run': M.SOURCE_RUN,
              'source_commit': T.FROZEN, 'initial_sha256': initial,
              'checkpoint_sha256': checkpoint, 'grounded_actions': len(actions),
              'source_training_actions': source['training_actions'], 'model_calls': 0,
              'competition_submission': False, 'traces': [], 'accepted': [],
              'terminal_win': False}
    accepted_warm = None

    def finish(status):
        result.update(status=status, training_actions=meter.actions,
                      training_episodes=meter.episodes,
                      installed_options=archive.snapshot()['options'],
                      levels_witnessed=max((a['level'] for a in result['accepted']), default=0))
        if accepted_warm is not None:
            result['warm'] = M.compact(accepted_warm)
        return result

    def replay(path, expected=None):
        path = tuple(path)
        meter.reserve(len(path), 1)
        return F.replay(meter.factory, path, expected, budget)

    # The source is installed only by the real shared gate. Its replay also
    # supplies the exact checkpoint observation for all subsequent comparisons.
    try:
        meter.reserve(2 * len(prefix), 2)
        approval = T.promote(meter.factory, prefix, stage, source['cold'],
                             initial, archive, output / 'source-gate', gate=gate)
    except M.TrainingLimit:
        return finish('TRAINING_BOUND_EXHAUSTED')
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        result['verifier_error'] = str(exc)
        return finish('INCONCLUSIVE_VERIFIER')
    if approval['status'] != 'REPLAY_GATED_PROMOTION_PASS':
        return finish(approval['status'])
    accepted_warm = approval['evidence']['proof']
    result['accepted'].append({'level': 1, 'prefix': prefix,
                               'promotion': approval['identity'],
                               'gate_source_sha256': approval['approval']['source_sha256']})
    entry = accepted_warm['observations'][-1]
    if F.digest(entry) != checkpoint:
        return finish('INCONCLUSIVE_PREFIX_MISMATCH')

    best = None
    for suffix in probes(actions, prefix, max_depth):
        path = prefix + suffix
        if len(path) > budget:
            continue
        try:
            trial = replay(path)
        except M.TrainingLimit:
            result['pending_probe'] = suffix
            break
        if trial['initial_sha256'] != initial or trial['status'] not in ('OBSERVED', 'OBSERVED_TERMINAL_PREFIX'):
            return finish('INCONCLUSIVE_REPLAY')
        if tuple(trial['executed'][:len(prefix)]) != prefix or F.digest(trial['observations'][len(prefix)]) != checkpoint:
            return finish('INCONCLUSIVE_PREFIX_MISMATCH')
        actual = tuple(trial['executed'][len(prefix):])
        observed = trial['observations'][len(prefix):]
        hashes = [F.digest(o) for o in observed]
        novelty = len(set(hashes[1:]) - {hashes[0]})
        first_change = next((i for i, h in enumerate(hashes[1:], 1) if h != hashes[0]), None)
        record = {'requested': suffix, 'executed': actual, 'status': trial['status'],
                  'initial_sha256': trial['initial_sha256'], 'final_sha256': trial['final_sha256'],
                  'levels_completed': trial['levels_completed'], 'state': trial['state'],
                  'novel_observations': novelty, 'first_change': first_change,
                  'delta': frame_delta(entry, observed[-1]), 'observations': observed}
        result['traces'].append(record)
        score = (trial['state'] == 'WIN', trial['levels_completed'], novelty, -len(actual))
        if best is None or score > best[0]:
            best = (score, record, trial)
        if trial['levels_completed'] > 1 or trial['state'] == 'WIN':
            break

    if best is None:
        return finish('TRAINING_BOUND_EXHAUSTED' if result.get('pending_probe') else 'NO_OBSERVATION_CHANGE_WITHIN_BOUND')
    _, record, trial = best
    result['selected_probe'] = {k: v for k, v in record.items() if k != 'observations'}
    # A fresh replay confirms the actual selected history. No unverified
    # nonterminal observation is installed as a general policy or world rule.
    actual_path = prefix + tuple(record['executed'])
    try:
        proof = replay(actual_path, trial['final_sha256'])
    except M.TrainingLimit:
        result['pending_proof'] = actual_path
        return finish('TRAINING_BOUND_EXHAUSTED')
    if (proof['status'] not in ('OBSERVED', 'OBSERVED_TERMINAL_PREFIX')
            or proof['executed'] != trial['executed']
            or proof['observations'] != trial['observations']
            or proof['initial_sha256'] != initial):
        return finish('INCONCLUSIVE_REPLAY')
    result['selected_probe']['replay_confirmed'] = True
    if trial['levels_completed'] <= 1 and trial['state'] != 'WIN':
        return finish('OBSERVED_RESIDUAL' if record['novel_observations'] else 'NO_OBSERVATION_CHANGE_WITHIN_BOUND')

    stage = {'level': trial['levels_completed'], 'prefix': actual_path,
             'checkpoint_sha256': trial['final_sha256']}
    try:
        meter.reserve(2 * len(actual_path), 2)
        promotion = T.promote(meter.factory, actual_path, stage, source['cold'],
                              initial, archive, output / 'new-gate', gate=gate)
    except M.TrainingLimit:
        result['pending_promotion'] = actual_path
        return finish('TRAINING_BOUND_EXHAUSTED')
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        result['verifier_error'] = str(exc)
        return finish('INCONCLUSIVE_VERIFIER')
    if promotion['status'] != 'REPLAY_GATED_PROMOTION_PASS':
        return finish(promotion['status'])
    accepted_warm = promotion['evidence']['proof']
    result['accepted'].append({'level': stage['level'], 'prefix': actual_path,
                               'promotion': promotion['identity'],
                               'gate_source_sha256': promotion['approval']['source_sha256']})
    result['terminal_win'] = accepted_warm['state'] == 'WIN'
    return finish('VERIFIED_WIN' if result['terminal_win'] else 'PROGRESS_WITNESSED')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-evidence', required=True)
    p.add_argument('--frozen-dir', required=True)
    p.add_argument('--environments-dir', required=True)
    p.add_argument('--game', default='bt33-a7c3f9d18b4e')
    p.add_argument('--output', default='arc3-observation-probe.json')
    a = p.parse_args()
    _, _, grounding, _, _ = T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('arc3-observation-probe')
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
    result = run(factory, actions, source, Path(a.output).parent / 'observation-gate')
    result.update(game=a.game, mode='offline', unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM, source_blobs=T.SOURCE_BLOBS,
                  comparison_runs=[34244268321, 34269636463])
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
    print('ARC3_OBSERVATION_PROBE=' + json.dumps({k: result.get(k) for k in
          ('status', 'training_actions', 'training_episodes', 'installed_options',
           'levels_witnessed', 'terminal_win')}, sort_keys=True))


if __name__ == '__main__':
    main()
