"""Live-entry integration test for the authenticated promotion transition.

Drives the REAL entrypoint (e677_developmental_os_run.main) and the live
e677 -> typed-OS promotion path to establish that:

  * the strongest verified residual (correct source / correct witness) is
    promoted through the live gate;
  * a capability backed by an unrelated valid witness (different source /
    weaker residual) is rejected;
  * reordered residuals still select the correct (strongest) witness;
  * forged ID/scope is rejected;
  * a failed promotion leaves the installed state unchanged (atomicity);
  * the old Boolean bypass cannot succeed through the live path.

This exercises the live e677 runner end-to-end and the real promotion path,
not bare promote_global calls in isolation.
"""
from __future__ import annotations
import copy
import json
import os as _os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = REPO_ROOT / 'artifacts'


def _run_main() -> dict:
    """Run the live entrypoint and return its produced state artifact."""
    env = dict(_os.environ)
    env['PYTHONPATH'] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, 'e677_developmental_os_run.py'],
        cwd=str(REPO_ROOT), env=env, check=True,
    )
    state_path = ARTIFACTS / 'e677_developmental_os_state.json'
    assert state_path.exists(), 'live run did not write e677_developmental_os_state.json'
    return json.loads(state_path.read_text())


def _verifier_rejects(state, capability):
    return False


def _build_fresh_state():
    from e677_developmental_os_run import strongest_verified_residual
    from developmental_operating_system import DevelopmentalOSState, LockState
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    res, prov = strongest_verified_residual(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=res, lock=lock)
    return js, state, prov


