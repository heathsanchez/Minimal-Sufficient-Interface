"""Live-entry integration test for the authenticated promotion transition.

The verifier validates the actual certificate contents and returns a stable
result identity = (source, theorem_text).  The capability's witness must
reference the verified-success node carrying that exact identity.

Tests:
  * correct result identity -> promoted
  * altered certificate (different theorem_text) -> rejected
  * wrong-result reference (capability references a different result_identity)
    -> rejected, even if the residual statement matches
  * reordered residuals -> correct witness still selected (identity-bound)
  * forged scope -> rejected
  * failed promotion -> atomic rollback (installed state unchanged)
  * Boolean bypass regression
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
    env = dict(_os.environ)
    env['PYTHONPATH'] = str(REPO_ROOT)
    subprocess.run([sys.executable, 'e677_developmental_os_run.py'], cwd=str(REPO_ROOT), env=env, check=True)
    state_path = ARTIFACTS / 'e677_developmental_os_state.json'
    assert state_path.exists(), 'live run did not write e677_developmental_os_state.json'
    return json.loads(state_path.read_text())


def _verifier_rejects(state, capability):
    return False


def _build_fresh():
    from e677_developmental_os_run import validate_strongest_certificate
    from developmental_operating_system import DevelopmentalOSState, LockState
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    res, prov, rid = validate_strongest_certificate(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=res, lock=lock)
    return js, state, res, prov, rid


def _wire_state(js, state, res, prov, rid, verifier):
    from e677_developmental_os_run import mk_verifier
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    os_obj = TypedDevelopmentalOperatingSystem(verifier=verifier if verifier is not None else mk_verifier(js))
    state = os_obj.cycle(state, dict(js, residual=res))
    wid = 'verified:strongest'
    state.provenance_graph.append({
        'id': wid, 'kind': 'verified-success', 'parents': [],
        'evidence': {'statement': res, 'result_identity': list(rid), 'source': prov['source']},
    })
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [wid], 'evidence': prov})
    return os_obj, state, wid, rid


def test_correct_identity_promoted():
    state = _run_main()
    gate = state['promoted_through_typed_gate']
    assert gate['promoted_id'] == gate['capability_id'] == 'cap:strongest-residual'
    assert gate['scope'] == 'current-task'
    assert 'verified:strongest' in gate['provenance'], f'provenance: {gate["provenance"]}'
    assert 'cap:strongest-residual' in {c['id'] for c in state['installed_capabilities']}
    assert state['residual_type'] == 'REPRESENTATION'
    print('  correct-identity -> promoted')


def test_altered_certificate_rejected():
    """If the authority's certificate contents differ (altered theorem_text),
    the result_identity changes and the witness no longer matches."""
    from e677_developmental_os_run import mk_verifier, promote_strongest
    from developmental_operating_system import Capability
    js, state, res, prov, rid = _build_fresh()
    # Authority built from the REAL certificate.
    os_obj, state, wid, rid_real = _wire_state(js, state, res, prov, rid, mk_verifier(js))
    # But the witness node carries an ALTERED result_identity (different theorem).
    altered_rid = (rid[0], 'an altered theorem text that does not match the certificate')
    state.provenance_graph[-2]['evidence']['result_identity'] = list(altered_rid)
    cap = Capability('cap:strongest-residual', 'current-task', ('strongest-residual',), 1.0, (wid,))
    state.installed_capabilities.append(cap)
    try:
        os_obj.promote_global(state, cap.id)
        raise AssertionError('altered certificate was accepted')
    except RuntimeError as e:
        assert 'passed=False' in str(e), f'unexpected: {e}'
    print('  altered-certificate -> rejected')


def test_wrong_result_reference_rejected():
    """A capability referencing a verified-success witness with a different
    result_identity is rejected, even if the residual statement matches."""
    from e677_developmental_os_run import mk_verifier
    from developmental_operating_system import Capability
    js, state, res, prov, rid = _build_fresh()
    os_obj, state, wid, rid_real = _wire_state(js, state, res, prov, rid, mk_verifier(js))
    # Imposter witness: same statement, DIFFERENT result_identity.
    imposter_rid = ('t6-relative-phase-theorem', 'a different theorem entirely')
    state.provenance_graph.append({
        'id': 'verified:imposter', 'kind': 'verified-success', 'parents': [],
        'evidence': {'statement': res, 'result_identity': list(imposter_rid), 'source': prov['source']},
    })
    cap = Capability('cap:strongest-residual', 'current-task', ('strongest-residual',), 1.0, ('verified:imposter',))
    state.installed_capabilities.append(cap)
    try:
        os_obj.promote_global(state, cap.id)
        raise AssertionError('wrong-result-reference was accepted')
    except RuntimeError as e:
        assert 'passed=False' in str(e), f'unexpected: {e}'
    print('  wrong-result-reference -> rejected')


def test_reordered_residuals_select_correct():
    from e677_developmental_os_run import mk_verifier, promote_strongest
    js, state, res, prov, rid = _build_fresh()
    js_shuffled = copy.deepcopy(js)
    js_shuffled['dots'] = list(reversed(js_shuffled.get('dots', [])))
    os_obj, state, wid, rid_s = _wire_state(js_shuffled, state, res, prov, rid, mk_verifier(js_shuffled))
    cap, promoted_id = promote_strongest(state, os_obj, prov, wid, rid)
    assert promoted_id == cap.id
    assert 'verified:strongest' in cap.provenance, f'provenance {cap.provenance}'
    print('  reordered-residuals -> correct witness still selected')


def test_forged_scope_rejected():
    from e677_developmental_os_run import mk_verifier, promote_strongest

    def authority_admits(state, capability):
        return capability.id == 'cap:strongest-residual'
    js, state, res, prov, rid = _build_fresh()
    os_obj, state, wid, rid_s = _wire_state(js, state, res, prov, rid, authority_admits)
    cap, _ = promote_strongest(state, os_obj, prov, wid, rid)
    try:
        os_obj.promote_global(state, cap.id, promoted_scope='wide-unauthorized-scope')
        raise AssertionError('scope widening was accepted')
    except RuntimeError as e:
        assert 'scope_ok=False' in str(e), f'unexpected: {e}'
    print('  forged-scope -> rejected')


def test_failed_promotion_atomic():
    from e677_developmental_os_run import promote_strongest
    js, state, res, prov, rid = _build_fresh()
    os_obj, state, wid, rid_s = _wire_state(js, state, res, prov, rid, _verifier_rejects)
    before = [c.id for c in state.installed_capabilities]
    try:
        promote_strongest(state, os_obj, prov, wid, rid)
        raise AssertionError('failed verdict was accepted')
    except RuntimeError:
        pass
    after = [c.id for c in state.installed_capabilities]
    assert after == before, f'failed promotion changed installed state: {before} -> {after}'
    print('  failed-promotion -> rejected (installed state unchanged)')


def test_boolean_bypass_regression():
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
    try:
        os.attach(s, env)
        raise AssertionError('Boolean bypass (no capability) was accepted')
    except RuntimeError as e:
        assert 'requires the capability' in str(e), f'unexpected: {e}'
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
    test_correct_identity_promoted()
    test_altered_certificate_rejected()
    test_wrong_result_reference_rejected()
    test_reordered_residuals_select_correct()
    test_forged_scope_rejected()
    test_failed_promotion_atomic()
    test_boolean_bypass_regression()
    print('TYPED_OS_LIVE_INTEGRATION_PASS')
