"""Qualification for cumulative developmental OS over the verified E677 JOIN state.

Later verifier-earned consequences strictly outrank older residuals.
"""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
from developmental_operating_system import DevelopmentalOperatingSystem, DevelopmentalOSState, LockState


def strongest_verified_residual(join_state):
    chain=(
        ('artifacts/t6_phase_consequence_probe.json','t6-phase-consequence','retained_coordinate'),
        ('artifacts/t6_relative_phase_theorem_certificate.json','t6-relative-phase-theorem','direct_live_phase_attachment_verified'),
        ('artifacts/e677_live_frontier_attachment_probe.json','live-frontier-attachment','mechanism_attachment_verified'),
        ('artifacts/phase_block_feasibility_probe.json','phase-block-feasibility','reconstructs_entire_shifted_frontier'),
        ('artifacts/phase_symbolic_theorem_certificate.json','phase-symbolic-theorem','symbolic_complete_n_ge_4'),
    )
    for filename,source,gate in chain:
        p=Path(filename)
        if not p.exists(): continue
        d=json.load(open(p))
        if d.get(gate): return d['residual'], {'source':source}
    return join_state['residual'], {'source':'join-state'}


def main():
    join_state=json.load(open('artifacts/e677_verified_join_reify_state.json'))
    residual,prov=strongest_verified_residual(join_state)
    routed=dict(join_state); routed['residual']=residual
    lock=LockState(
        problem='Resolve finite E677 -> E255 implication or certify scoped obstruction/counterexample.',
        representation='verified recursive discovery + JOIN/REIFY + live-frontier attachment',
        installed_capabilities=tuple(),
        discovery_policy='PUSH > VERIFY > READ CONSEQUENCE > RETAIN MINIMALLY > CHANGE FUTURE SEARCH; attachment required for global promotion',
        verifier='external exact finite certificates / Lean / independent checks',
        budget={'model_calls':100.0,'verifier_seconds':900.0,'search_steps':1000.0},
    )
    state=DevelopmentalOSState(target=lock.problem,residual=residual,lock=lock)
    state=DevelopmentalOperatingSystem().cycle(state,routed)
    state.provenance_graph.append({'id':'controller:strongest-residual','kind':'routing-decision','parents':[],'evidence':prov})
    out=asdict(state); out['strongest_residual_provenance']=prov; out['state_sha256']=state.digest()
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_developmental_os_state.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    kinds={p['kind'] for p in state.provenance_graph}
    print(json.dumps({'residual':state.residual,'residual_type':state.residual_type,'strongest_residual_provenance':prov,'actions':[(a.id,a.mode,round(a.utility,3)) for a in state.action_queue],'process_residuals':state.process_residuals},indent=2,sort_keys=True))
    assert state.lawbook and state.obstruction_atlas and state.action_queue and state.installed_capabilities
    assert 0 < len(state.active_capabilities) <= len(state.installed_capabilities)
    assert 'act:negative-join' in {a.id for a in state.action_queue}
    assert 'act:contrast-join' in {a.id for a in state.action_queue}
    assert 'trajectory' in kinds and state.residual==residual and not state.process_residuals
    if prov['source']=='t6-phase-consequence':
        assert state.residual.startswith('Classify phase-labelled agreement edges')
    print('DEVELOPMENTAL_OS_QUALIFICATION_PASS')
    print('STRONGEST_VERIFIED_RESIDUAL_ROUTING_PASS')

if __name__=='__main__': main()
