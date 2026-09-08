"""Evaluate a bounded action quotient; preserve the original controller.

The reduced alphabet is an experimental hypothesis derived from public
checkpoint outcomes. No semantic action equivalence is assumed. The full
alphabet is retained as an ablation and no failed option is promoted.
"""
import argparse,json,logging
from pathlib import Path
from arc_agi import Arcade,OperationMode
from agent import observation
from finite_consequence import digest
from parameterized_actions import action_catalog,decode
from compositional_development import compare_levels


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',default='bt33-a7c3f9d18b4e')
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--evidence',required=True)
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--max-episodes',type=int,default=2048)
    p.add_argument('--max-depth',type=int,default=32)
    p.add_argument('--max-training-actions',type=int,default=20000)
    p.add_argument('--max-levels',type=int,default=5)
    p.add_argument('--output',default='arc3-action-classes.json')
    a=p.parse_args()
    evidence=json.loads(Path(a.evidence).read_text())
    logger=logging.getLogger('arc3-action-classes');logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
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
    first=factory();initial=digest(observation(first.observation_space))
    full,unsupported=action_catalog(first.action_space,first.observation_space,8,256)
    first.close()
    if a.game!=evidence['game'] if 'game' in evidence else a.game!='bt33-a7c3f9d18b4e':
        raise ValueError('Evidence game mismatch')
    if not evidence['checkpoint_sha256'] or evidence['total_actions']!=len(full):
        raise ValueError('Evidence boundary mismatch')
    reduced=tuple(tuple(x) for x in evidence['experimental_actions'])
    if len(set(reduced))!=len(reduced) or not set(reduced).issubset(set(full)):
        raise ValueError('Reduced alphabet not a subset of public actions')
    result={'game':a.game,'mode':'offline','competition_submission':False,'model_calls':0,
            'initial_sha256':initial,'evidence':evidence,'unsupported_action_ids':unsupported,
            'max_training_actions':a.max_training_actions,'max_depth':a.max_depth,'max_levels':a.max_levels,
            'arms':{}}
    for name,actions in [('reduced',reduced),('full',full)]:
        result['arms'][name]=compare_levels(factory,actions,a.max_actions,a.max_episodes,a.max_depth,a.max_training_actions,a.max_levels)
        for arm in ('cold','warm'):
            if result['arms'][name][arm]['initial_sha256']!=initial:
                raise RuntimeError('Unmatched initial observation')
    result['status']='COMPARABLE'
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    for name,r in result['arms'].items():
        print('ACTION_CLASS_ARM='+json.dumps({'name':name,'status':r['development']['status'],
              'training_actions':r['development']['training_actions'],
              'levels_witnessed':r['development']['levels_witnessed'],
              'warm':{k:r['warm'][k] for k in ('actions','levels_completed','score','state')}},sort_keys=True))

if __name__=='__main__':main()
