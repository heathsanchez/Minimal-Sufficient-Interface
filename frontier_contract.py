"""Validate authoritative programme frontier."""
import json
from pathlib import Path
ALLOWED={"PROMOTE","PARK","SUPERSEDE","REJECT","REQUIRE_ATTACHMENT"}

def main():
    x=json.loads(Path('program_frontier.json').read_text())
    assert x['authoritative'] and x['schema_version']>=5
    assert set(int(v['kappa']) for v in x['promoted'] if 'kappa' in v)=={18,22,24,26,30}
    assert x['curvature_spectrum']=={'18':294,'22':882,'24':1470,'26':1764,'30':588}
    assert sum(x['curvature_spectrum'].values())==4998==x['nonlinear_D_total']
    assert x['affine_D_total']==42 and x['nonlinear_D_total']+x['affine_D_total']==5040
    assert x['live_residual']['type']=='VERIFICATION' and '42 affine D' in x['live_residual']['text']
    assert x['last_transition']['result_id']=='kappa30_excluded'
    assert (x['last_transition']['run_id'],x['last_transition']['job_id'],x['last_transition']['artifact_id'])==(33729377790,100565598433,9883235360)
    for group in ('promoted','parked'):
        assert all(v['status'] in ALLOWED for v in x[group])
    assert any('version space is exhausted' in v.lower() for v in x['process_laws'])
    print('PROGRAM_FRONTIER_VERIFIED')
    print('PROMOTED_KAPPAS=18,22,24,26,30')
    print('LIVE_RESIDUAL='+x['live_residual']['text'])
if __name__=='__main__': main()
