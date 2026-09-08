"""Bounded public-observation continuation separation, not a game solve.

The frozen controller and three-stage archive are unchanged. A collision is
only a hypothesis until the same continuation separates fresh full replays.
No nonterminal observation is promoted as a capability.
"""
import argparse
import hashlib
import json
import logging
from collections import defaultdict
from pathlib import Path

import arc3_stage4_separator as S
import arc3_stage4_probe as P
import arc3_archive_transfer as A
import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F


def collision_groups(residual, alphabet, checkpoint):
    """Find one-step observation collisions without identifying hidden states."""
    groups = defaultdict(set)
    for row in residual.get('diagnostic_rows', ()):
        program = tuple(map(F.atom, row['program']))
        observations = row['observations']
        hashes = tuple(map(F.digest, observations))
        if (not program or len(observations) != len(program) + 1
                or tuple(row['observed_hashes']) != hashes
                or hashes[0] != checkpoint or any(a not in alphabet for a in program)
                or row['changed'] != (len(set(hashes)) > 1)):
            raise ValueError('Malformed residual observation')
        if len(program) == 1:
            groups[hashes[-1]].add(program[0])
    return tuple((h, tuple(sorted(actions))) for h, actions in sorted(groups.items())
                 if len(actions) > 1)


def first_divergence(rows):
    """Return the first differing continuation index, or None.

    Index zero is the common checkpoint and index one the common immediate
    observation. The comparison is of actual public observations, not states.
    """
    if len(rows) != 2:
        return None
    left, right = (row['observed_hashes'] for row in rows)
    if len(left) != len(right) or len(left) < 3 or left[:2] != right[:2]:
        return None
    return next((i for i in range(2, len(left)) if left[i] != right[i]), None)


def distinct_successors(rows):
    return first_divergence(rows) is not None


def experiment(factory, prefix, checkpoint, groups, contexts, max_actions=1200,
               max_episodes=64, initial_sha256=None, initial_actions=0,
               initial_episodes=0, max_path=120):
    """Charge complete full-prefix pairs; reserve confirmation before discovery.

    Budget includes the supplied historical acquisition counts. Every external
    action is charged by ActionMeter, including failed calls. A pair is never
    silently truncated or interpreted as a proof of hidden-state equivalence.
    """
    prefix = tuple(map(F.atom, prefix))
    meter = M.ActionMeter(factory, initial_actions, initial_episodes,
                          max_actions, max_episodes)
    rows, witnesses = [], []
    seen = set()
    skipped = 0
    attempted = 0
    def finish(status, **extra):
        return dict(status=status, rows=rows, witnesses=witnesses,
                    training_actions=meter.actions, training_episodes=meter.episodes,
                    diagnostic_actions=meter.actions-initial_actions,
                    diagnostic_episodes=meter.episodes-initial_episodes,
                    attempted_pairs=attempted, skipped_pairs=skipped, **extra)
    for immediate, actions in groups:
        for i, a in enumerate(actions):
            for b in actions[i+1:]:
                for context in contexts:
                    context = tuple(map(F.atom, context))
                    if not context or (a, b, context) in seen:
                        continue
                    seen.add((a, b, context))
                    paths = (prefix + (a,) + context, prefix + (b,) + context)
                    if any(len(p) > max_path for p in paths):
                        skipped += 1
                        continue
                    # Fund discovery and its independent confirmation together.
                    # A rejected candidate cannot consume the confirmation reserve.
                    try:
                        meter.reserve(2*sum(map(len, paths)), 4)
                    except M.TrainingLimit:
                        return finish('TRAINING_BOUND_EXHAUSTED')
                    attempted += 1
                    pair = []
                    for path in paths:
                        try:
                            r = F.replay(meter.factory, path, None, max_path)
                        except Exception as exc:
                            return finish('INCONCLUSIVE_REPLAY', error=repr(exc))
                        if (initial_sha256 is not None and r['initial_sha256'] != initial_sha256
                                or r['executed'] != path or r['status'] != 'OBSERVED'
                                or len(r['observations']) != len(path)+1
                                or F.digest(r['observations'][len(prefix)]) != checkpoint):
                            return finish('INCONCLUSIVE_REPLAY', error='Initial, checkpoint, or execution mismatch')
                        obs = r['observations'][len(prefix):]
                        pair.append(dict(program=tuple(path[len(prefix):]),
                                         observed_hashes=tuple(map(F.digest, obs)),
                                         observations=obs, levels_completed=r['levels_completed'],
                                         state=r['state']))
                    if any(row['observed_hashes'][1] != immediate for row in pair):
                        return finish('INCONCLUSIVE_REPLAY', error='Archived immediate consequence changed')
                    divergence = first_divergence(pair)
                    row = dict(actions=(a,b), context=context, immediate_sha256=immediate,
                               successors=pair, separated=divergence is not None,
                               first_divergence=divergence)
                    rows.append(row)
                    if divergence is None:
                        continue
                    # The same full paths must reproduce the complete public traces.
                    try:
                        meter.reserve(sum(map(len, paths)), 2)
                        repeat = [F.replay(meter.factory, p, None, max_path) for p in paths]
                    except M.TrainingLimit:
                        return finish('INCONCLUSIVE_CONFIRMATION_BUDGET')
                    except Exception as exc:
                        return finish('INCONCLUSIVE_CONFIRMATION', error=repr(exc))
                    if not all(r['status']=='OBSERVED' and r['executed']==p
                               and (initial_sha256 is None or r['initial_sha256']==initial_sha256)
                               and r['observations'][len(prefix):]==pair[j]['observations']
                               for j,(r,p) in enumerate(zip(repeat,paths))):
                        return finish('INCONCLUSIVE_CONFIRMATION', error='Fresh trace mismatch')
                    witnesses.append(row)
                    return finish('REPLAY_CONFIRMED_SEPARATOR')
    return finish('NO_SEPARATOR_WITHIN_BOUND')


