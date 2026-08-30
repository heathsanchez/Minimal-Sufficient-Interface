#!/usr/bin/env python3
"""V16: does the SAME residual law both force change and recognize arrival?

This is a deliberately narrow ablation of V15.  The controller is not given an
oracle target partition, target class count, minimum basis, target depth, or final
state.  It repeatedly applies the already-frozen developmental operator D.  The
same predicate used on every step decides between:

    positive residual gain -> verify, retain, promote, CHANGE
    zero residual gain     -> return the exact same state, STAY

Only *after* the controller has stopped do we instantiate the independent exhaustive
oracle.  The post-hoc oracle therefore cannot be a stopping criterion.

Scientific question
-------------------
Can the law that necessitates becoming also recognize being, operationally: reach a
state S* without a target-state oracle, then return exact identity D(S*) = S*, with
independent exhaustive enumeration confirming that S* is the oracle-minimal
consequential closure?  A lesion must reactivate the same D and recover the same
observable closure, after which D must again return identity.

Boundary: finite verifier-governed consequence systems with a supplied generic
continuation substrate.  This is not a claim of universal self-certification.
"""
import hashlib
import json

from being_becoming_fixed_point_v15 import (
    D, initial_state, quotient, remove_one_essential, run_steps
)
from recursive_selected_consequence_language_fixed_point_v14 import (
    WORLDS, canonical_partition, residual_gain, oracle
)


def sig(c):
    return (c['name'], repr(c['ast']), tuple(c['vector']), c['depth'])


def state_payload(state):
    return {
        'retained': [sig(c) for c in state['retained']],
        'available': [sig(c) for c in state['available']],
        'queried': sorted((name, repr(ast)) for name, ast in state['queried']),
    }


