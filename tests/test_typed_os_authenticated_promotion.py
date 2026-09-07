"""Authenticated promotion transition tests through the real typed OS.

Exercises TypedDevelopmentalOperatingSystem.promote_global / attach /
invariant_guard with evidence COMPUTED from the frozen verifier and the actual
retained state.  Rejects forged, missing, failed, scope-widening, unattached,
and preservation-breaking evidence, and proves the previous Boolean-flag bypass
no longer works.
"""
from developmental_operating_system import DevelopmentalOSState, LockState, Capability
from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
from typed_residual_protocol import compile_residual


def mk_state():
    lock = LockState(
        problem='swap residual', representation='live',
        installed_capabilities=(), discovery_policy='verified-residual',
        verifier='frozen-external-verifier',
        budget={'search_steps': 20.0, 'model_calls': 10.0},
    )
    return DevelopmentalOSState(
        target='separate the swap witness', residual='initial', lock=lock,
    )


def mk_envelope(cert=True):
    return compile_residual(
        statement='separate the swap witness (f x y) vs (f y x)',
        stage='post-local-proof', local_scope='swap-subsystem',
        target_scope='global', verified_local_result=True,
        attachment_certificate=cert,
        evidence_ids=('residual-envelope:0',),
        metadata={},
    )


def mk_bind_capability(scope='swap-subsystem', provenance=('residual-envelope:0',)):
    return Capability(
        id='cap:bind', scope=scope, activation=('bind',), cost=1.0,
        provenance=provenance,
    )


# Frozen authorities: the OS invokes these; the caller cannot inject a bool.
def authority_accepts_bind(state, capability):
    return capability.id == 'cap:bind'


def authority_rejects_all(state, capability):
    return False


def install_and_verify(os, s, cap, cert=False):
    s.installed_capabilities.append(cap)
    os.install_residual_envelope(s, mk_envelope(cert))


def expect_rejected(fn, needle):
    try:
        fn()
    except RuntimeError as e:
        assert needle in str(e), f'expected {needle!r} in {e!r}'
        return
    raise AssertionError(f'expected rejection containing {needle!r}')


def test_success():
    os = TypedDevelopmentalOperatingSystem(verifier=authority_accepts_bind)
    s = mk_state()
    install_and_verify(os, s, mk_bind_capability())
    assert os.promote_global(s, 'cap:bind') == 'cap:bind'
    print('  success -> promoted')


def test_verdict_failed():
    os = TypedDevelopmentalOperatingSystem(verifier=authority_rejects_all)
    s = mk_state()
    install_and_verify(os, s, mk_bind_capability())
    expect_rejected(lambda: os.promote_global(s, 'cap:bind'), 'passed=False')
    print('  failed-verdict -> rejected')


def test_missing_authority():
    os = TypedDevelopmentalOperatingSystem(verifier=None)
    s = mk_state()
    install_and_verify(os, s, mk_bind_capability())
    expect_rejected(lambda: os.promote_global(s, 'cap:bind'), 'passed=False')
    print('  missing-authority -> rejected')


def test_scope_widening():
    os = TypedDevelopmentalOperatingSystem(verifier=authority_accepts_bind)
    s = mk_state()
    install_and_verify(os, s, mk_bind_capability(scope='swap-subsystem'))
    expect_rejected(
        lambda: os.promote_global(s, 'cap:bind', promoted_scope='global'),
        'scope_ok=False')
    print('  scope-widening -> rejected')


def test_unattached():
    os = TypedDevelopmentalOperatingSystem(verifier=authority_accepts_bind)
    s = mk_state()
    install_and_verify(os, s, mk_bind_capability(provenance=()))
    expect_rejected(lambda: os.promote_global(s, 'cap:bind'), 'attached=False')
    print('  unattached -> rejected')


def test_preservation_break():
    os = TypedDevelopmentalOperatingSystem(verifier=authority_accepts_bind)
    s = mk_state()
    keep = Capability('cap:keep', 'swap-subsystem', ('keep',), 1.0, ())
    install_and_verify(os, s, keep, cert=False)          # keep retained at install
    s.installed_capabilities.append(mk_bind_capability())  # bind added after
    # Now break preservation: drop the prior capability.
    s.installed_capabilities = [c for c in s.installed_capabilities if c.id != 'cap:keep']
    expect_rejected(lambda: os.promote_global(s, 'cap:bind'), 'preserves=False')
    print('  preservation-break -> rejected')


def test_boolean_bypass_regression():
    # Old path: os.attach(s, envelope(True)) unblocked global promotion merely
    # because the envelope carried attachment_certificate=True.  That must no
    # longer work: attach now requires a capability verified by the authority.
    os = TypedDevelopmentalOperatingSystem(verifier=authority_rejects_all)
    s = mk_state()
    os.install_residual_envelope(s, mk_envelope(False))
    expect_rejected(
        lambda: os.attach(s, mk_envelope(True)),          # no capability
        'requires the capability being attached')
    expect_rejected(
        lambda: os.attach(s, mk_envelope(True), mk_bind_capability()),  # authority rejects
        'ATTACH rejected')
    assert not os.can_promote_globally()
    print('  boolean-bypass -> regression-pass (rejected)')


if __name__ == '__main__':
    test_success()
    test_verdict_failed()
    test_missing_authority()
    test_scope_widening()
    test_unattached()
    test_preservation_break()
    test_boolean_bypass_regression()
    print('TYPED_OS_AUTHENTICATED_PROMOTION_PASS')
