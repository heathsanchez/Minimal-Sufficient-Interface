"""Causal qualification tests for the developmental operating system.

These are process tests, not object-level E677 claims. Each test has an ablation.
"""
from __future__ import annotations
from developmental_operating_system import (
    DevelopmentalOperatingSystem, DevelopmentalOSState, LockState,
    Action, Obstruction,
)


def base_state(residual: str) -> DevelopmentalOSState:
    return DevelopmentalOSState(
        target='qualification target', residual=residual,
        lock=LockState(
            problem='qualification target', representation='test', installed_capabilities=(),
            discovery_policy='verified residual routing', verifier='independent qualification assertions',
            budget={'model_calls': 2.0, 'search_steps': 2.0, 'verifier_seconds': 10.0},
        ),
    )


def test_suppression_ablation():
    os = DevelopmentalOperatingSystem()
    bad = Action('act:bad','PUSH','repeat dominated route',('repeat-low-leverage-route',),9,9,0.1)
    good = Action('act:good','PROBE','new discriminating route',(),2,2,1.0)

    with_obstruction = base_state('find a separating observable')
    with_obstruction.action_queue = [bad, good]
    with_obstruction.obstruction_atlas = [Obstruction(
        'obs:x','old route','verified low leverage','qualification',{},('repeat-low-leverage-route',)
    )]
    os.suppress_dominated_actions(with_obstruction)
    assert [a.id for a in with_obstruction.action_queue] == ['act:good']

    ablated = base_state('find a separating observable')
    ablated.action_queue = [bad, good]
    os.suppress_dominated_actions(ablated)
    assert 'act:bad' in {a.id for a in ablated.action_queue}
    return {'full':'dominated route suppressed','ablation':'dominated route returns'}


def test_typed_routing():
    os = DevelopmentalOperatingSystem()
    cases = {
        'REPRESENTATION':'Find the smallest quotient representation preserving shifted realizability without full state.',
        'OBSERVABLE':'Find a probe observable that separates the two surviving explanations.',
        'VERIFIER':'The verifier certificate cannot replay the claimed theorem.',
        'INFRA':'The runner timed out because a dependency install failed.',
    }
    out={}
    for expected,text in cases.items():
        got,scores=os.classify_residual(text)
        assert got == expected, (expected,got,scores)
        out[expected]=scores[expected]
    return out


def test_budget_debit_and_boundary():
    os=DevelopmentalOperatingSystem(); s=base_state('representation quotient needed')
    s.residual_type='REPRESENTATION'; s.remaining_budget=dict(s.lock.budget)
    s.action_queue=[Action('act:r','REFRAME','reframe',(),3,3,1,residual_types=('REPRESENTATION',))]
    a1=os.select_and_debit_next_action(s)
    assert a1 and a1.id=='act:r'
    assert s.remaining_budget['model_calls']==1.0 and s.remaining_budget['search_steps']==1.0
    a2=os.select_and_debit_next_action(s)
    assert a2 and s.remaining_budget['model_calls']==0.0 and s.remaining_budget['search_steps']==0.0
    a3=os.select_and_debit_next_action(s)
    assert a3 is None
    assert len(s.action_history)==2
    return {'selected':2,'third':'blocked-by-budget','remaining':s.remaining_budget}


def test_representation_route_wakes_reframe():
    os=DevelopmentalOperatingSystem(); s=base_state('Search for the smallest quotient of permutation action that preserves shifted realizability without retaining full state.')
    s.residual_type,s.residual_type_scores=os.classify_residual(s.residual)
    os.wake_actions(s)
    ids=[a.id for a in s.action_queue]
    assert s.residual_type=='REPRESENTATION'
    assert 'act:reframe' in ids
    # Routed representation work must beat raw push in this residual.
    assert ids.index('act:reframe') < ids.index('act:push')
    return {'type':s.residual_type,'queue':ids}


def main():
    results={
        'suppression_ablation':test_suppression_ablation(),
        'typed_routing':test_typed_routing(),
        'budget':test_budget_debit_and_boundary(),
        'representation_route':test_representation_route_wakes_reframe(),
    }
    import json
    print(json.dumps(results,indent=2,sort_keys=True))
    print('DEVELOPMENTAL_OS_CAUSAL_QUALIFICATION_PASS')

if __name__=='__main__': main()
