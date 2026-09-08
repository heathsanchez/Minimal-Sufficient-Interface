"""Reproduce one finite ARC residual and its Lean certificate from public data."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
from agent import Development, SensorGrammar, observation
from finite_consequence import Repair, conflict_count, digest, lean_certificate, replay

PINNED_TRACE_SHA256='4e8ed8f20fac3303a22009b190e90100ee4e867d8f3e520cdf60bf6896a68d83'

def build(data: bytes):
    actual=hashlib.sha256(data).hexdigest()
    if actual!=PINNED_TRACE_SHA256:raise ValueError('Pinned public trace changed')
    trace=json.loads(data)
    # Freeze at the first externally observed progress event. Later observations
    # are a held-out replay, not part of the certificate's training universe.
    split=next(i for i in range(1,len(trace))
               if trace[i]['levels_completed']>trace[i-1]['levels_completed'])
    d=Development((1,2,3,4),SensorGrammar(feature_bound=32),repair_interval=10000)
    d.level_start=observation(trace[0])
    for i in range(1,split+1):
        d.observe(trace[i-1],trace[i]['action'],trace[i])
    rows=tuple(d.records)
    q=d.base;f=lambda r:r.outcome
    before=conflict_count(rows,q,f)
    if not before or not d.features:raise AssertionError('Expected an actual residual and repair')
    repair=Repair(d.features,before,0,'FINITE_ADEQUATE',None,
                  digest([(q(r),f(r)) for r in rows]),0,0)
    if replay(rows,q,f,repair):raise AssertionError('Training repair failed exact replay')
    # Holdout is read only after the feature is frozen. Do not call refresh().
    d.repair_interval=1000000
    for i in range(split+1,len(trace)):
        d.observe(trace[i-1],trace[i]['action'],trace[i])
    holdout=tuple(d.records[split:])
    # The complete recorded table is also replayed under the frozen interface.
    holdout_residual=conflict_count(holdout,lambda r:(q(r),)+tuple(c.evaluate(r) for c in repair.features),f)
    full_residual=replay(d.records,q,f,repair)
    report={'source_sha256':actual,'rows':len(rows),'before':before,'after':0,
            'features':[c.name for c in repair.features], 'status':'FINITE_REPLAY_CERTIFIED',
            'scope':'first public level, recorded action/outcome pairs only',
            'holdout_rows':len(holdout),'holdout_residual_pairs':holdout_residual,
            'full_replay_residual_pairs':full_residual,
            'competition_score':None,'model_calls':0}
    source=lean_certificate(rows,q,f,repair)
    report['lean_sha256']=hashlib.sha256(source.encode()).hexdigest()
    return report,source

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trace',required=True)
    p.add_argument('--lean',required=True)
    p.add_argument('--report',required=True)
    a=p.parse_args()
    report,source=build(Path(a.trace).read_bytes())
    Path(a.lean).write_text(source)
    Path(a.report).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('FINITE_CONSEQUENCE_REPLAY='+json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
