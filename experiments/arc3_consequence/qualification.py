"""External, matched-start qualification for a generated development operation.

A successful trace is a candidate, not an improvement. This gate compares
observable progress and action cost on fresh environments, preserves failures,
and installs only a candidate that improves the precommitted objective. It
never reads game internals. Factories must supply independent public episodes.
"""
from __future__ import annotations
from agent import Development, Transition, observation, terminal
from finite_consequence import freeze, digest, Candidate, synthesize


def run_one_progress(env, actions, budget, script=None):
    frame=env.observation_space
    if frame is None:frame=env.reset()
    initial=observation(frame)
    d=Development(tuple(actions),retain_scripts=False,repair_interval=budget+1)
    trace=[]
    for i in range(budget):
        if terminal(observation(frame)):break
        if script is not None:
            if i>=len(script):break
            action=script[i]
        else:
            key=d.state(observation(frame),d.history)
            action=d.choose(frame)
            d.visits[key,action]=d.visits.get((key,action),0)+1
        before=observation(frame)
        frame=env.step(action)
        if frame is None:raise RuntimeError('Missing external observation')
        d.observe(before,action,frame)
        trace.append((action,observation(frame)['levels_completed'],observation(frame)['state']))
        if observation(frame)['levels_completed']>initial['levels_completed']:break
    final=observation(frame)
    return {'initial':initial,'final':final,'initial_sha256':digest(initial),'progress':final['levels_completed']-initial['levels_completed'],
            'actions':len(trace),'state':final['state'],'trace_sha256':digest(trace),'model_calls':0}


def candidate_programs(script, max_candidates=128):
    """Generic one-deletion closure, then the witnessed program itself."""
    script=tuple(script)
    if not script:return ()
    out={script}
    if len(script)>1:
        out.update(script[:i]+script[i+1:] for i in range(len(script)))
    return tuple(sorted(out,key=lambda s:(len(s),s)))[:max_candidates]


def compare(factory, actions, script, budget):
    baseline_env=factory(); candidate_env=factory()
    before=observation(baseline_env.observation_space)
    other=observation(candidate_env.observation_space)
    if freeze(before)!=freeze(other):
        return {'status':'INCONCLUSIVE_UNMATCHED_START','initial_sha256':digest(before)}
    base=run_one_progress(baseline_env,actions,budget)
    proposed=run_one_progress(candidate_env,actions,budget,script)
    better=(proposed['progress']>base['progress'] or
            (proposed['progress']==base['progress'] and proposed['progress']>0 and
             proposed['actions']<base['actions']))
    no_worse=(proposed['progress']>=base['progress'] and
              (proposed['progress']>base['progress'] or proposed['actions']<=base['actions']))
    return {'status':'COMPARABLE','baseline':base,'candidate':proposed,
            'improved':better,'no_worse':no_worse}


def qualify_programs(development, train_factories, holdout_factories, budget=64, max_candidates=128):
    """Use the same generic verification loop on the development procedure.

    Train and holdout factories are supplied externally. Failed candidates
    are never promoted. A zero-cost or untested proof of improvement is not
    inferred from syntactic program length.
    """
    if not train_factories or not holdout_factories:raise ValueError('Need independent qualification and holdout')
    for entry in tuple(development.scripts):
        for script in candidate_programs(entry['actions'],max_candidates):
            if script in development.approved_scripts:continue
            checks=[]
            for factory in tuple(train_factories)+tuple(holdout_factories):
                result=compare(factory,development.actions,script,budget)
                checks.append(result)
                if result['status']!='COMPARABLE' or not result['no_worse']:
                    break
            status='VERIFIED_IMPROVEMENT' if (len(checks)==len(train_factories)+len(holdout_factories)
                  and all(c['status']=='COMPARABLE' and c['no_worse'] for c in checks)
                  and any(c['improved'] for c in checks)) else 'REJECTED_OR_INCONCLUSIVE'
            evidence={'script':script,'status':status,'checks':checks,
                      'qualification_actions':sum(c['baseline']['actions']+c['candidate']['actions']
                          for c in checks if c['status']=='COMPARABLE')}
            development.qualification_log.append(evidence)
            for check in checks:
                if check['status']!='COMPARABLE':continue
                c=check['candidate'];source=c['initial']
                development.policy_records.append(Transition(source,(),('program',script),c['final'],
                    (c['progress'],c['state'],c['actions'])))
            repair=development.refresh_policy()
            if repair is not None and repair.status!='FINITE_ADEQUATE':
                status='REJECTED_OR_INCONCLUSIVE';evidence['status']=status
            if status=='VERIFIED_IMPROVEMENT':
                development.approved_scripts[script]=evidence
                source=checks[0]['candidate']['initial']
                if not any(e['actions']==script and freeze(e['source'])==freeze(source) for e in development.scripts):
                    development.scripts.append({'actions':script,'source':source,'history':(),
                                                'evidence':digest(evidence)})
                return evidence
    return None
