"""Qualification for cumulative developmental OS over the verified E677 JOIN state."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from developmental_operating_system import DevelopmentalOperatingSystem, DevelopmentalOSState, LockState


def main():
    join_state = json.load(open('artifacts/e677_verified_join_reify_state.json'))
    lock = LockState(
        problem='Resolve finite E677 -> E255 implication or certify scoped obstruction/counterexample.',
        representation='verified recursive discovery + JOIN/REIFY',
        installed_capabilities=tuple(),
        discovery_policy='PUSH > PROBE > REFRAME > META; escalation requires verified insufficiency evidence',
        verifier='external exact finite certificates / Lean / independent checks',
        budget={'model_calls': 100.0, 'verifier_seconds': 900.0, 'search_steps': 1000.0},
    )
    state = DevelopmentalOSState(target=lock.problem, residual=join_state['residual'], lock=lock)
    os = DevelopmentalOperatingSystem()
    state = os.cycle(state, join_state)

    out = asdict(state)
    out['state_sha256'] = state.digest()
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_developmental_os_state.json').write_text(json.dumps(out, indent=2, sort_keys=True)+'\n')

    kinds = {p['kind'] for p in state.provenance_graph}
    summary = {
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
    assert not state.process_residuals, state.process_residuals
    print('DEVELOPMENTAL_OS_QUALIFICATION_PASS')

if __name__ == '__main__':
    main()
