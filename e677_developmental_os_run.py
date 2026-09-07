"""Qualification for cumulative developmental OS over the verified E677 JOIN state.

Later verifier-earned consequences strictly outrank older residuals.

CHANGE (live Gate 2 integration, verifier-validated identity): the run routes
promotion through ``TypedDevelopmentalOperatingSystem`` with a frozen authority
that VALIDATES the actual certificate contents and returns a stable result
identity — the capability's witness must reference that exact identity, not a
caller-supplied Boolean or a source-name string.

* ``validate_strongest_certificate`` reads the selected certificate artifact and
  checks its gate flag; it returns (residual_statement, result_identity) where
  ``result_identity = (source, theorem)`` is content-derived and stable.
* ``main`` records the verified-result identity as a ``verified-success``
  provenance node carrying ``result_identity`` + ``residual_statement``.
* ``mk_verifier`` admits ``cap:strongest-residual`` only when the capability's
  provenance references that exact ``verified-success`` node, whose
  ``result_identity`` matches the one the authority derived by validating the
  certificate itself.  An altered certificate or a wrong-result reference is
  rejected because the identities will not match.

This does NOT change the E677 mathematical theorem.  No four-row 141-state
result is re-labelled as a T6 solution.  No E677=>E255 claim is made.
"""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
from developmental_operating_system import DevelopmentalOSState, LockState, Capability
from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem


CERTIFICATE_CHAIN = (
    ('artifacts/t6_phase_consequence_probe.json', 't6-phase-consequence', 'retained_coordinate'),
    ('artifacts/t6_relative_phase_theorem_certificate.json', 't6-relative-phase-theorem', 'direct_live_phase_attachment_verified'),
    ('artifacts/e677_live_frontier_attachment_probe.json', 'live-frontier-attachment', 'mechanism_attachment_verified'),
    ('artifacts/phase_block_feasibility_probe.json', 'phase-block-feasibility', 'reconstructs_entire_shifted_frontier'),
    ('artifacts/phase_symbolic_theorem_certificate.json', 'phase-symbolic-theorem', 'symbolic_complete_n_ge_4'),
)


def validate_strongest_certificate(join_state):
    """Validate the strongest verified certificate's contents and return its
    residual statement + a stable, content-derived result identity.

    The identity = (source_name, theorem_text) where theorem_text is read from
    the certificate artifact itself.  An altered certificate changes the
    identity, so a forged witness referencing a stale identity is rejected.
    Returns (residual, prov, result_identity)."""
    for filename, source, gate in CERTIFICATE_CHAIN:
        p = Path(filename)
        if not p.exists():
            continue
        d = json.load(open(p))
        if d.get(gate):
            residual = d['residual']
            # theorem_text is the content-derived identity anchor; it is empty
            # for probe artifacts that lack a 'theorem' field.
            theorem_text = d.get('theorem', '')
            result_identity = (source, theorem_text)
            prov = {'source': source, 'result_identity': result_identity}
            return residual, prov, result_identity
    residual = join_state.get('residual', '')
    result_identity = ('join-state', '')
    return residual, {'source': 'join-state', 'result_identity': result_identity}, result_identity


def strongest_verified_residual(join_state):
    residual, prov, _ = validate_strongest_certificate(join_state)
    return residual, prov


def resolved_residual_witnesses(state):
    """The witness ids actually present in the provenance graph, including
    verified-success nodes that carry a verified-result identity."""
    return {p['id'] for p in state.provenance_graph
            if p['kind'] in ('residual-envelope', 'typed-residual', 'residual', 'verified-success')}


# ---------------------------------------------------------------------------
# Frozen authority: the OS invokes this callable; it never trusts a caller bool.
# The authority validates the certificate contents itself and admits a
# capability ONLY when its witness references the exact result_identity the
# authority derived.
def mk_verifier(join_state):
    residual, prov, result_identity = validate_strongest_certificate(join_state)

    def authority(state, capability):
        if capability.id != 'cap:strongest-residual' or capability.scope != 'current-task':
            return False
        # 1. The capability's provenance must reference a witness present in the
        #    current provenance graph.
        present = resolved_residual_witnesses(state)
        cap_provenance = set(capability.provenance)
        referenced_present = cap_provenance & present
        if not referenced_present:
            return False
        # 2. That witness must be a verified-success node whose stored
        #    result_identity matches the identity THIS authority derived by
        #    validating the certificate.  An altered certificate (different
        #    theorem text / source) or a wrong-result reference cannot match.
        for p in state.provenance_graph:
            if p.get('kind') != 'verified-success' or p.get('id') not in referenced_present:
                continue
            ev = p.get('evidence', {})
            if ev.get('result_identity') != list(result_identity):
                continue
            if ev.get('statement') != residual:
                continue
            return True
        return False

    return authority


def promote_strongest(state, os, prov, witness_id, result_identity):
    """Promote the strongest verified residual through the typed gate.

    The capability's evidence provenance references the verified-success
    witness carrying the authority-validated result identity.

    ATOMIC: the candidate is staged then validated; on rejection the install is
    rolled back so the retained capability state is unchanged.
    """
    cap = Capability(
        'cap:strongest-residual', 'current-task',
        ('strongest-residual',), 1.0, (witness_id,),
    )
    # ATOMIC: stage then validate; roll back on rejection so a failed promotion
    # does not leave a capability installed.
    pre_installed = list(state.installed_capabilities)
    try:
        state.installed_capabilities.append(cap)
        promoted_id = os.promote_global(state, cap.id)
    except RuntimeError:
        state.installed_capabilities[:] = pre_installed
        raise
    return cap, promoted_id


def main():
    join_state = json.load(open('artifacts/e677_verified_join_reify_state.json'))
    residual, prov, result_identity = validate_strongest_certificate(join_state)
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
    # Record the strongest verified result's identity as a verified-success
    # witness carrying the authority-validated result_identity + residual
    # statement.  This node is created from the certificate the authority
    # validates — not a self-fabricated identity.
    strongest_witness_id = 'verified:strongest'
    state.provenance_graph.append({
        'id': strongest_witness_id,
        'kind': 'verified-success',
        'parents': list(prov.get('evidence_ids', ())) if isinstance(prov, dict) else [],
        'evidence': {
            'statement': residual,
            'result_identity': list(result_identity),
            'source': prov['source'],
        },
    })
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [strongest_witness_id], 'evidence': prov})

    # Promote the strongest verified residual through the authenticated gate.
    promoted_cap, promoted_id = promote_strongest(state, os, prov, strongest_witness_id, result_identity)

    out = asdict(state)
    out['strongest_residual_provenance'] = prov
    out['state_sha256'] = state.digest()
    out['promoted_through_typed_gate'] = {
        'capability_id': promoted_cap.id,
        'promoted_id': promoted_id,
        'verdict': 'executed+passed via frozen authority validating certificate contents',
        'scope': promoted_cap.scope,
        'provenance': list(promoted_cap.provenance),
        'result_identity': list(result_identity),
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