def main():
    p=argparse.ArgumentParser()
    for name in ('source','archive','transfer','stage','residual'):
        p.add_argument('--'+name+'-evidence',required=True)
    p.add_argument('--frozen-dir',required=True)
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--game',default='bt33-a7c3f9d18b4e')
    p.add_argument('--output',default='arc3-delayed-separator.json')
    a=p.parse_args()
    _,_,grounding,_,_=T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade,OperationMode
    logger=logging.getLogger('arc3-delayed-separator')
    logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
    def factory():
        arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=a.environments_dir,logger=logger)
        env=arcade.make(a.game)
        if env is None: raise RuntimeError('Environment unavailable')
        class Adapter:
            @property
            def observation_space(self): return env.observation_space
            @property
            def action_space(self): return env.action_space
            def reset(self): return env.reset()
            def step(self,action):
                kind,data=grounding.decode(action)
                return env.step(kind,data=data)
            def close(self): return arcade.close_scorecard()
        return Adapter()
    first=factory()
    actions,unsupported=grounding.action_catalog(first.action_space,first.observation_space,8,256)
    first.close()
    def read(path): return json.loads(Path(path).read_text())
    if hashlib.sha256(Path(a.residual_evidence).read_bytes()).hexdigest()!=S.RESIDUAL_SHA256:
        raise ValueError('Residual evidence SHA256 mismatch')
    source,report,transfer,evidence,residual=(read(getattr(a,name+'_evidence')) for name in ('source','archive','transfer','stage','residual'))
    representatives,_=S.separator_programs(source,report,transfer,evidence,residual,actions)
    stages=A.select_archive(report,source,actions)
    prefix=tuple(map(F.atom,stages[-1]['prefix']))
    entry=P.verified_entry(source,report,transfer,evidence,actions)
    checkpoint=F.digest(entry)
    alphabet=set(map(F.atom,actions))|set(P.component_actions(entry,entry['available_actions']))
    groups=collision_groups(residual,alphabet,checkpoint)
    contexts=tuple(dict.fromkeys(tuple(map(F.atom,p)) for p in representatives))
    result=experiment(factory,prefix,checkpoint,groups,contexts,
                      initial_sha256=source['initial_sha256'],
                      initial_actions=source['training_actions'],
                      initial_episodes=source['source_development']['training_episodes'])
    result.update(game=a.game,mode='offline',source_run=M.SOURCE_RUN,archive_run=A.ARCHIVE_RUN,
                  transfer_run=P.TRANSFER_RUN,residual_run=S.RESIDUAL_RUN,
                  source_commit=T.FROZEN,upstream_commit=T.UPSTREAM,initial_sha256=source['initial_sha256'],
                  checkpoint_sha256=checkpoint,collision_groups=groups,contexts=contexts,
                  archived_levels=len(stages),new_discoveries=0,installed_options=0,
                  terminal_win=False,model_calls=0,competition_submission=False,
                  unsupported_action_ids=unsupported)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_DELAYED_SEPARATOR='+json.dumps({k:result[k] for k in ('status','training_actions','training_episodes','diagnostic_actions','attempted_pairs','archived_levels','new_discoveries')},sort_keys=True))

if __name__=='__main__':main()
