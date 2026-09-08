"""Test whether equal immediate public observations hide different continuations.

No game internals, target labels, or learned rules are used. The immutable
three-stage archive supplies the checkpoint. Every experiment is a fresh
public-API replay, and no nonterminal effect is promoted as a capability.
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
    """Return only independently observed, well-formed one-step collisions."""
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


def distinct_successors(rows):
    """A common immediate observation is not assumed to be a common state."""
    if len(rows) != 2 or rows[0]['observed_hashes'][1] != rows[1]['observed_hashes'][1]:
        return False
    return rows[0]['observed_hashes'][-1] != rows[1]['observed_hashes'][-1]


def experiment(factory, prefix, checkpoint, groups, contexts, max_actions=1200, max_episodes=64):
    """Use matched fresh replays, reserve complete pairs, and retain raw evidence."""
    meter = M.ActionMeter(factory, 0, 0, max_actions, max_episodes)
    rows, witnesses = [], []
    seen = set()
    initial = None
    for immediate, actions in groups:
        for i, a in enumerate(actions):
            for b in actions[i+1:]:
                for context in contexts:
                    if not context or (a, b, context) in seen:
                        continue
                    seen.add((a, b, context))
                    paths = (prefix + (a,) + context, prefix + (b,) + context)
                    if any(len(p) > 120 for p in paths):
                        continue
                    try:
                        meter.reserve(sum(map(len, paths)), 2)
                    except M.TrainingLimit:
                        return {'status':'TRAINING_BOUND_EXHAUSTED','rows':rows,'witnesses':witnesses,
                                'training_actions':meter.actions,'training_episodes':meter.episodes}
                    pair = []
                    for path in paths:
                        r = F.replay(meter.factory, path, None, 120)
                        if initial is None: initial = r['initial_sha256']
                        if (r['initial_sha256'] != initial or r['executed'] != path
                                or r['status'] != 'OBSERVED' or len(r['observations']) != len(path)+1
                                or F.digest(r['observations'][len(prefix)]) != checkpoint):
                            raise ValueError('Fresh replay or checkpoint mismatch')
                        obs = r['observations'][len(prefix):]
                        pair.append({'program':(a,)+context if path == paths[0] else (b,)+context,
                                     'observed_hashes':tuple(map(F.digest,obs)), 'observations':obs,
                                     'levels_completed':r['levels_completed'],'state':r['state']})
                    if pair[0]['observed_hashes'][1] != immediate or pair[1]['observed_hashes'][1] != immediate:
                        raise ValueError('Archived immediate consequence changed')
                    row = {'actions':(a,b),'context':context,'immediate_sha256':immediate,
                           'successors':pair,'separated':distinct_successors(pair)}
                    rows.append(row)
                    if row['separated']:
                        # A second pair of fresh replays is required before a witness is retained.
                        meter.reserve(sum(map(len,paths)),2)
                        repeat = [F.replay(meter.factory,path,None,120) for path in paths]
                        if all(r['status']=='OBSERVED' and r['executed']==p and
                               r['observations'][len(prefix):]==pair[j]['observations']
                               for j,(r,p) in enumerate(zip(repeat,paths))):
                            witnesses.append(row)
                            return {'status':'REPLAY_CONFIRMED_SEPARATOR','rows':rows,'witnesses':witnesses,
                                    'training_actions':meter.actions,'training_episodes':meter.episodes}
                        raise ValueError('Separator did not survive fresh replay')
    return {'status':'NO_SEPARATOR_WITHIN_BOUND','rows':rows,'witnesses':witnesses,
            'training_actions':meter.actions,'training_episodes':meter.episodes}


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
    result=experiment(factory,prefix,checkpoint,groups,contexts)
    result.update(game=a.game,mode='offline',source_run=M.SOURCE_RUN,archive_run=A.ARCHIVE_RUN,
                  transfer_run=P.TRANSFER_RUN,residual_run=S.RESIDUAL_RUN,
                  source_commit=T.FROZEN,upstream_commit=T.UPSTREAM,initial_sha256=source['initial_sha256'],
                  checkpoint_sha256=checkpoint,collision_groups=groups,contexts=contexts,
                  archived_levels=len(stages),new_discoveries=0,installed_options=0,
                  terminal_win=False,model_calls=0,competition_submission=False,
                  unsupported_action_ids=unsupported)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_DELAYED_SEPARATOR='+json.dumps({k:result[k] for k in ('status','training_actions','training_episodes','archived_levels','new_discoveries')},sort_keys=True))

if __name__=='__main__':main()