def state_hash(state):
    raw = json.dumps(state_payload(state), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


def run_self_recognizing(world, start, max_steps=16):
    """Apply only D until D itself returns the unchanged object.

    No oracle information is accepted by this function.  For every changing step we
    record exact before/after hashes and require a positive *verified* residual.
    """
    state = start
    trace = []
    verifier_queries = 0
    for _ in range(max_steps):
        before = state_hash(state)
        ns, ev = D(world, state)
        after = state_hash(ns)
        if ev[0] == 'FIXED':
            assert ns is state
            assert before == after
            trace.append((ev, before, after))
            return state, tuple(trace), verifier_queries

        assert ev[0] == 'STEP'
        assert ev[1] > 0, ev
        assert ev[4] is True, ('changing residual was not externally verified', ev)
        verifier_queries += 1
        assert ns is not state
        assert before != after
        trace.append((ev, before, after))
        state = ns
    raise AssertionError('D did not self-recognize closure within finite safety bound')


def reachable_zero_residual_certificate(state):
    """Post-terminal certificate over the currently reachable consequence language."""
    q = quotient(state)
    gains = [(c['name'], residual_gain(q, c['vector'])) for c in state['available']]
    positive = [(name, gain) for name, gain in gains if gain > 0]
    return len(gains), positive


def reapply_identity(world, star, repeats=5):
    """Repeatedly apply the SAME D; exact serialized state and query set must not move."""
    base_hash = state_hash(star)
    base_queried = set(star['queried'])
    state = star
    events = []
    for _ in range(repeats):
        ns, ev = D(world, state)
        events.append(ev)
        assert ev[0] == 'FIXED'
        assert ns is state
        assert state_hash(ns) == base_hash
        assert ns['queried'] == base_queried
        state = ns
    return tuple(events)


def main():
    world_results = []

    for world in WORLDS:
        # ---- CONTROLLER PHASE ----
        # Crucially, oracle(...) has not been called.  The state contains no target.
        s0 = initial_state(world)
        assert set(s0) == {'retained', 'available', 'queried'}
        star, trace, query_count = run_self_recognizing(world, s0)
        qstar = quotient(star)

        # The same D must recognize arrival repeatedly, not just once accidentally.
        identity_events = reapply_identity(world, star, repeats=5)

        # A post-terminal certificate over what is currently reachable.  This uses
        # the same mathematical residual measure but is not fed back to the controller.
        reachable_count, positive_after = reachable_zero_residual_certificate(star)
        assert positive_after == []

        # ---- POST-HOC ORACLE PHASE ----
        # Only now independently exhaust the supplied finite continuation closure.
        target, oracle_min, _, closure_syntax, closure_behaviors = oracle(world)
        exact_oracle = qstar == target
        minimal_basis = len(star['retained']) == oracle_min

        assert exact_oracle
        assert minimal_basis
        assert query_count == oracle_min

        # Lesion one essential retained distinction while preserving reachable L.
        # No target information is supplied during repair.
        lesion = remove_one_essential(star)
        qlesion = quotient(lesion)
        assert len(qlesion) < len(qstar)
        repaired, repair_trace, repair_queries = run_self_recognizing(world, lesion)
        qrepair = quotient(repaired)
        assert qrepair == qstar == target
        assert repair_trace[0][0][0] == 'STEP'
        assert repair_trace[0][0][1] > 0
        assert repair_trace[0][0][4] is True
        repair_identity_events = reapply_identity(world, repaired, repeats=3)

        # Matched-budget controls.  As in V15 these controls can have their own
        # operator-relative fixed points; the claim is only that they miss the
        # independently established oracle closure under the same query budget.
        no_prom, no_prom_trace = run_steps(
            world, initial_state(world), oracle_min, promote=False)
        static, static_trace = run_steps(
            world, initial_state(world), oracle_min, static_score=True)
        assert quotient(no_prom) != target
        assert quotient(static) != target

        changing = [row for row in trace if row[0][0] == 'STEP']
        fixed = [row for row in trace if row[0][0] == 'FIXED']
        assert len(changing) == oracle_min
        assert len(fixed) == 1
        assert all(row[0][1] > 0 and row[0][4] is True for row in changing)
        assert fixed[0][1] == fixed[0][2]

        print('V16_WORLD', world['name'])
        print('V16_CONTROLLER_STATE_FIELDS', sorted(s0.keys()), 'TARGET_FIELDS', 0)
        print('V16_CONTROLLER_TRACE', tuple(row[0] for row in trace))
        print('V16_CONTROLLER_QUERIES', query_count,
              'STAR_CLASSES', len(qstar), 'RETAINED', len(star['retained']))
        print('V16_REAPPLY_IDENTITY', identity_events)
        print('V16_REACHABLE_CERTIFICATE', 'CANDIDATES', reachable_count,
              'POSITIVE_RESIDUALS', len(positive_after))
        print('V16_POSTHOC_ORACLE', 'CLASSES', len(target), 'MIN_BASIS', oracle_min,
              'CLOSURE_SYNTAX', closure_syntax, 'CLOSURE_BEHAVIORS', closure_behaviors,
              'EXACT', exact_oracle, 'MINIMAL', minimal_basis)
        print('V16_LESION', 'CLASSES', len(qlesion), 'REPAIR_QUERIES', repair_queries,
              'REPAIR_TRACE', tuple(row[0] for row in repair_trace),
              'RESTORED', qrepair == target, 'REIDENTITY', repair_identity_events)
        print('V16_CONTROLS', 'NO_PROM_CLASSES', len(quotient(no_prom)),
              'STATIC_CLASSES', len(quotient(static)),
              'NO_PROM_TRACE', no_prom_trace, 'STATIC_TRACE', static_trace)

        world_results.append({
            'world': world['name'], 'oracle_min': oracle_min,
            'query_count': query_count, 'star_classes': len(qstar),
            'oracle_classes': len(target), 'reachable_positive': len(positive_after),
            'exact': exact_oracle, 'minimal': minimal_basis,
            'lesion_restored': qrepair == target,
        })

    assert len(world_results) == 3
    assert all(r['exact'] and r['minimal'] and r['lesion_restored'] for r in world_results)

    print('SAME_RESIDUAL_PREDICATE_DECIDES_CHANGE_AND_STAY=PASS')
    print('POSITIVE_VERIFIED_RESIDUAL_FORCES_STRICT_STATE_CHANGE=PASS')
    print('ZERO_RESIDUAL_RETURNS_EXACT_IDENTITY_TRANSITION=PASS')
    print('NO_TARGET_STATE_VISIBLE_TO_CONTROLLER=PASS')
    print('POSTHOC_ORACLE_NOT_USED_FOR_STOPPING=PASS')
    print('POSTHOC_REACHABLE_CLOSURE_CERTIFICATE_ZERO_POSITIVE_RESIDUALS=PASS')
    print('POSTHOC_ORACLE_EXACT=PASS')
    print('POSTHOC_ORACLE_MINIMAL=PASS')
    print('REAPPLY_D_EXACT_STATE_IDENTITY_5X=PASS')
    print('REAPPLY_D_NO_NEW_VERIFIER_QUERIES_OR_PROMOTIONS=PASS')
    print('LESION_REACTIVATES_SAME_OPERATOR=PASS')
    print('LESION_REPAIRS_TO_SAME_OBSERVABLE_FIXED_POINT=PASS')
    print('LESION_REACHIEVES_EXACT_IDENTITY=PASS')
    print('NO_PROMOTION_ABLATION_MISSES_ORACLE=PASS')
    print('NO_RESIDUAL_UPDATE_ABLATION_MISSES_ORACLE=PASS')
    print('SOURCE_DISTINCT_TRANSFER_3_OF_3=PASS')
    print('SELF_RECOGNIZING_CLOSURE_V16=PASS')
    print('BOUNDARY=finite verifier-governed consequence systems; supplied generic continuation substrate; oracle is post-hoc only')


if __name__ == '__main__':
    main()