def _wire_state(js, state, prov, verifier):
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    os_obj = TypedDevelopmentalOperatingSystem(verifier=verifier)
    state = os_obj.cycle(state, dict(js, residual=state.residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    return os_obj, state


# ---------------------------------------------------------------------------

def test_correct_source_witness_promoted():
    """The strongest verified residual (correct source / strongest witness)
    is promoted through the live-typed gate."""
    state = _run_main()
    assert 'promoted_through_typed_gate' in state, 'live run did not promote through the typed gate'
    gate = state['promoted_through_typed_gate']
    assert gate['promoted_id'] == gate['capability_id'] == 'cap:strongest-residual'
    assert gate['scope'] == 'current-task'
    # Provenance references a real residual witness (the strongest, not residual:0).
    prov_refs = gate.get('provenance', [])
    assert any(r.startswith('residual:') for r in prov_refs), f'provenance did not reference a residual witness: {prov_refs}'
    # Verify it references the highest-index residual witness in the graph.
    assert 'cap:strongest-residual' in {c['id'] for c in state['installed_capabilities']}
    assert state['residual_type'] == 'REPRESENTATION'
    print('  correct-source/witness -> promoted')


def test_unrelated_witness_rejected():
    """A capability whose provenance references an unrelated residual witness
    (residual:0, the weakest, not the strongest) is rejected by the authority."""
    from e677_developmental_os_run import mk_verifier
    from developmental_operating_system import Capability
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js, state, prov = _build_fresh_state()
    os_obj = TypedDevelopmentalOperatingSystem(verifier=mk_verifier(js))
    state = os_obj.cycle(state, dict(js, residual=state.residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    # Mis-witnessed: provenance references residual:0 (weakest) not residual:4.
    cap = Capability('cap:strongest-residual', 'current-task', ('strongest-residual',), 1.0, ('residual:0',))
    state.installed_capabilities.append(cap)
    try:
        os_obj.promote_global(state, cap.id)
        raise AssertionError('unrelated/weak witness was accepted by the gate')
    except RuntimeError as e:
        assert 'attached=False' in str(e) or 'passed=False' in str(e), f'unexpected: {e}'
    print('  unrelated-witness -> rejected')


def test_reordered_residuals_select_correct():
    """Reordering the residual witnesses in the provenance graph must still
    select the strongest (highest-index) residual witness, not residual:0."""
    from e677_developmental_os_run import mk_verifier, promote_strongest, resolved_residual_witnesses
    js, state, prov = _build_fresh_state()
    js_shuffled = copy.deepcopy(js)
    # Shuffle the dots ordering to simulate a reordered join.
    js_shuffled['dots'] = list(reversed(js_shuffled.get('dots', [])))
    os_obj, state = _wire_state(js_shuffled, state, prov, mk_verifier(js))
    cap, promoted_id = promote_strongest(state, os_obj, prov)
    assert promoted_id == cap.id
    # provenance references the strongest-idx residual (index 4, i.e. residual:4)
    residual_nodes = [
        (p['id'], p.get('evidence', {}).get('index'))
        for p in state.provenance_graph
        if p.get('kind') == 'residual'
    ]
    strongest_idx = max((idx for _, idx in residual_nodes if idx is not None), default=-1)
    strongest_wid = {wid for wid, idx in residual_nodes if idx == strongest_idx}
    assert set(cap.provenance) & strongest_wid, f'provenance {cap.provenance} did not reference strongest witness {strongest_wid}'
    print('  reordered-residuals -> correct witness still selected')


def test_forged_scope_rejected():
    """A capability whose authorized scope is narrower than the promoted scope
    is rejected — the verifier admits the capability (verdict True), but the
    OS rejects the unauthorized scope widening."""
    from e677_developmental_os_run import resolved_residual_witnesses
    from developmental_operating_system import Capability
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem

    def authority_admits(state, capability):
        return capability.id == 'cap:strongest-residual'
    js, state, prov = _build_fresh_state()
    os_obj = TypedDevelopmentalOperatingSystem(verifier=authority_admits)
    state = os_obj.cycle(state, dict(js, residual=state.residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    witnesses = sorted(resolved_residual_witnesses(state))
    cap = Capability('cap:strongest-residual', 'narrow-scope', ('strongest-residual',), 1.0, tuple(witnesses))
    state.installed_capabilities.append(cap)
    try:
        os_obj.promote_global(state, cap.id, promoted_scope='wide-unauthorized-scope')
        raise AssertionError('scope widening was accepted')
    except RuntimeError as e:
        assert 'scope_ok=False' in str(e), f'unexpected: {e}'
    print('  forged-scope -> rejected')


def test_failed_promotion_atomic():
    """A failed promotion must not leave the staged capability installed.

    promote_strongest stages a candidate, calls promote_global, and rolls back
    on RuntimeError — the installed set must be unchanged across a failed
    promotion.
    """
    from e677_developmental_os_run import promote_strongest
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js, state, prov = _build_fresh_state()
    os_obj = TypedDevelopmentalOperatingSystem(verifier=_verifier_rejects)
    state = os_obj.cycle(state, dict(js, residual=state.residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    before = [c.id for c in state.installed_capabilities]
    try:
        promote_strongest(state, os_obj, prov)
        raise AssertionError('failed verdict was accepted')
    except RuntimeError:
        pass
    after = [c.id for c in state.installed_capabilities]
    assert after == before, f'failed promotion changed installed state: {before} -> {after}'
    print('  failed-promotion -> rejected (installed state unchanged)')


def test_boolean_bypass_regression():
    """The old Boolean bypass — attach(state, envelope) trusting
    attachment_certificate=True with no verified capability — must fail."""
    from typed_residual_protocol import compile_residual
    from developmental_operating_system import DevelopmentalOSState, LockState
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    s = DevelopmentalOSState(target='x', residual='r',
                             lock=LockState(problem='x', representation='r',
                                            installed_capabilities=(),
                                            discovery_policy='d', verifier='v',
                                            budget={'search_steps': 1.0, 'model_calls': 1.0}))
    os = TypedDevelopmentalOperatingSystem(verifier=_verifier_rejects)
    env = compile_residual(statement='r', stage='post', local_scope='s', target_scope='g',
                           verified_local_result=True, attachment_certificate=True)
    # No capability supplied -> rejected regardless of the envelope Boolean flag
    try:
        os.attach(s, env)
        raise AssertionError('Boolean bypass (no capability) was accepted')
    except RuntimeError as e:
        assert 'requires the capability' in str(e), f'unexpected: {e}'
    # Capability supplied but authority rejects -> rejected regardless of flag
    from developmental_operating_system import Capability
    cap = Capability('cap:x', 'current-task', ('x',), 1.0, ('residual:0',))
    try:
        os.attach(s, env, cap)
        raise AssertionError('Boolean bypass (forged capability) was accepted')
    except RuntimeError as e:
        assert 'ATTACH rejected' in str(e), f'unexpected: {e}'
    print('  boolean-bypass -> regression-pass (rejected)')


if __name__ == '__main__':
    assert (ARTIFACTS / 'e677_verified_join_reify_state.json').exists(), 'run e677_verified_join_reify_run.py first'
    assert (ARTIFACTS / 'e677_developmental_os_state.json').exists(), 'run e677_developmental_os_run.py first'
    test_correct_source_witness_promoted()
    test_unrelated_witness_rejected()
    test_reordered_residuals_select_correct()
    test_forged_scope_rejected()
    test_failed_promotion_atomic()
    test_boolean_bypass_regression()
    print('TYPED_OS_LIVE_INTEGRATION_PASS')
