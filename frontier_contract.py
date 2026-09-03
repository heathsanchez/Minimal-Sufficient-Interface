"""Validate structural invariants of the authoritative programme frontier.

The contract is deliberately state-agnostic: legitimate mathematical progress may
change the live residual, promoted result set, or last transition. This validator
checks the constitution of the state, not a frozen snapshot of its contents.
"""
from __future__ import annotations
import json
from pathlib import Path

ALLOWED_STATUS={"PROMOTE","PARK","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT"}
ALLOWED_RESIDUAL={"DERIVATION","VERIFICATION","ATTACHMENT","REFRAME","OBSTRUCTION","INFRA","UNKNOWN"}
ALLOWED_TRANSITION={"PROMOTE","PARK","PARK_AND_REFRAME","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT","REFRAME","SKIP"}


def main():
    x=json.loads(Path('program_frontier.json').read_text())
    assert x.get('authoritative') is True
    assert isinstance(x.get('schema_version'),int) and x['schema_version']>=5
    assert isinstance(x.get('target'),str) and x['target'].strip()
    assert isinstance(x.get('constitutional_loop'),list) and len(x['constitutional_loop'])>=5
    assert isinstance(x.get('promotion_contract'),list) and x['promotion_contract']

    # There is exactly one explicit live residual object.
    r=x.get('live_residual')
    assert isinstance(r,dict) and set(('type','text')) <= set(r)
    assert r['type'] in ALLOWED_RESIDUAL and isinstance(r['text'],str) and r['text'].strip()

    # Evidence ledgers are typed and classifications are explicit.
    for group in ('promoted','parked'):
        vals=x.get(group)
        assert isinstance(vals,list)
        ids=[]
        for v in vals:
            assert isinstance(v,dict) and isinstance(v.get('id'),str) and v['id']
            assert v.get('status') in ALLOWED_STATUS
            ids.append(v['id'])
        assert len(ids)==len(set(ids)), f'duplicate ids in {group}'

    # The frozen n=7 D accounting remains internally consistent while present.
    if 'curvature_spectrum' in x:
        spectrum={int(k):int(v) for k,v in x['curvature_spectrum'].items()}
        assert all(k>=0 and v>=0 for k,v in spectrum.items())
        if 'nonlinear_D_total' in x:
            assert sum(spectrum.values())==x['nonlinear_D_total']
        if 'affine_D_total' in x and 'full_D_total' in x:
            assert x['nonlinear_D_total']+x['affine_D_total']==x['full_D_total']

    # A state transition must retain provenance and an explicit classification.
    t=x.get('last_transition')
    assert isinstance(t,dict) and t.get('classification') in ALLOWED_TRANSITION
    assert isinstance(t.get('result_id'),str) and t['result_id']

    assert isinstance(x.get('negative_laws'),list)
    assert isinstance(x.get('process_laws'),list)
    assert any('conversation' in v.lower() and 'authoritative' in v.lower() for v in x['process_laws'])
    assert any('version space is exhausted' in v.lower() for v in x['process_laws'])

    print('PROGRAM_FRONTIER_VERIFIED')
    print('SCHEMA_VERSION='+str(x['schema_version']))
    print('LIVE_RESIDUAL_TYPE='+r['type'])
    print('LIVE_RESIDUAL='+r['text'])
    print('LAST_TRANSITION='+t['classification']+':'+t['result_id'])

if __name__=='__main__': main()
