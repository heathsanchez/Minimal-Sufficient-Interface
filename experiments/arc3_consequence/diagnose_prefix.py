"""Diagnose a witnessed checkpoint using only public observations.

This is a measurement experiment, not a solver. The prefix is supplied as
external evidence; no game-specific interpretation or hidden state is used.
"""
import argparse, json, logging
from pathlib import Path
from collections import Counter
from arc_agi import Arcade, OperationMode
from agent import observation, terminal
from finite_consequence import digest, freeze
from parameterized_actions import action_catalog, decode
from multi_level_development import execute_stage


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',required=True)
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--prefix-json',required=True)
    p.add_argument('--target',type=int,required=True)
    p.add_argument('--checkpoint',required=True)
    p.add_argument('--repetitions',type=int,default=4)
    p.add_argument('--max-probes',type=int,default=256)
    p.add_argument('--output',default='arc3-checkpoint-diagnostic.json')
    a=p.parse_args()
    prefix=tuple(tuple(x) if isinstance(x,list) else x for x in json.loads(a.prefix_json))
    logger=logging.getLogger('arc3-checkpoint-diagnostic')
    logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
    def factory():
        arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=a.environments_dir,logger=logger)
        env=arcade.make(a.game)
        if env is None:raise RuntimeError('Environment unavailable')
        class Adapter:
            @property
            def observation_space(self):return env.observation_space
            @property
            def action_space(self):return env.action_space
            def reset(self):return env.reset()
            def step(self,action):
                kind,data=decode(action)
                return env.step(kind,data=data)
            def close(self):return arcade.close_scorecard()
        return Adapter()
    first=factory()
    initial=observation(first.observation_space)
    actions,unsupported=action_catalog(first.action_space,first.observation_space,8,a.max_probes)
    first.close()
    rows=[];representatives={};source=None
    for action in actions[:a.max_probes]:
        history=[]
        class Recorder:
            def __init__(self):self.env=factory()
            @property
            def observation_space(self):return self.env.observation_space
            def reset(self):return self.env.reset()
            def step(self,token):
                before=observation(self.env.observation_space)
                frame=self.env.step(token)
                after=observation(frame)
                history.append({'action':token,'before':before,'after':after})
                return frame
            def close(self):return self.env.close()
        rec=Recorder()
        result=execute_stage(rec,prefix,(action,)*a.repetitions,a.target,
                             len(prefix)+a.repetitions,a.checkpoint)
        if result['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH','PREFIX_TERMINATED'):
            raise RuntimeError(result['status'])
        if source is None:
            source=history[len(prefix)-1]['after'] if prefix else initial
        changes=[]
        for transition in history[len(prefix):]:
            before,after=transition['before'],transition['after']
            b=before['frame'];c=after['frame']
            changes.append(sum(x!=y for x,y in zip(flat(b),flat(c))))
        final=history[-1]['after'] if history else initial
        key=(result['progress'],result['state'],tuple(changes),digest(final['frame']))
        label=digest(key)
        rows.append({'action':action,'progress':result['progress'],'state':result['state'],
                     'executed':result['executed'][len(prefix):],'changes':changes,
                     'final_sha256':result['final_sha256'],'outcome_key':label})
        if label not in representatives:
            representatives[label]={'action':action,'observation':final}
    groups=Counter(r['outcome_key'] for r in rows)
    report={'game':a.game,'mode':'offline','competition_submission':False,'model_calls':0,
            'prefix':prefix,'target':a.target,'checkpoint_sha256':a.checkpoint,
            'initial_sha256':digest(initial),'unsupported_action_ids':unsupported,
            'probes':len(rows),'repetitions':a.repetitions,'source':source,
            'rows':rows,'representatives':representatives,'outcome_counts':dict(groups)}
    Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
    print('CHECKPOINT_DIAGNOSTIC='+json.dumps({'probes':len(rows),'progress':sum(r['progress']>0 for r in rows),
          'terminal':sum(r['state'] in ('WIN','GAME_OVER') for r in rows),
          'outcomes':len(groups),'outcome_counts':dict(groups),
          'initial_sha256':report['initial_sha256'],'checkpoint_sha256':a.checkpoint},sort_keys=True))

def flat(value):
    if isinstance(value,(list,tuple)):
        for x in value:yield from flat(x)
    else:yield value

if __name__=='__main__':main()
