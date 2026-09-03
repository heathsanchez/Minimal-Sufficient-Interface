"""Qualification for cumulative developmental OS over the verified E677 JOIN state.

V2 adds a live-frontier attachment gate: later verifier-earned residuals outrank older
JOIN residuals, so the controller cannot keep asking an already-solved question.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from developmental_operating_system import DevelopmentalOperatingSystem, DevelopmentalOSState, LockState


def strongest_verified_residual(join_state):
    attachment = Path('artifacts/e677_live_frontier_attachment_probe.json')
    if attachment.exists():
        a = json.load(open(attachment))
        assert a['attachment_status'] in {'DIRECT','MECHANISM_ONLY','NO_ATTACHMENT'}
        return a['residual'], {'source':'live-frontier-attachment','attachment_status':a['attachment_status']}
    block = Path('artifacts/phase_block_feasibility_probe.json')
    if block.exists():
        b = json.load(open(block))
        if b.get('reconstructs_entire_shifted_frontier'):
            return b['residual'], {'source':'phase-block-feasibility'}
    symbolic = Path('artifacts/phase_symbolic_theorem_certificate.json')
    if symbolic.exists():
        s = json.load(open(symbolic))
        if s.get('symbolic_complete_n_ge_4'):
            return s['residual'], {'source':'phase-symbolic-theorem'}
    return join_state['residual'], {'source':'join-state'}


def main():
    join_state = json.load(open('artifacts/e677_verified_join_reify_state.json'))
    residual, residual_provenance = strongest_verified_residual(join_state)
    # Feed the strongest verified consequence into the ordinary OS ingest path.
    routed_join_state = dict(join_state)
    routed_join_state['residual'] = residual

    lock = LockState(
        problem='Resolve finite E677 -> E255 implication or certify scoped obstruction/counterexample.',
        representation='verified recursive discovery + JOIN/REIFY + live-frontier attachment',
        installed_capabilities=tuple(),
        discovery_policy='PUSH > VERIFY > READ CONSEQUENCE > RETAIN MINIMALLY > CHANGE FUTURE SEARCH; attachment required for global promotion',
        verifier='external exact finite certificates / Lean / independent checks',
        budget={'model_calls': 100.0, 'verifier_seconds': 900.0, 'search_steps': 1000.0},
    )
    state = DevelopmentalOSState(target=lock.problem, residual=residual, lock=lock)
    os = DevelopmentalOperatingSystem()
    state = os.cycle(state, routed_join_state)
    state.provenance_graph.append({'id':'controller:strongest-residual','kind':'routing-decision','parents':[], 'evidence':residual_provenance})

    out = asdict(state)
    out['strongest_residual_provenance'] = residual_provenance
    out['state_sha256'] = state.digest()
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_developmental_os_state.json').write_text(json.dumps(out, indent=2, sort_keys=True)+'\n')

    kinds = {p['kind'] for p in state.provenance_graph}
    summary = {
        'residual': state.residual,
        'residual_type': state.residual_type,
        'strongest_residual_provenance': residual_provenance,
        'laws': len(state.lawbook),
        'obstructions': len(state.obstruction_atlas),
        'actions': [(a.id, a.mode, round(a.utility, 3)) for a in state.action_queue],
        'installed_capabilities': [c.id for c in state.installed_capabilities],
        'active_capabilities': state.active_capabilities,
        'macros': [m.id for m in state.macros],
        'evidence_kinds': sorted(kinds),
        'process_residuals': state.process_residuals,
        'state_sha256': state.digest(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    assert state.lawbook, 'Lawbook did not compile positive evidence'
    assert state.obstruction_atlas, 'Obstruction Atlas did not compile negative evidence'
    assert state.action_queue, 'Action Queue did not wake'
    assert state.installed_capabilities, 'promoted concepts did not become installed capabilities'
    assert 0 < len(state.active_capabilities) <= len(state.installed_capabilities)
    assert 'act:negative-join' in {a.id for a in state.action_queue}, 'F+F join not woken'
    assert 'act:contrast-join' in {a.id for a in state.action_queue}, 'S+F join not woken'
    assert 'trajectory' in kinds, 'trajectory dots missing'
    assert state.residual == residual
    if residual_provenance['source'] == 'live-frontier-attachment':
        assert state.residual.startswith('Derive or refute a seven-row T6 phase-labelled')
        assert state.residual_type == 'DERIVATION'
    assert not state.process_residuals, state.process_residuals
    print('DEVELOPMENTAL_OS_QUALIFICATION_PASS')
    print('STRONGEST_VERIFIED_RESIDUAL_ROUTING_PASS')

if __name__ == '__main__':
    main()
