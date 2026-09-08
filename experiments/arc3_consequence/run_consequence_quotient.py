"""Official offline comparison; no game source enters the controller."""
import argparse,json,logging
from pathlib import Path
from arc_agi import Arcade,OperationMode
from agent import observation
from finite_consequence import digest
from parameterized_actions import action_catalog,decode
from consequence_quotient import compare

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',default='bt33-a7c3f9d18b4e')
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--max-episodes',type=int,default=2048)
    p.add_argument('--max-depth',type=int,default=32)
    p.add_argument('--max-training-actions',type=int,default=20000)
    p.add_argument('--max-levels',type=int,default=5)
    p.add_argument('--horizon',type=int,default=4)
    p.add_argument('--stride',type=int,default=8)
    p.add_argument('--max-grounded-actions',type=int,default=256)
    p.add_argument('--output',default='arc3-consequence-quotient.json')
    a=p.parse_args()
    logger=logging.getLogger('arc3-quotient');logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
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
    actions,unsupported=action_catalog(first.action_space,first.observation_space,a.stride,a.max_grounded_actions)
    first.close()
    result={'game':a.game,'mode':'offline','competition_submission':False,'model_calls':0,
            'initial_sha256':initial,'grounded_actions':len(actions),'unsupported_action_ids':unsupported,
            'budget':a.max_actions,'max_training_actions':a.max_training_actions,'max_levels':a.max_levels,
            'horizon':a.horizon,'stride':a.stride}
    result.update(compare(factory,actions,budget=a.max_actions,max_episodes=a.max_episodes,
                          max_depth=a.max_depth,max_training_actions=a.max_training_actions,
                          max_levels=a.max_levels,horizon=a.horizon))
    if any(result[k]['initial_sha256']!=initial for k in ('cold','warm')):
        result['status']='INCONCLUSIVE_UNMATCHED_START';result['improved']=False
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_CONSEQUENCE_QUOTIENT='+json.dumps({'status':result['status'],'improved':result['improved'],
          'development':result['development'],'quotient_sizes':[len(q['classes']) for q in result['quotients']],
          'cold':{k:result['cold'][k] for k in ('actions','levels_completed','score','state')},
          'warm':{k:result['warm'][k] for k in ('actions','levels_completed','score','state')}},sort_keys=True,default=str))
if __name__=='__main__':main()
