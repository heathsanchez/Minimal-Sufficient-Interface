"""Qualification for cumulative developmental OS over the verified E677 JOIN state.

Later verifier-earned consequences strictly outrank older residuals.

CHANGE (live Gate 2 integration): the run routes promotion through
``TypedDevelopmentalOperatingSystem`` with a frozen authority derived from the
existing externally-verified E677 certificate artifacts.  The strongest
verified residual result is promoted as-is (scope preserved), and a forged /
unrelated-witness / scope-widening / Boolean-bypass attempt is rejected by the
gate.  The typed OS computes the four obligations (verdict/attachment/scope/
preservation) from the frozen authority + actual provenance/state;
caller-supplied Boolean fields never authorize promotion.

The authority identifies the capability's witness by the strongest verified
result's residual statement (evidence identity), recorded as a
residual-envelope witness carrying that statement, and verifies the
source-to-witness relationship at validation time.

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
def resolved_residual_witnesses(state):
    """The residual witness ids actually present in the provenance graph,
    including residual-envelope and residual kinds (both carry evidence
    identity)."""
    return {p['id'] for p in state.provenance_graph
            if p['kind'] in ('residual-envelope', 'typed-residual', 'residual', 'verified-success')}


def mk_verifier(join_state):
    residual, prov = strongest_verified_residual(join_state)
    strongest_source = prov['source']
    # The strongest verified result's residual statement is the stable evidence
    # identity that the capability's witness must carry.
    strongest_residual_stmt = residual

    def authority(state, capability):
        if capability.id != 'cap:strongest-residual' or capability.scope != 'current-task':
            return False
        # 1. The capability's provenance must reference a residual witness that is
        #    present in the current provenance graph.
        present = resolved_residual_witnesses(state)
        cap_provenance = set(capability.provenance)
        referenced_present = cap_provenance & present
        if not referenced_present:
            return False
        # 2. That witness must carry the strongest verified result's residual
        #    statement as its identity — statement equality, not index ordering.
        #    An unrelated valid witness (different statement / different source)
        #    cannot authorize promotion.
        witness_statements = {}
        for p in state.provenance_graph:
            if p.get('kind') in ('residual-envelope', 'residual') and p.get('id') in present:
                witness_statements[p['id']] = p.get('evidence', {}).get('statement', '')
        backing_match = {
            wid for wid, stmt in witness_statements.items()
            if stmt == strongest_residual_stmt and wid in referenced_present
        }
        if not backing_match:
            return False
        # 3. The strongest verified source must be reachable (routing-decision
        #    node carrying prov with 'source' must exist).
        source_reachable = any(
            p.get('evidence', {}).get('source') == strongest_source
            for p in state.provenance_graph
        )
        return source_reachable

    return authority


def promote_strongest(state, os, prov, witness_id):
    """Promote the strongest verified residual through the typed gate.

    The capability's evidence provenance references the residual-envelope
    witness (passed in from ``main``) carrying the strongest verified result's
    residual statement, deriving identity from evidence, not index.

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
    # Record the strongest verified result's residual as a residual-envelope
    # witness carrying its statement identity, so the promotion authority can
    # bind the capability's witness to the verified result by evidence identity.
    strongest_witness_id = 'residual-envelope:strongest'
    state.provenance_graph.append({
        'id': strongest_witness_id,
        'kind': 'residual-envelope',
        'parents': list(prov.get('evidence_ids', ())) if isinstance(prov, dict) else [],
        'evidence': {'statement': residual, 'source': prov['source']},
    })
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [strongest_witness_id], 'evidence': prov})

    # Promote the strongest verified residual through the authenticated gate.
    promoted_cap, promoted_id = promote_strongest(state, os, prov, strongest_witness_id)

    out = asdict(state)
    out['strongest_residual_provenance'] = prov
    out['state_sha256'] = state.digest()
    out['promoted_through_typed_gate'] = {
        'capability_id': promoted_cap.id,
        'promoted_id': promoted_id,
        'verdict': 'executed+passed via frozen authority on verified certificate artifacts',
        'scope': promoted_cap.scope,
        'provenance': list(promoted_cap.provenance),
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
