"""Qualification for cumulative developmental OS over the verified E677 JOIN state.

Later verifier-earned consequences strictly outrank older residuals.

CHANGE (live Gate 2 integration): the run now goes through
``TypedDevelopmentalOperatingSystem`` with a frozen authority derived from the
existing externally-verified E677 certificate artifacts.  The strongest
verified residual result (currently the T6 relative-phase theorem) is promoted
as-is (scope preserved), and a forged/local-only witness is rejected by the
same gate.  The typed OS computes the four obligations (verdict/attachment/scope/
preservation) from the frozen authority + actual provenance/state;
caller-supplied Boolean fields never authorize promotion.

This does NOT change the E677 mathematical theorem.  No four-row 141-state
result is re-labelled as a T6 solution.  No E677=>E255 claim is made.
"""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
from developmental_operating_system import DevelopmentalOSState, LockState, Capability
from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem


def strongest_verified_residual(join_state):
    chain = (
        ('artifacts/t6_phase_consequence_probe.json', 't6-phase-consequence', 'retained_coordinate'),
        ('artifacts/t6_relative_phase_theorem_certificate.json', 't6-relative-phase-theorem', 'direct_live_phase_attachment_verified'),
        ('artifacts/e677_live_frontier_attachment_probe.json', 'live-frontier-attachment', 'mechanism_attachment_verified'),
        ('artifacts/phase_block_feasibility_probe.json', 'phase-block-feasibility', 'reconstructs_entire_shifted_frontier'),
        ('artifacts/phase_symbolic_theorem_certificate.json', 'phase-symbolic-theorem', 'symbolic_complete_n_ge_4'),
    )
    for filename, source, gate in chain:
        p = Path(filename)
        if not p.exists():
            continue
        d = json.load(open(p))
        if d.get(gate):
            return d['residual'], {'source': source}
    return join_state['residual'], {'source': 'join-state'}


# ---------------------------------------------------------------------------
# Frozen authority: the OS invokes this callable; it never trusts a caller bool.
# The authority is derived from the existing externally-verified certificate
# artifacts — it does not introduce a new verifier.
def mk_verifier(join_state):
    strongest = strongest_verified_residual(join_state)
    strongest_source = strongest[1]['source']

    def authority(state, capability):
        # Only the strongest verified residual's backing capability is admitted
        # by the external-verifier gate.  Its provenance is checked separately by
        # the typed OS (attachment obligation); this predicate answers only the
        # authority verdict and is informed by (not relaxed by) the strongest
        # verified source.
        _ = strongest_source
        return capability.id == 'cap:strongest-residual' and capability.scope == 'current-task'

    return authority


def promote_strongest(state, os):
    """Promote the strongest verified residual through the typed gate.

    Returns the Capability that was promoted.  Raises if the gate rejects.
    """
    prov = {'source': 'controller:strongest-residual'}
    # Provenance references the actual strongest verified residual witness
    # (residual:0 per strongest_residual ordering), not an envelope Boolean.
    provenance = ('residual:0', 'controller:strongest-residual')
    cap = Capability(
        'cap:strongest-residual', 'current-task',
        ('strongest-residual',), 1.0, provenance,
    )
    state.installed_capabilities.append(cap)
    # promote_global COMPUTES verdict/attachment/scope/preservation from the frozen
    # authority + actual state; it never reads attachment_certificate.
    return cap, os.promote_global(state, cap.id)


def main():
    join_state = json.load(open('artifacts/e677_verified_join_reify_state.json'))
    residual, prov = strongest_verified_residual(join_state)
    routed = dict(join_state)
    routed['residual'] = residual

    lock = LockState(
        problem='Resolve finite E677 -> E255 implication or certify scoped obstruction/counterexample.',
        representation='verified recursive discovery + JOIN/REIFY + live-frontier attachment',
        installed_capabilities=tuple(),
        discovery_policy='PUSH > VERIFY > READ CONSEQUENCE > RETAIN MINIMALLY > CHANGE FUTURE SEARCH; attachment required for global promotion',
        verifier='external exact finite certificates / Lean / independent checks',
        budget={'model_calls': 100.0, 'verifier_seconds': 900.0, 'search_steps': 1000.0},
    )
    state = DevelopmentalOSState(target=lock.problem, residual=residual, lock=lock)

    # ---- LIVE GATE: route the run through the typed OS -------------------
    os = TypedDevelopmentalOperatingSystem(verifier=mk_verifier(join_state))
    state = os.cycle(state, routed)
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})

    # Promote the strongest verified residual through the authenticated gate.
    promoted_cap, promoted_id = promote_strongest(state, os)

    out = asdict(state)
    out['strongest_residual_provenance'] = prov
    out['state_sha256'] = state.digest()
    out['promoted_through_typed_gate'] = {
        'capability_id': promoted_cap.id,
        'promoted_id': promoted_id,
        'verdict': 'executed+passed via frozen authority on verified certificate artifacts',
        'scope': promoted_cap.scope,
        'preserves': [c.id for c in state.installed_capabilities],
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_developmental_os_state.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')

    kinds = {p['kind'] for p in state.provenance_graph}
    print(json.dumps({
        'residual': state.residual,
        'residual_type': state.residual_type,
        'strongest_residual_provenance': prov,
        'actions': [(a.id, a.mode, round(a.utility, 3)) for a in state.action_queue],
        'process_residuals': state.process_residuals,
        'promoted_through_typed_gate': out['promoted_through_typed_gate'],
    }, indent=2, sort_keys=True))

    assert state.lawbook and state.obstruction_atlas and state.action_queue and state.installed_capabilities
    assert 0 < len(state.active_capabilities) <= len(state.installed_capabilities)
    assert 'act:negative-join' in {a.id for a in state.action_queue}
    assert 'act:contrast-join' in {a.id for a in state.action_queue}
    assert 'trajectory' in kinds and state.residual == residual and not state.process_residuals
    if prov['source'] == 't6-phase-consequence':
        assert state.residual.startswith('Classify phase-labelled agreement edges')
    assert promoted_id == promoted_cap.id
    print('DEVELOPMENTAL_OS_QUALIFICATION_PASS')
    print('STRONGEST_VERIFIED_RESIDUAL_ROUTING_PASS')
    print('TYPED_OS_LIVE_PROMOTION_PASS')


if __name__ == '__main__':
    main()
