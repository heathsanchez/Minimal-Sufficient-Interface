"""Continue a certified ARC3 policy from its replayed checkpoint.

The frozen option search proposes suffixes; the existing external promotion
checks each new consequence before it enters the shared archive. No game rules
or winning sequences are supplied. Every interaction, including verification,
is charged to the bounded experiment.
"""
import argparse
import json
import logging
from pathlib import Path
import subprocess

import arc3_shared_transfer as T


def atoms(program):
    return tuple(T.F.atom(a) for a in program)


def verify_source(source, game, identity):
    if (source.get('status') != 'COMPARABLE'
            or source.get('game') != game
            or source.get('source_commit') != T.FROZEN
            or source.get('upstream_commit') != T.UPSTREAM
            or source.get('source_blobs') != T.SOURCE_BLOBS):
        raise ValueError('Source identity or provenance mismatch')
    p = source['promotion']
    e = p['evidence']
    expected = T.digest({'kind': 'arc3_witnessed_policy',
                         'evidence_sha256': T.digest(e),
                         'program': atoms(e['program']), 'source_commit': T.FROZEN})
    if (p['status'] != 'REPLAY_GATED_PROMOTION_PASS'
            or p['identity'] != p['approval']['identity']
            or p['identity'] != expected or p['identity'] != identity
            or p['evidence_sha256'] != T.digest(e)
            or e['initial_sha256'] != source['initial_sha256']
            or atoms(e['program']) != atoms(source['source_development']['prefix'])):
        raise ValueError('Source certificate mismatch')
    stage = source['source_development']['stages'][-1]
    if (atoms(stage['prefix']) != atoms(e['program'])
            or stage['checkpoint_sha256'] != e['proof']['final_sha256']
            or stage['level'] != e['proof']['levels_completed']):
        raise ValueError('Source checkpoint mismatch')
    return stage


def promote_stage(factory, prefix, entry_path, stage, baseline, initial_sha,
                  archive, output, gate, account=lambda n: None):
    """Replay, externally certify, then install the local suffix at its entry."""
    prefix, entry_path = atoms(prefix), atoms(entry_path)
    if prefix[:len(entry_path)] != entry_path or len(prefix) <= len(entry_path):
        raise ValueError('Invalid continuation prefix')
    first = T.F.replay(factory, prefix, None, 120)
    account(first['actions'])
    proof = T.F.replay(factory, prefix, first['final_sha256'], 120)
    account(proof['actions'])
    replay_actions = first['actions'] + proof['actions']
    valid = (first['status'] == proof['status'] == 'OBSERVED'
             and atoms(first['executed']) == atoms(proof['executed']) == prefix
             and first['observations'] == proof['observations']
             and first['initial_sha256'] == proof['initial_sha256'] == initial_sha
             and stage['checkpoint_sha256'] == proof['final_sha256']
             and atoms(stage['prefix']) == prefix
             and stage['level'] == proof['levels_completed']
             and (not entry_path or T.digest(proof['observations'][len(entry_path)])
                  == baseline['final_sha256']))
    if not valid:
        return {'status': 'INCONCLUSIVE_REPLAY', 'replay': first,
                'proof': proof, 'replay_actions': replay_actions}
    candidate = {'actions': len(prefix), 'levels_completed': proof['levels_completed'],
                 'state': proof['state']}
    if T.quality(candidate) <= T.quality(baseline):
        return {'status': 'NO_MEASURED_IMPROVEMENT', 'replay': first,
                'proof': proof, 'replay_actions': replay_actions}
    evidence = {'initial_sha256': initial_sha, 'program': prefix, 'cold': baseline,
                'replay': first, 'proof': proof, 'source_commit': T.FROZEN}
    evidence_sha = T.digest(evidence)
    identity = T.digest({'kind': 'arc3_witnessed_policy', 'evidence_sha256': evidence_sha,
                         'program': prefix, 'source_commit': T.FROZEN})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output/'evidence.json').write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str)+'\n')
    approval = gate(identity, [baseline, candidate], evidence_sha, output)
    if approval.get('identity') != identity:
        raise ValueError('Promotion identity mismatch')
    suffix = prefix[len(entry_path):]
    entry = T.digest(proof['observations'][len(entry_path)])
    item = archive.install(entry, suffix, proof['final_sha256'], proof,
                           entry_path=entry_path, source=('policy', identity),
                           dependencies=tuple(range(len(archive.options))))
    return {'status': 'REPLAY_GATED_PROMOTION_PASS', 'identity': identity,
            'evidence_sha256': evidence_sha, 'evidence': evidence,
            'approval': approval, 'installed': item, 'replay_actions': replay_actions}


