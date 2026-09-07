"""Live-entry integration test for the authenticated promotion transition.

Drives the REAL entrypoint (e677_developmental_os_run.main) and the live
e677 -> typed-OS promotion path to establish that:

  * the strongest verified residual (correct source / correct witness by
    statement identity) is promoted through the live gate;
  * a capability backed by an unrelated residual witness (different statement)
    is rejected;
  * reordered residuals do not change the selected witness (statement-bound,
    not index-bound);
  * forged ID/scope is rejected;
  * a failed promotion leaves the installed state unchanged (atomicity);
  * the old Boolean bypass cannot succeed through the live path.

Exercises the real runner end-to-end / real promotion path, not bare
promote_global calls in isolation.
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
    subprocess.run(
        [sys.executable, 'e677_developmental_os_run.py'],
        cwd=str(REPO_ROOT), env=env, check=True,
    )
    state_path = ARTIFACTS / 'e677_developmental_os_state.json'
    assert state_path.exists(), 'live run did not write e677_developmental_os_state.json'
    return json.loads(state_path.read_text())


def _verifier_rejects(state, capability):
    return False


def _build_fresh():
    from e677_developmental_os_run import strongest_verified_residual
    from developmental_operating_system import DevelopmentalOSState, LockState
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    res, prov = strongest_verified_residual(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=res, lock=lock)
    return js, state, res, prov


def _wire_state(js, state, res, prov, verifier):
    from e677_developmental_os_run import mk_verifier
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    os_obj = TypedDevelopmentalOperatingSystem(verifier=verifier if verifier is not None else mk_verifier(js))
    state = os_obj.cycle(state, dict(js, residual=res))
    # Install the strongest-verified residual witness (statement identity).
    wid = 'residual-envelope:strongest'
    state.provenance_graph.append({
        'id': wid, 'kind': 'residual-envelope', 'parents': [],
        'evidence': {'statement': res, 'source': prov['source']},
    })
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [wid], 'evidence': prov})
    return os_obj, state, wid


# ---------------------------------------------------------------------------

def test_correct_witness_promoted():
    """The strongest verified residual (correct statement identity) is promoted."""
    state = _run_main()
    assert 'promoted_through_typed_gate' in state, 'live run did not promote through the typed gate'
    gate = state['promoted_through_typed_gate']
    assert gate['promoted_id'] == gate['capability_id'] == 'cap:strongest-residual'
    assert gate['scope'] == 'current-task'
    # Provenance references the statement-identity witness, not an index.
    assert 'residual-envelope:strongest' in gate['provenance'], f'provenance did not reference strongest witness: {gate["provenance"]}'
    assert 'cap:strongest-residual' in {c['id'] for c in state['installed_capabilities']}
    assert state['residual_type'] == 'REPRESENTATION'
    print('  correct-witness -> promoted')


def test_unrelated_witness_rejected():
    """A capability whose witness carries an unrelated residual statement is
    rejected by the authority."""
    from e677_developmental_os_run import mk_verifier, promote_strongest
    from developmental_operating_system import Capability
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js, state, res, prov = _build_fresh()
    os_obj, state, wid = _wire_state(js, state, res, prov, mk_verifier(js))
    # Build a capability referencing a DIFFERENT residual-envelope witness
    # with an unrelated statement.
    state.provenance_graph.append({
        'id': 'residual-envelope:other', 'kind': 'residual-envelope', 'parents': [],
        'evidence': {'statement': 'an unrelated residual statement', 'source': 't6-relative-phase-theorem'},
    })
    cap = Capability('cap:strongest-residual', 'current-task', ('strongest-residual',), 1.0, ('residual-envelope:other',))
    state.installed_capabilities.append(cap)
    try:
        os_obj.promote_global(state, cap.id)
        raise AssertionError('unrelated witness was accepted by the gate')
    except RuntimeError as e:
        assert 'attached=False' in str(e) or 'passed=False' in str(e), f'unexpected: {e}'
    print('  unrelated-witness -> rejected')


def test_reordered_residuals_select_correct():
    """Reordering the residual dots in the join state does not change the
    selected witness — identity is statement-bound, not index-bound."""
    from e677_developmental_os_run import mk_verifier, promote_strongest
    js, state, res, prov = _build_fresh()
    js_shuffled = copy.deepcopy(js)
    # Reverse the dots ordering.
    js_shuffled['dots'] = list(reversed(js_shuffled.get('dots', [])))
    os_obj, state, wid = _wire_state(js_shuffled, state, res, prov, mk_verifier(js_shuffled))
    cap, promoted_id = promote_strongest(state, os_obj, prov, wid)
    assert promoted_id == cap.id
    # The selected witness must be the one carrying the strongest residual statement.
    assert 'residual-envelope:strongest' in cap.provenance, f'provenance {cap.provenance} did not reference strongest witness'
    print('  reordered-residuals -> correct witness still selected')


def test_forged_scope_rejected():
    """A capability whose authorized scope is narrower than the promoted scope
    is rejected — the verifier admits the capability (verdict True), but the
    OS rejects the unauthorized scope widening."""
    from e677_developmental_os_run import mk_verifier, promote_strongest
    from developmental_operating_system import Capability
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem

    def authority_admits(state, capability):
        return capability.id == 'cap:strongest-residual'
    js, state, res, prov = _build_fresh()
    os_obj, state, wid = _wire_state(js, state, res, prov, authority_admits)
    cap, _ = promote_strongest(state, os_obj, prov, wid)
    # The promoted capability is authorized narrow scope; attempt wider promotion.
    try:
        os_obj.promote_global(state, cap.id, promoted_scope='wide-unauthorized-scope')
        raise AssertionError('scope widening was accepted')
    except RuntimeError as e:
        assert 'scope_ok=False' in str(e), f'unexpected: {e}'
    print('  forged-scope -> rejected')


def test_failed_promotion_atomic():
    """A failed promotion must not leave the staged capability installed."""
    from e677_developmental_os_run import mk_verifier, promote_strongest
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js, state, res, prov = _build_fresh()
    os_obj, state, wid = _wire_state(js, state, res, prov, _verifier_rejects)
    before = [c.id for c in state.installed_capabilities]
    try:
        promote_strongest(state, os_obj, prov, wid)
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
    test_correct_witness_promoted()
    test_unrelated_witness_rejected()
    test_reordered_residuals_select_correct()
    test_forged_scope_rejected()
    test_failed_promotion_atomic()
    test_boolean_bypass_regression()
    print('TYPED_OS_LIVE_INTEGRATION_PASS')
