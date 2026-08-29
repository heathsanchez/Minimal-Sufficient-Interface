#!/usr/bin/env python3
"""V11: consequence-separate statistic genesis before cross-domain transfer.

V10 discovered that many raw-trace summaries were equally adequate on the original B
program tasks. V11 does not tie-break them. It adds a frozen, C-blind verifier
separator suite in which sparse catastrophic and diffuse small errors have different
protected consequences. Statistic programs are judged only by whether their induced
candidate ordering agrees with those verifier consequences plus the original B tasks.
Equivalent syntax is allowed only when it induces the same complete behavior.
"""
from __future__ import annotations
import hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import policy_language_genesis_cross_domain_v10 as v10

# Each case is (name, candidate raw traces, protected-success candidate).
# The traces are deliberately distribution-shape separators. No orbital/C data.
SEP_CASES=(
 ('diffuse_beats_large_spike',
  {'spike':(0.,0.,0.,4.), 'diffuse':(1.5,1.5,1.5,1.5), 'bad':(3.,3.,3.,3.)},
  'diffuse'),
 ('small_spike_beats_diffuse_peak',
  {'spike':(0.,0.,0.,2.), 'diffuse':(1.2,1.2,1.2,1.2), 'bad':(2.5,2.5,2.5,2.5)},
  'spike'),
 ('quadratic_penalty_prefers_balanced',
  {'imbalanced':(0.,0.,0.,3.), 'balanced':(1.1,1.1,1.1,1.1), 'bad':(2.,2.,2.,2.)},
  'balanced'),
)

def sep_order(kast, traces):
    return tuple(sorted(traces,key=lambda n:(v10.stat_eval(kast,traces[n]),n)))

def sep_signature(kast):
    return tuple(sep_order(kast,tr) for _,tr,_ in SEP_CASES)

def sep_calls(kast):
    total=0; per=[]; solved=True
    for name,tr,winner in SEP_CASES:
        order=sep_order(kast,tr); k=order.index(winner)+1
        total+=k; per.append((name,k,winner,order))
        if k!=1: solved=False
    return solved,total,per

def full_behavior(kast):
    return (v10.stat_behavior(kast),sep_signature(kast))

def synthesize_statistic_v11():
    rows=[]
    for kast in v10.stat_programs():
        # Original B discovery competence.
        bper=[]; btotal=0; bsolved=True
        for name,pts,t in v10.BTASKS:
            calls,hit=v10.b_calls_stat(kast,pts,t); btotal+=calls; bper.append((name,calls,hit))
            if hit is None:bsolved=False
        ssolved,stotal,sper=sep_calls(kast)
        solved=bsolved and ssolved
        rows.append((not solved,btotal+stotal,v10.stat_cost(kast),repr(kast),kast,bper,sper,full_behavior(kast)))
    rows.sort(key=lambda z:(z[0],z[1],z[2],z[3]))
    print('V11_STATISTIC_TOP',[(z[1],z[4],z[5],z[6]) for z in rows[:8]])
    assert rows and not rows[0][0],rows[:8]
    metric=rows[0][:3]; best=[z for z in rows if z[:3]==metric]
    behaviors={repr(z[7]) for z in best}
    assert len(behaviors)==1,('NONUNIQUE_CONSEQUENCE_SEPARATED_BEHAVIOR',[(z[4],z[6]) for z in best])
    winner=min(best,key=lambda z:z[3]); kast=winner[4]
    # Require every genuinely different minimal-cost behavior to lose a protected separator.
    winbeh=winner[7]
    competitors=[]
    for z in rows:
        if z[2]>winner[2] or z[7]==winbeh: continue
        competitors.append(z)
    assert competitors,'no competing statistic behaviors'
    assert all(z[0] for z in competitors),[(z[4],z[6]) for z in competitors if not z[0]]
    print('B_SYNTHESIZED_STATISTIC_AST',kast)
    print('CONSEQUENCE_SEPARATOR_SUITE',[(n,w) for n,_,w in SEP_CASES])
    print('GENUINELY_DISTINCT_MINIMAL_STATISTICS_DEFEATED_BY_CONSEQUENCE=PASS')
    print('NO_ARBITRARY_STATISTIC_TIEBREAK=PASS')
    return kast,rows

def main():
    v10.lean_gate()
    kast,krows=synthesize_statistic_v11()
    past,prows=v10.synthesize_policy(kast)
    stack=(kast,past); digest=hashlib.sha256(repr(stack).encode()).hexdigest()
    print('B_FROZEN_CONSEQUENCE_SELECTED_STACK',stack)
    print('B_FROZEN_STACK_SHA256',digest)

    # C first touched only after the whole stack is frozen.
    src,ma,cand=v10.c_setup()
    warm=v10.c_run(kast,past,src,ma,cand)
    print('C_V11_WARM',warm[0],None if warm[1] is None else warm[1].text,warm[2])
    print('C_V11_TRIED',warm[3]); assert warm[0] is not None,warm[3]

    # Exact K ablation: no learned statistic, same six-query budget.
    dummy=('REDUCE','SUM',('MAP','ID',('RAW',)))
    ablation_policies=(((1,'c'),),((-1,'c'),),((1,'v'),),((-1,'v'),))
    ab=[]
    for q in ablation_policies:
        z=v10.c_run(dummy,q,src,ma,cand);ab.append((q,z));print('C_NO_K_CONTROL',q,z[0],z[3])
    assert all(z[1][0] is None for z in ab),ab

    # Every genuinely different statistic behavior from the finite grammar gets the exact learned policy and same budget.
    alt=[];seen=set(); winbeh=full_behavior(kast)
    for row in krows:
        q=row[4];beh=row[7]
        sig=repr(beh)
        if q==kast or beh==winbeh or sig in seen:continue
        seen.add(sig); z=v10.c_run(q,past,src,ma,cand);alt.append((q,z));print('C_ALT_K',q,z[0],z[3])
    assert alt,'no alternative statistic behaviors'
    assert all(z[1][0] is None for z in alt),alt

    assert hashlib.sha256(repr(stack).encode()).hexdigest()==digest
    print('MATCHED_CANDIDATE_QUERY_BUDGET',v10.C_BUDGET)
    print('RAW_TRACE_STATISTIC_FORCED_BY_PROTECTED_CONSEQUENCES=PASS')
    print('STATISTIC_PROMOTED_TO_POLICY_LANGUAGE=PASS')
    print('EXACT_CONSEQUENCE_SELECTED_STACK_UNCHANGED_B_TO_C=PASS')
    print('STATISTIC_ABLATION_RESTORES_COLD_FRONTIER=PASS')
    print('ALL_DISTINCT_STATISTIC_BEHAVIORS_FAIL_MATCHED_C_BUDGET=PASS')
    print('CONSEQUENCE_SEPARATED_POLICY_LANGUAGE_GENESIS_V11=PASS')
    print('BOUNDARY=finite generic statistic grammar and frozen separator suite supplied; C remains blind until stack freeze')

if __name__=='__main__':main()
