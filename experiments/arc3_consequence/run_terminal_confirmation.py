"""Recheck a retained public-API program; no successful sequence is supplied in code."""
import argparse,json,logging
from pathlib import Path
from arc_agi import Arcade,OperationMode
from agent import observation
from finite_consequence import digest
from parameterized_actions import action_catalog,decode
from terminal_confirmation import confirm


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',required=True)
    p.add_argument('--game',required=True)
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--max-training-actions',type=int,default=3000)
    p.add_argument('--max-episodes',type=int,default=128)
    p.add_argument('--max-depth',type=int,default=32)
    p.add_argument('--output',default='arc3-terminal-confirmation.json')
    a=p.parse_args()
    evidence=json.loads(Path(a.evidence).read_text())
    if evidence['game']!=a.game or evidence['status']!='COMPARABLE':
        raise ValueError('Source evidence game or qualification mismatch')
    selected=evidence['selected_policy']
    if selected is None:raise ValueError('No qualified source policy')
    prior=evidence['policies'][selected]
    if prior['status']!='COMPARABLE':raise ValueError('Source policy is inconclusive')
    prefix=prior['development']['prefix']
    stages=prior['development']['stages']
    if not stages or len(stages)!=prior['warm']['levels_completed']:
        raise ValueError('No complete witnessed prefix')
    checkpoint=stages[-1]['checkpoint_sha256']
    if prior['warm']['final_sha256']!=checkpoint:
        raise ValueError('Source deployment and checkpoint disagree')
    logger=logging.getLogger('arc3-terminal-confirmation')
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
    initial=digest(observation(first.observation_space))
    actions,unsupported=action_catalog(first.action_space,first.observation_space,8,256)
    first.close()
    if initial!=evidence['initial_sha256']:
        raise ValueError('Source initial observation mismatch')
    result=confirm(factory,actions,prefix,len(stages),checkpoint,initial,
                   a.max_actions,a.max_training_actions,a.max_episodes,a.max_depth,
                   options=prior['development']['options'])
    result.update(game=a.game,mode='offline',competition_submission=False,model_calls=0,
                  source_run=34192005884,source_policy=selected,source_evidence_sha256=digest(evidence),
                  initial_sha256=initial,unsupported_action_ids=unsupported)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_TERMINAL_CONFIRMATION='+json.dumps({
        'status':result['status'],'training_actions':result['training_actions'],
        'training_episodes':result['training_episodes'],
        'levels_witnessed':result['levels_witnessed'],
        'actions':result.get('result',{}).get('actions'),
        'levels_completed':result.get('result',{}).get('levels_completed'),
        'state':result.get('result',{}).get('state'),
        'score':result.get('result',{}).get('score'),
        'trace_sha256':result.get('result',{}).get('trace_sha256')},sort_keys=True))

if __name__=='__main__':main()
