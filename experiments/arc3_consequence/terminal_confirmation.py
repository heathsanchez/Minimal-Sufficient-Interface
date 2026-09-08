"""Verify completion of a witnessed program without assuming that progress is WIN.

The existing search grammar supplies continuations. Only the external terminal
verdict can promote a completed program. All fresh replays count against the
experiment budget; a score or level count alone is not a terminal certificate.
"""
from multi_level_development import execute_stage
from consequence_search import RankedSearch


def confirm(factory, actions, prefix, target, checkpoint, initial_sha256,
            budget=120, max_training_actions=3000, max_episodes=128, max_depth=4):
    prefix=tuple(tuple(a) if isinstance(a,list) else a for a in prefix)
    actions=tuple(tuple(a) if isinstance(a,list) else a for a in actions)
    if not prefix or not actions or target < 1:
        raise ValueError('A witnessed prefix, target and public action alphabet are required')
    if len(prefix) >= budget:
        return {'status':'DEPLOYMENT_BOUND_EXHAUSTED','training_actions':0,'training_episodes':0}
    initial=execute_stage(factory(),prefix,(),target,budget,checkpoint,stop_at_progress=False)
    spent=initial['actions'];episodes=1
    if initial['initial_sha256']!=initial_sha256 or initial['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH','PREFIX_TERMINATED'):
        return {'status':'INCONCLUSIVE_PREFIX_MISMATCH','training_actions':spent,'training_episodes':episodes}
    if initial['state']=='WIN':
        return {'status':'VERIFIED_WIN','program':prefix,'result':initial,'training_actions':spent,'training_episodes':episodes}
    card=initial.get('scorecard') or {}
    total=card.get('total_levels') if isinstance(card,dict) else None
    if total is None or target != total:
        return {'status':'NOT_CONFIRMED_FINAL_LEVEL','declared_levels':total,'target':target,
                'training_actions':spent,'training_episodes':episodes}
    if initial['terminal']:
        return {'status':'TERMINAL_WITHOUT_WIN','result':initial,'training_actions':spent,'training_episodes':episodes}
    # The last successful action is the simplest continuation hypothesis.
    # The full alphabet remains available and no game-specific action is supplied.
    alphabet=tuple(dict.fromkeys((prefix[-1],)+actions))
    search=RankedSearch(alphabet,max_depth=max_depth)
    evidence=[]
    while episodes < max_episodes and spent < max_training_actions:
        suffix=search.propose()
        if suffix is None:break
        remaining=min(budget,max_training_actions-spent)
        if remaining <= len(prefix):break
        r=execute_stage(factory(),prefix,suffix,target,remaining,checkpoint,stop_at_progress=False)
        spent+=r['actions'];episodes+=1
        if r['initial_sha256']!=initial_sha256 or r['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH','PREFIX_TERMINATED'):
            return {'status':'INCONCLUSIVE_PREFIX_MISMATCH','training_actions':spent,'training_episodes':episodes,'evidence':evidence}
        evidence.append({'suffix':suffix,'state':r['state'],'actions':r['actions'],'trace_sha256':r['trace_sha256']})
        if r['state']=='WIN':
            return {'status':'VERIFIED_WIN','program':r['executed'],'result':r,
                    'training_actions':spent,'training_episodes':episodes,'evidence':evidence}
        if r['status']=='BUDGET_EXHAUSTED':break
        local=dict(r,actions=r['actions']-len(prefix),executed=r['executed'][len(prefix):])
        # No level increment is a substitute for the terminal verifier.
        local['progress']=0
        search.retain(suffix,local)
    return {'status':'NO_TERMINAL_WITHIN_BOUND','retained_prefix':prefix,
            'training_actions':spent,'training_episodes':episodes,'evidence':evidence}
