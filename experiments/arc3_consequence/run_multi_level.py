"""Official offline ARC qualification; the controller sees public observations only."""
import argparse, json, logging
from pathlib import Path
from arc_agi import Arcade, OperationMode
from agent import observation
from run_arc import simple_action_ids, decode_action
from multi_level_development import compare_levels
from finite_consequence import digest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',default='bt11-fd9df0622a1a')
    p.add_argument('--environments-dir',default='environment_files')
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--max-episodes',type=int,default=512)
    p.add_argument('--max-depth',type=int,default=8)
    p.add_argument('--max-training-actions',type=int,default=3000)
    p.add_argument('--max-levels',type=int,default=5)
    p.add_argument('--output',default='arc3-multi-level.json')
    a=p.parse_args()
    logger=logging.getLogger('arc3-multi-level')
    logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
    def factory():
        arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=a.environments_dir,logger=logger)
        env=arcade.make(a.game)
        if env is None:raise RuntimeError('Environment unavailable: '+a.game)
        class Adapter:
            @property
            def observation_space(self):return env.observation_space
            @property
            def action_space(self):return env.action_space
            def reset(self):return env.reset()
            def step(self,action):return env.step(decode_action(action))
            def close(self):return arcade.close_scorecard()
        return Adapter()
    first=factory();actions=simple_action_ids(first.action_space)
    initial_sha=digest(observation(first.observation_space));first.close()
    result=compare_levels(factory,actions,a.max_actions,a.max_episodes,a.max_depth,
                          a.max_training_actions,a.max_levels)
    result.update(game=a.game,mode='offline',competition_submission=False,model_calls=0,
                  budget=a.max_actions,max_training_actions=a.max_training_actions,
                  max_episodes=a.max_episodes,max_depth=a.max_depth,max_levels=a.max_levels)
    result['status']='INCONCLUSIVE_UNMATCHED_START' if any(
        x['initial_sha256']!=initial_sha for x in (result['cold'],result['warm'])) else result['status']
    if result['status']!='COMPARABLE':result['improved']=False
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    summary={k:v for k,v in result.items() if k not in ('cold','warm')}
    summary['cold']={k:result['cold'][k] for k in ('actions','levels_completed','score','state')}
    summary['warm']={k:result['warm'][k] for k in ('actions','levels_completed','score','state')}
    print('ARC3_MULTI_LEVEL='+json.dumps(summary,sort_keys=True,default=str))

if __name__=='__main__':main()
