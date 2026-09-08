"""Continue externally witnessed progress; only WIN certifies completion.

A reported level count is not a stopping rule. Reuse witnessed options and
retest them at each checkpoint. Never infer a terminal state from a score.
"""
from multi_level_development import execute_stage
from consequence_search import RankedSearch, factors


def confirm(factory, actions, prefix, target, checkpoint, initial_sha256,
            budget=120, max_training_actions=3000, max_episodes=128,
            max_depth=4, options=()):
    atom=lambda a: tuple(a) if isinstance(a,list) else a
    prefix=tuple(map(atom,prefix))
    actions=tuple(map(atom,actions))
    options=tuple(tuple(map(atom,o)) for o in options)
    if not actions or target < 0:
        raise ValueError('A public action alphabet and nonnegative target are required')
    if len(prefix)>budget:
        return {'status':'DEPLOYMENT_BOUND_EXHAUSTED','training_actions':0,'training_episodes':0}
    initial=execute_stage(factory(),prefix,(),target,budget,checkpoint,stop_at_progress=False)
    spent=initial['actions'];episodes=1
    evidence=[];stages=[]
    def report(status,**extra):
        return {'status':status,'retained_prefix':prefix,'levels_witnessed':target,
                'training_actions':spent,'training_episodes':episodes,
                'evidence':evidence,'stages':stages,**extra}
    if initial['initial_sha256']!=initial_sha256 or initial['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH','PREFIX_TERMINATED'):
        return report('INCONCLUSIVE_PREFIX_MISMATCH')
    if initial['state']=='WIN':
        return report('VERIFIED_WIN',program=prefix,result=initial)
    if initial['terminal']:
        return report('TERMINAL_WITHOUT_WIN',result=initial)
    # The existing successful programs are hypotheses, not assumed rules.
    options=tuple(dict.fromkeys(o for o in options if 1<len(o)<=max_depth))
    alphabet=tuple(dict.fromkeys((prefix[-1],)+actions)) if prefix else actions
    search=RankedSearch(alphabet,options,max_depth=max_depth)
    while episodes<max_episodes and spent<max_training_actions:
        suffix=search.propose()
        if suffix is None:break
        remaining=min(budget,max_training_actions-spent)
        if remaining<=len(prefix):break
        r=execute_stage(factory(),prefix,suffix,target,remaining,checkpoint)
        spent+=r['actions'];episodes+=1
        if r['initial_sha256']!=initial_sha256 or r['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH','PREFIX_TERMINATED'):
            return report('INCONCLUSIVE_PREFIX_MISMATCH')
        local=dict(r,actions=r['actions']-len(prefix),executed=r['executed'][len(prefix):])
        evidence.append({'target':target,'suffix':suffix,'progress':r['progress'],
                         'state':r['state'],'actions':r['actions'],'trace_sha256':r['trace_sha256']})
        if r['state']=='WIN':
            return report('VERIFIED_WIN',program=r['executed'],result=r)
        if r['status']=='BUDGET_EXHAUSTED':break
        verdict=search.retain(suffix,local)
        if verdict=='PROGRESS_WITNESSED':
            observed=local['executed']
            prefix+=observed
            target=r['levels_completed']
            checkpoint=r['final_sha256']
            stages.append({'level':target,'suffix':observed,'prefix':prefix,
                           'checkpoint_sha256':checkpoint,'trace_sha256':r['trace_sha256']})
            options=tuple(dict.fromkeys(options+(observed,)+tuple(f for f in factors(observed,max_depth) if len(f)>1)))
            # A new consequence changes the next search, not the definition of success.
            search=RankedSearch(alphabet,options,max_depth=max_depth)
    return report('NO_TERMINAL_WITHIN_BOUND')
