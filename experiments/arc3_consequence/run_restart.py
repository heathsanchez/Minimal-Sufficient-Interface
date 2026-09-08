"""Independent public-API episodes; no hidden game state or source in controller."""
import argparse, json, logging
from pathlib import Path
from arc_agi import Arcade, OperationMode
from agent import observation, run_episode
from run_arc import simple_action_ids, decode_action
from probe_exploration import ProbeController
from restart_development import discover, execute
from finite_consequence import digest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',default='bt11-fd9df0622a1a')
    p.add_argument('--environments-dir',default='environment_files')
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--max-episodes',type=int,default=512)
    p.add_argument('--max-depth',type=int,default=8)
    p.add_argument('--output',default='arc3-restart-development.json')
    a=p.parse_args()
    logger=logging.getLogger('arc3-restart-development')
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
    learned=discover(factory,actions,a.max_actions,a.max_episodes,a.max_depth)
    d=learned['development']
    # Training is excluded from the fresh-start deployment score, but counted.
    cold_env=factory();warm_env=factory()
    cold_start=digest(observation(cold_env.observation_space))
    warm_start=digest(observation(warm_env.observation_space))
    matched=initial_sha==cold_start==warm_start==learned['initial_sha256']
    cold=run_episode(cold_env,actions,a.max_actions,ProbeController(actions,probe_enabled=False,retain_scripts=False))
    cold_card=cold_env.close();cold_card=cold_card.model_dump(mode='json') if hasattr(cold_card,'model_dump') else str(cold_card)
    program=learned.get('program')
    if program is None:
        # No learned success is silently promoted. The warm deployment uses the
        # original controller and the experiment remains a negative result.
        warm=run_episode(warm_env,actions,a.max_actions,ProbeController(actions,probe_enabled=True,retain_scripts=False))
        warm['program_replayed']=False
    else:
        warm=execute(warm_env,program,a.max_actions)
        warm['levels_completed']=warm['final']['levels_completed']
        warm['program_replayed']=True
    warm_card=warm_env.close();warm_card=warm_card.model_dump(mode='json') if hasattr(warm_card,'model_dump') else str(warm_card)
    for card in (cold_card,warm_card):
        if isinstance(card,dict):card.pop('api_key',None)
    def score(card):return card.get('score') if isinstance(card,dict) else None
    improved=bool(matched and warm['levels_completed']>cold['levels_completed'] or
                  matched and warm['levels_completed']==cold['levels_completed'] and warm['levels_completed']>0 and warm['actions']<cold['actions'])
    result={'status':'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'game':a.game,'mode':'offline','competition_submission':False,'model_calls':0,
            'budget':a.max_actions,'training_episodes':len(d.evidence),
            'training_actions':learned['training_actions'],'development_status':learned['status'],
            'development':d.snapshot(),'candidate':program,'cold':cold,'warm':warm,
            'cold_score':score(cold_card),'warm_score':score(warm_card),
            'improved':improved,'cold_scorecard':cold_card,'warm_scorecard':warm_card}
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_RESTART_DEVELOPMENT='+json.dumps({k:v for k,v in result.items() if k not in ('cold_scorecard','warm_scorecard','cold','warm')},sort_keys=True,default=str))
    print('ARC3_RESTART_DEPLOYMENT='+json.dumps({'cold':{'actions':cold['actions'],'levels':cold['levels_completed'],'score':score(cold_card)},'warm':{'actions':warm['actions'],'levels':warm['levels_completed'],'score':score(warm_card)},'improved':improved},sort_keys=True))

if __name__=='__main__':main()
