"""Externally qualify a proposed search procedure without promoting it by assertion."""
import argparse, json, logging
from pathlib import Path
from arc_agi import Arcade, OperationMode
from agent import observation
from finite_consequence import digest
from parameterized_actions import action_catalog, decode
from consequence_quotient import compare as legacy_compare
from consequence_search import compare as ranked_compare


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
    p.add_argument('--output',default='arc3-consequence-search.json')
    a=p.parse_args()
    logger=logging.getLogger('arc3-consequence-search')
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
    actions,unsupported=action_catalog(first.action_space,first.observation_space,a.stride,a.max_grounded_actions)
    first.close()
    result={'game':a.game,'mode':'offline','competition_submission':False,'model_calls':0,
            'initial_sha256':initial,'grounded_actions':len(actions),'unsupported_action_ids':unsupported,
            'budget':a.max_actions,'max_training_actions_per_policy':a.max_training_actions,
            'max_episodes_per_policy':a.max_episodes,'max_depth':a.max_depth,'max_levels':a.max_levels,
            'horizon':a.horizon,'policies':{}}
    if not actions:
        result.update(status='UNSUPPORTED_ACTION_INTERFACE',selected_policy=None,improved=False)
    else:
        kwargs=dict(budget=a.max_actions,max_episodes=a.max_episodes,max_depth=a.max_depth,
                    max_training_actions=a.max_training_actions,max_levels=a.max_levels,horizon=a.horizon)
        for name,fn in [('legacy',legacy_compare),('ranked-factor-v1',ranked_compare)]:
            result['policies'][name]=fn(factory,actions,**kwargs)
        legacy=result['policies']['legacy'];candidate=result['policies']['ranked-factor-v1']
        matched=all(r['status']=='COMPARABLE' and
                    r['cold']['initial_sha256']==r['warm']['initial_sha256']==initial
                    for r in (legacy,candidate))
        a0=legacy['warm'];b0=candidate['warm']
        better=b0['levels_completed']>a0['levels_completed'] or (
            b0['levels_completed']==a0['levels_completed']>0 and b0['actions']<a0['actions'])
        selected='ranked-factor-v1' if matched and better else 'legacy'
        result.update(status='COMPARABLE' if matched else 'INCONCLUSIVE_UNMATCHED_START',
                      selected_policy=selected if matched else None,
                      improved=bool(matched and better))
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    summary={k:v for k,v in result.items() if k!='policies'}
    summary['policies']={name:{'status':r['status'],'development_status':r['development']['status'],
                              'training_actions':r['development']['training_actions'],
                              'training_episodes':r['development']['training_episodes'],
                              'levels_witnessed':r['development']['levels_witnessed'],
                              'quotient_sizes':[len(q['classes']) for q in r['quotients']],
                              'warm':{k:r['warm'][k] for k in ('actions','levels_completed','score','state')}}
                         for name,r in result['policies'].items()}
    print('ARC3_CONSEQUENCE_SEARCH='+json.dumps(summary,sort_keys=True,default=str))

if __name__=='__main__':main()
