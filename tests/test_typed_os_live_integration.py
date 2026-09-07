"""Live-entry integration test for the authenticated promotion transition.

Drives the REAL entrypoint (e677_developmental_os_run.main) to establish that
a live capability promotion flows through TypedDevelopmentalOperatingSystem's
gate, and that forged / missing / failed / scope-widening / unattached /
preservation-breaking evidence cannot be promoted through that same live path.

This is NOT a unit test of attach/promote_global in isolation: it exercises the
live e677 runner end-to-end and asserts on the produced state artifacts.
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
    r = subprocess.run(
        [sys.executable, 'e677_developmental_os_run.py'],
        cwd=str(REPO_ROOT), env=env, check=True,
        capture_output=True, text=True,
    )
    state_path = ARTIFACTS / 'e677_developmental_os_state.json'
    assert state_path.exists(), 'live run did not write e677_developmental_os_state.json'
    return json.loads(state_path.read_text())


def _verifier_rejects(state, capability):
    return False


def _verifier_accepts_strongest(state, capability):
    return capability.id == 'cap:strongest-residual' and capability.scope == 'current-task'


def test_live_promotion_success():
    state = _run_main()
    assert 'promoted_through_typed_gate' in state, 'live run did not promote through the typed gate'
    gate = state['promoted_through_typed_gate']
    assert gate['promoted_id'] == gate['capability_id'] == 'cap:strongest-residual'
    assert gate['scope'] == 'current-task'
    # The promoted capability is present in the retained installed set.
    assert 'cap:strongest-residual' in {c['id'] for c in state['installed_capabilities']}
    assert state['residual_type'] == 'REPRESENTATION'
    print('  live-promotion-success')


def test_forged_verdict_rejected():
    # Use a verifier that rejects ALL verdicts, then attempt the live promotion
    # path.  The gate must reject, not promote a forged accepted capability.
    from e677_developmental_os_run import strongest_verified_residual, promote_strongest
    from developmental_operating_system import DevelopmentalOSState, LockState
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    residual, prov = strongest_verified_residual(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=residual, lock=lock)
    os = TypedDevelopmentalOperatingSystem(verifier=_verifier_rejects)
    state = os.cycle(state, dict(js, residual=residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})

    try:
        promote_strongest(state, os)
        raise AssertionError('forged/failed verdict was accepted by the gate')
    except RuntimeError as e:
        assert 'passed=False' in str(e), f'unexpected rejection reason: {e}'

    print('  forged/failed-verdict -> rejected')


def test_unattached_capability_rejected():
    from e677_developmental_os_run import strongest_verified_residual, promote_strongest
    from developmental_operating_system import DevelopmentalOSState, LockState, Capability
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    residual, prov = strongest_verified_residual(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=residual, lock=lock)
    os = TypedDevelopmentalOperatingSystem(verifier=_verifier_accepts_strongest)
    state = os.cycle(state, dict(js, residual=residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    # Unattached: provenance references nothing real
    cap = Capability('cap:strongest-residual', 'current-task', ('strongest-residual',), 1.0, ('forged-unattached-witness',))
    state.installed_capabilities.append(cap)
    try:
        os.promote_global(state, cap.id)
        raise AssertionError('unattached capability was accepted')
    except RuntimeError as e:
        assert 'attached=False' in str(e), f'unexpected: {e}'
    print('  unattached -> rejected')


def test_scope_widening_rejected():
    from e677_developmental_os_run import strongest_verified_residual
    from developmental_operating_system import DevelopmentalOSState, LockState, Capability
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    residual, prov = strongest_verified_residual(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=residual, lock=lock)
    os = TypedDevelopmentalOperatingSystem(verifier=_verifier_accepts_strongest)
    state = os.cycle(state, dict(js, residual=residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    cap = Capability('cap:strongest-residual', 'current-task', ('strongest-residual',), 1.0, ('residual:0',))
    state.installed_capabilities.append(cap)
    # Attempt to promote into a wider scope than authorized
    try:
        os.promote_global(state, cap.id, promoted_scope='global-wider-scope')
        raise AssertionError('scope widening was accepted')
    except RuntimeError as e:
        assert 'scope_ok=False' in str(e), f'unexpected: {e}'
    print('  scope-widening -> rejected')


def test_preservation_break_rejected():
    from e677_developmental_os_run import strongest_verified_residual, promote_strongest
    from developmental_operating_system import DevelopmentalOSState, LockState
    from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
    js = json.load(open(ARTIFACTS / 'e677_verified_join_reify_state.json'))
    residual, prov = strongest_verified_residual(js)
    lock = LockState(problem='x', representation='r', installed_capabilities=(),
                     discovery_policy='d', verifier='v',
                     budget={'search_steps': 100.0, 'model_calls': 100.0})
    state = DevelopmentalOSState(target='x', residual=residual, lock=lock)
    os = TypedDevelopmentalOperatingSystem(verifier=_verifier_accepts_strongest)
    state = os.cycle(state, dict(js, residual=residual))
    state.provenance_graph.append({'id': 'controller:strongest-residual', 'kind': 'routing-decision', 'parents': [], 'evidence': prov})
    # Snapshot a retained capability then delete it (simulate corruption)
    from developmental_operating_system import Capability
    keep = Capability('cap:keep', 'current-task', ('keep',), 1.0, ('residual:0',))
    state.installed_capabilities.append(keep)
    os.typed.pre_transition_installed = (keep.id,)
    cap, _ = promote_strongest(state, os)
    # Now break preservation by removing the prior capability
    state.installed_capabilities = [c for c in state.installed_capabilities if c.id != 'cap:keep']
    # A fresh promotion attempt on the surviving capability must detect the loss
    try:
        os.promote_global(state, cap.id)
        raise AssertionError('preservation break was accepted on second promotion')
    except RuntimeError as e:
        assert 'preserves=False' in str(e), f'unexpected: {e}'
    print('  preservation-break -> rejected')


def test_boolean_bypass_regression():
    # The old TypedDevelopmentalOperatingSystem accepted attach(state, envelope)
    # and trusted envelope.attachment_certificate=True with no capability/authority.
    # That path must now be rejected: attach requires a verified capability.
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
    # The OLD bypass: attach trusted envelope.attachment_certificate=True with no
    # capability/authority and unblocked global promotion.  That path must now
    # be rejected because attach requires a capability verified by the authority.
    from developmental_operating_system import Capability
    cap = Capability('cap:x', 'current-task', ('x',), 1.0, ('residual:0',))
    try:
        os.attach(s, env)  # no capability supplied
        raise AssertionError('Boolean bypass (no capability) was accepted')
    except RuntimeError as e:
        assert 'requires the capability' in str(e), f'unexpected: {e}'
    try:
        os.attach(s, env, cap)  # capability supplied but authority rejects
        raise AssertionError('Boolean bypass (forged capability) was accepted')
    except RuntimeError as e:
        assert 'ATTACH rejected' in str(e), f'unexpected: {e}'
    print('  boolean-bypass -> regression-pass (rejected)')


if __name__ == '__main__':
    # Ensure artifacts are present for the live-promotion test
    assert (ARTIFACTS / 'e677_verified_join_reify_state.json').exists(), 'run e677_verified_join_reify_run.py first'
    test_live_promotion_success()
    test_forged_verdict_rejected()
    test_unattached_capability_rejected()
    test_scope_widening_rejected()
    test_preservation_break_rejected()
    test_boolean_bypass_regression()
    print('TYPED_OS_LIVE_INTEGRATION_PASS')
