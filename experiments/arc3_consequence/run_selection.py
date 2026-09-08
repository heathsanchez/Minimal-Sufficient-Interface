"""Exact online/offline ablation of intermediate-consequence development.

Both arms start with empty memory. No game implementation is passed to the
controller. A scorecard is external evidence, not a proof of transfer.
"""
import argparse, json, logging
from pathlib import Path
from arc_agi import Arcade, OperationMode
from agent import observation, run_episode
from run_arc import simple_action_ids, decode_action
from consequence_selection import ConsequenceController
from finite_consequence import digest, freeze


def run_arm(game, online, directory, budget, enabled):
    logger=logging.getLogger('arc3-consequence-selection')
    logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
    arcade=Arcade(operation_mode=OperationMode.ONLINE if online else OperationMode.OFFLINE,
                  environments_dir=directory,logger=logger)
    env=arcade.make(game)
    if env is None:raise RuntimeError('Environment unavailable: '+game)
    actions=simple_action_ids(env.action_space)
    initial=observation(env.observation_space)
    class Adapter:
        @property
        def observation_space(self):return env.observation_space
        def reset(self):return env.reset()
        def step(self,a):return env.step(decode_action(a))
    d=ConsequenceController(actions,enabled=enabled,retain_scripts=False)
    result=run_episode(Adapter(),actions,budget,d)
    card=arcade.close_scorecard()
    card=card.model_dump(mode='json') if hasattr(card,'model_dump') else str(card)
    if isinstance(card,dict):card.pop('api_key',None)
    return dict(result,initial_sha256=digest(initial),scorecard=card,
                score=card.get('score') if isinstance(card,dict) else None,
                method='consequence-selection' if enabled else 'exact-selection-ablation',
                model_provider=None,competition_submission=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--game',default='bt11-fd9df0622a1a')
    p.add_argument('--online',action='store_true')
    p.add_argument('--environments-dir',default='environment_files')
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--output',default='arc3-consequence-selection.json')
    a=p.parse_args()
    cold=run_arm(a.game,a.online,a.environments_dir,a.max_actions,False)
    warm=run_arm(a.game,a.online,a.environments_dir,a.max_actions,True)
    matched=cold['initial_sha256']==warm['initial_sha256']
    result={'status':'COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
            'game':a.game,'mode':'online' if a.online else 'offline','budget':a.max_actions,
            'cold':cold,'warm':warm,'model_calls':cold['model_calls']+warm['model_calls'],
            'competition_submission':False}
    if matched:
        result['improved']=(warm['levels_completed']>cold['levels_completed'] or
            (warm['levels_completed']==cold['levels_completed'] and warm['levels_completed']>0 and warm['actions']<cold['actions']))
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_CONSEQUENCE_SELECTION='+json.dumps(result,sort_keys=True,default=str))

if __name__=='__main__':main()
