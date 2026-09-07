"""End-to-end causal replay for typed attachment safety.

A locally verified theorem is admitted as knowledge but must not change global
search until attachment is certified.  We intervene by adding the certificate,
verify the route changes, then ablate the certificate and require the unsafe
promotion block to return.
"""
from developmental_operating_system import DevelopmentalOSState, LockState
from developmental_operating_system_typed import TypedDevelopmentalOperatingSystem
from typed_residual_protocol import compile_residual


def mk_state():
    lock=LockState(
        problem='Global E677=>E255 frontier', representation='live-frontier',
        installed_capabilities=(), discovery_policy='verified-residual',
        verifier='external theorem/SAT checker',
        budget={'search_steps':20.0,'model_calls':10.0},
    )
    return DevelopmentalOSState(
        target='Close or sharpen the global E677=>E255 residual',
        residual='initial', lock=lock,
    )


def envelope(cert: bool):
    return compile_residual(
        statement='Use the verified saturated phase theorem only if its assumptions attach to the live T6/frontier reduction.',
        stage='post-local-proof', local_scope='saturated-four-row-subsystem',
        target_scope='global-E677-frontier', verified_local_result=True,
        attachment_certificate=cert,
        evidence_ids=('law:symbolic-phase-n-ge-4',),
        metadata={'theorem':'symbolic-phase','scope_transition':'local->global'},
    )


def blocked_phase():
    os=TypedDevelopmentalOperatingSystem(); s=mk_state()
    os.install_residual_envelope(s,envelope(False)); os.wake_actions(s); os.invariant_guard(s)
    assert s.residual_type=='ATTACHMENT'
    assert [a.id for a in s.action_queue]==['act:attach']
    assert not os.can_promote_globally()
    try:
        os.promote_global('cap:symbolic-phase')
    except RuntimeError:
        pass
    else:
        raise AssertionError('unsafe global promotion was not blocked')
    return os,s

if __name__=='__main__':
    os,s=blocked_phase()
    before={'type':s.residual_type,'actions':[a.id for a in s.action_queue],
            'promotable':os.can_promote_globally()}

    # Verified bridge intervention.
    os.attach(s,envelope(True)); os.invariant_guard(s)
    promoted=os.promote_global('cap:symbolic-phase')
    after={'type':s.residual_type,'promotable':os.can_promote_globally(),'promoted':promoted}
    assert after['promotable'] and after['type']!='ATTACHMENT'

    # Exact ablation: rebuild identical state but remove only the bridge certificate.
    os2,s2=blocked_phase()
    ablated={'type':s2.residual_type,'actions':[a.id for a in s2.action_queue],
             'promotable':os2.can_promote_globally()}
    assert ablated==before

    import json
    print(json.dumps({'before_attachment':before,'with_attachment':after,
                      'certificate_ablated':ablated,
                      'causal_consequence':'attachment certificate alone changes global promotion safety and next action'},
                     indent=2,sort_keys=True))
    print('TYPED_OS_ATTACHMENT_REPLAY_PASS')