def continue_run(factory, actions, source, game, source_identity, output,
                 max_training_actions=3000, max_episodes=512, max_depth=32,
                 max_levels=5, budget=120, gate=T.run_lean_gate,
                 search_class=None, execute_stage=None):
    """One cumulative run with a shared archive and stage-by-stage certification."""
    if search_class is None:
        from compositional_development import OptionSearch
        search_class = OptionSearch
    if execute_stage is None:
        from multi_level_development import execute_stage
    if not actions or min(max_training_actions, max_episodes, max_depth, max_levels, budget) < 1:
        raise ValueError('Positive bounds and nonempty action alphabet required')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stage = verify_source(source, game, source_identity)
    initial_sha = source['initial_sha256']
    prefix = atoms(stage['prefix'])
    archive = T.F.FeedbackArchive()
    spent = episodes = 0
    stages = []
    attempts = []
    result = {'status': 'NOT_STARTED', 'game': game, 'source_identity': source_identity,
              'source_commit': T.FROZEN, 'upstream_commit': T.UPSTREAM,
              'initial_sha256': initial_sha, 'grounded_actions': len(actions),
              'model_calls': 0, 'competition_submission': False}

    def snapshot(status, **extra):
        result.update(status=status, training_actions=spent, training_episodes=episodes,
                      prefix=prefix, stages=stages, archive=archive.snapshot(),
                      attempts=attempts, **extra)
        return result

    def charge(n, count=1):
        nonlocal spent, episodes
        if spent+n > max_training_actions or episodes+count > max_episodes:
            raise ValueError('Training budget exceeded')
        spent += n
        episodes += count

    # The source certificate is not trusted as a substitute for fresh replay.
    if len(prefix) > min(budget, max_training_actions) or max_episodes < 1:
        return snapshot('TRAINING_BOUND_EXHAUSTED')
    restored = T.F.replay(factory, prefix, stage['checkpoint_sha256'], budget)
    charge(restored['actions'])
    if (restored['status'] != 'OBSERVED' or atoms(restored['executed']) != prefix
            or restored['initial_sha256'] != initial_sha
            or restored['levels_completed'] != stage['level']):
        return snapshot('INCONCLUSIVE_SOURCE_REPLAY', restored=restored)
    baseline = dict(source['cold'])
    if baseline['initial_sha256'] != initial_sha:
        return snapshot('INCONCLUSIVE_UNMATCHED_START')
    if spent+2*len(prefix) > max_training_actions or episodes+2 > max_episodes:
        return snapshot('TRAINING_BOUND_EXHAUSTED')
    try:
        accepted = promote_stage(factory, prefix, (), stage, baseline, initial_sha,
                                 archive, output/'stage-01', gate, charge)
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        return snapshot('INCONCLUSIVE_VERIFIER', verifier_error=str(exc))
    if accepted['status'] != 'REPLAY_GATED_PROMOTION_PASS':
        return snapshot(accepted['status'], promotion=accepted)
    if accepted['identity'] != source_identity:
        return snapshot('INCONCLUSIVE_SOURCE_IDENTITY')
    stages.append({'level': stage['level'], 'prefix': prefix,
                   'checkpoint_sha256': stage['checkpoint_sha256'],
                   'promotion': accepted})
    current = restored
    checkpoint = restored['final_sha256']
    if current['state'] == 'WIN':
        return snapshot('VERIFIED_WIN', terminal_win=True)
    if current['state'] == 'GAME_OVER':
        return snapshot('TERMINAL_WITHOUT_WIN', terminal_win=False)

    while current['levels_completed'] < max_levels:
        target = current['levels_completed']
        entry_path = prefix
        # Only certified options enter the search. Their effects at this new
        # entry are hypotheses, not assumed state-equivalence laws.
        options = [item['program'] for item in archive.options]
        search = search_class(tuple(actions), options, max_depth=max_depth)
        advanced = False
        while episodes < max_episodes and spent < max_training_actions:
            suffix = search.propose()
            if suffix is None:
                return snapshot('NO_PROGRESS_WITHIN_BOUND', terminal_win=False)
            suffix = atoms(suffix)
            path = prefix+suffix
            # Reserve two full replays for any newly witnessed candidate.
            if len(path) > budget or spent+3*len(path) > max_training_actions or episodes+3 > max_episodes:
                return snapshot('TRAINING_BOUND_EXHAUSTED', terminal_win=False)
            trial = execute_stage(factory(), prefix, suffix, target, budget, checkpoint)
            charge(trial['actions'])
            if (trial['initial_sha256'] != initial_sha or trial['status'] in
                    ('INCONCLUSIVE_PREFIX_MISMATCH', 'PREFIX_TERMINATED')):
                return snapshot('INCONCLUSIVE_PREFIX_REPLAY', terminal_win=False)
            if trial['status'] == 'BUDGET_EXHAUSTED':
                return snapshot('TRAINING_BOUND_EXHAUSTED', terminal_win=False)
            local = dict(trial, actions=trial['actions']-len(prefix),
                         executed=atoms(trial['executed'][len(prefix):]))
            verdict = search.retain(suffix, local)
            attempts.append({'target': target, 'suffix': suffix,
                             'status': trial['status'], 'actions': trial['actions'],
                             'progress': trial['progress'], 'trace_sha256': trial['trace_sha256']})
            if verdict != 'PROGRESS_WITNESSED':
                continue
            actual = local['executed']
            candidate_prefix = prefix+actual
            new_stage = {'level': trial['levels_completed'], 'prefix': candidate_prefix,
                         'suffix': actual, 'checkpoint_sha256': trial['final_sha256'],
                         'trace_sha256': trial['trace_sha256']}
            if spent+2*len(candidate_prefix) > max_training_actions or episodes+2 > max_episodes:
                return snapshot('PENDING_CERTIFICATION_BUDGET', pending_stage=new_stage)
            try:
                accepted = promote_stage(factory, candidate_prefix, entry_path, new_stage,
                                         current, initial_sha, archive,
                                         output/('stage-%02d' % (len(stages)+1)), gate, charge)
            except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
                return snapshot('INCONCLUSIVE_VERIFIER', pending_stage=new_stage,
                                verifier_error=str(exc))
            if accepted['status'] != 'REPLAY_GATED_PROMOTION_PASS':
                return snapshot(accepted['status'], pending_stage=new_stage, promotion=accepted)
            prefix, checkpoint = candidate_prefix, trial['final_sha256']
            current = accepted['evidence']['proof']
            stages.append(dict(new_stage, promotion=accepted))
            advanced = True
            if current['state'] == 'WIN':
                return snapshot('VERIFIED_WIN', terminal_win=True)
            if current['state'] == 'GAME_OVER':
                return snapshot('TERMINAL_WITHOUT_WIN', terminal_win=False)
            break
        if not advanced:
            return snapshot('TRAINING_BOUND_EXHAUSTED', terminal_win=False)
    return snapshot('LEVEL_TARGET_WITNESSED', terminal_win=current['state'] == 'WIN')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--frozen-dir', required=True)
    p.add_argument('--environments-dir', required=True)
    p.add_argument('--game', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--source-identity', required=True)
    p.add_argument('--output', default='arc3-shared-continuation.json')
    p.add_argument('--max-training-actions', type=int, default=3000)
    p.add_argument('--max-episodes', type=int, default=512)
    p.add_argument('--max-depth', type=int, default=32)
    p.add_argument('--max-levels', type=int, default=5)
    a = p.parse_args()
    _, _, grounding, _, multilevel = T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('arc3-shared-continuation')
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
    source = json.loads(Path(a.source).read_text())
    result = continue_run(factory, actions, source, a.game, a.source_identity,
                          Path(a.output).parent/'shared-continuation-gate',
                          max_training_actions=a.max_training_actions,
                          max_episodes=a.max_episodes, max_depth=a.max_depth,
                          max_levels=a.max_levels, execute_stage=multilevel.execute_stage)
    result['unsupported_action_ids'] = unsupported
    result['mode'] = 'offline'
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str)+'\n')
    print('ARC3_SHARED_CONTINUATION='+json.dumps({k:result.get(k) for k in
          ('status','training_actions','training_episodes','grounded_actions','terminal_win')},sort_keys=True))

if __name__ == '__main__':
    main()
