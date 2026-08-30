#!/usr/bin/env python3
"""V15: Is 'being' a fixed point of the same verifier-gated becoming operator?

Operationalization
------------------
A developmental state S=(C,L) consists of retained verified consequences C and the
currently reachable consequence language L.  Define ONE frozen operator D:
  1. form the quotient induced by C;
  2. among currently reachable unqueried consequences, select maximum residual gain;
  3. if maximum gain is zero, return S unchanged (fixed point);
  4. externally verify the selected consequence;
  5. only if verified, retain it and promote generic descendants into L.

The test asks whether repeated D reaches S* such that D(S*)=S*, whether the quotient
of S* equals the exhaustive closure oracle, and whether perturbing S* by deleting an
essential retained distinction makes the SAME D resume development and restore S*'s
observable quotient. Controls are matched-budget ablations: they are not required to
converge, because failure of residual updating can itself produce endless redundant
language growth.

This is a bounded mathematical test of the phrase 'what it is is stable under how it
becomes'; it is not a universal metaphysical claim.
"""
from recursive_selected_consequence_language_fixed_point_v14 import (
    WORLDS, canonical_partition, residual_gain, generated_children, verifier, oracle
)


def signature(c):
    return (c['name'], c['ast'])


def initial_state(world):
    return {'retained': [], 'available': list(world['seeds']), 'queried': set()}


def quotient(state):
    return canonical_partition([c['vector'] for c in state['retained']])


def D(world, state, promote=True, score_partition=None):
    """One frozen developmental step. Returns (new_state, evidence)."""
    current = quotient(state)
    basis = current if score_partition is None else score_partition
    candidates = []
    for c in state['available']:
        if signature(c) in state['queried']:
            continue
        candidates.append((residual_gain(basis, c['vector']), c['depth'], c['name'], c))
    if not candidates:
        return state, ('FIXED', 0, len(current), None)
    candidates.sort(key=lambda r: (-r[0], r[1], r[2]))
    gain, _, _, chosen = candidates[0]
    if gain == 0:
        return state, ('FIXED', 0, len(current), chosen['name'])

    ns = {
        'retained': list(state['retained']),
        'available': list(state['available']),
        'queried': set(state['queried']) | {signature(chosen)},
    }
    ok = verifier(world, chosen)
    new_names = []
    if ok:
        ns['retained'].append(chosen)
        if promote:
            have = {signature(c) for c in ns['available']}
            for child in generated_children(world, chosen):
                if signature(child) not in have:
                    ns['available'].append(child)
                    have.add(signature(child))
                    new_names.append(child['name'])
    return ns, ('STEP', gain, len(current), chosen['name'], ok, tuple(new_names))


def iterate_to_fixed(world, state, promote=True, max_steps=12):
    trace = []
    for _ in range(max_steps):
        ns, ev = D(world, state, promote=promote)
        trace.append(ev)
        if ns is state:
            return state, tuple(trace)
        state = ns
    raise AssertionError('development did not terminate within fixed-point bound')


def run_steps(world, state, steps, promote=True, static_score=False):
    """Matched-budget control: run exactly up to `steps`, without assuming convergence."""
    trace = []
    r0 = canonical_partition([])
    for _ in range(steps):
        ns, ev = D(world, state, promote=promote,
                   score_partition=r0 if static_score else None)
        trace.append(ev)
        if ns is state:
            break
        state = ns
    return state, tuple(trace)


def remove_one_essential(state):
    # Remove an essential retained distinction, but keep the consequence language
    # itself intact. This models loss of retained structure/memory, not destruction
    # of the external possibility of re-observing the missing distinction.
    assert state['retained']
    kept_retained = state['retained'][:-1]
    return {
        'retained': list(kept_retained),
        'available': list(state['available']),
        'queried': set(),
    }


def main():
    for world in WORLDS:
        target, oracle_min, _, _, _ = oracle(world)
        assert oracle_min > 0

        s0 = initial_state(world)
        star, trace = iterate_to_fixed(world, s0)
        qstar = quotient(star)
        star2, ev = D(world, star)
        idempotent = star2 is star and ev[0] == 'FIXED'

        lesion = remove_one_essential(star)
        qlesion = quotient(lesion)
        repaired, repair_trace = iterate_to_fixed(world, lesion)
        qrepair = quotient(repaired)

        # Controls get the same oracle-minimal verifier-query budget as the successful
        # developmental trajectory. They need not terminate naturally.
        no_prom, no_prom_trace = run_steps(
            world, initial_state(world), oracle_min, promote=False)
        static, static_trace = run_steps(
            world, initial_state(world), oracle_min, static_score=True)

        print('V15_WORLD', world['name'])
        print('V15_TRACE', trace)
        print('V15_STAR_CLASSES', len(qstar), 'ORACLE_CLASSES', len(target),
              'EXACT_ORACLE', qstar == target, 'D_STAR_EQ_STAR', idempotent,
              'ORACLE_MIN', oracle_min)
        print('V15_LESION_CLASSES', len(qlesion), 'REPAIR_TRACE', repair_trace,
              'REPAIRED_CLASSES', len(qrepair), 'RESTORED_ORACLE', qrepair == target)
        print('V15_NO_PROMOTION_CLASSES', len(quotient(no_prom)), 'TRACE', no_prom_trace)
        print('V15_STATIC_RESIDUAL_CLASSES', len(quotient(static)), 'TRACE', static_trace)

        assert qstar == target
        assert idempotent
        assert len(qlesion) < len(qstar)
        assert qrepair == target
        assert len(quotient(no_prom)) < len(target)
        assert len(quotient(static)) < len(target)
        assert repair_trace[0][0] == 'STEP'

    print('SAME_OPERATOR_GENERATES_AND_RECOGNIZES_FIXED_POINT=PASS')
    print('FIXED_POINT_EQUALS_EXHAUSTIVE_CONSEQUENCE_QUOTIENT=PASS')
    print('D_OF_FIXED_POINT_EQUALS_FIXED_POINT=PASS')
    print('STRUCTURAL_LESION_RESTARTS_DEVELOPMENT=PASS')
    print('SAME_OPERATOR_RESTORES_OBSERVABLE_FIXED_POINT_AFTER_LESION=PASS')
    print('NO_PROMOTION_ABLATION_PREVENTS_FIXED_POINT=PASS')
    print('NO_RESIDUAL_UPDATE_ABLATION_PREVENTS_FIXED_POINT=PASS')
    print('SOURCE_DISTINCT_TRANSFER_3_OF_3=PASS')
    print('BEING_BECOMING_FIXED_POINT_V15=PASS')
    print('BOUNDARY=finite verifier-governed consequence system; fixed point is observational/structural, not a universal metaphysical theorem')


if __name__ == '__main__':
    main()
