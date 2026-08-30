#!/usr/bin/env python3
"""V16: remove the finite-state boundary from the V15 developmental fixed-point test.

Domain
------
The world is N, not a finite enumerated state set.  Consequence b_k(n) is the k-th
binary digit of n.  The initial language contains b_0.  Verifier-gated promotion of
b_k exposes b_{k+1}.  A developmental state retains verified bit consequences.

For every finite retained prefix {b_0,...,b_{k-1}}, the pair (0, 2^k):
  * agrees on every retained consequence; and
  * differs on b_k.
Thus b_k is an exact residual witness against the current quotient.  After b_k is
verified and retained, the generic successor constructor makes b_{k+1} reachable.
There is therefore no finite terminal fixed point in this infinite domain.

The executable test checks the frozen controller for a long prefix and independently
checks the parametric residual certificate at sparse very large indices.  The latter
does not enumerate a finite world; it directly validates the witness construction.
This is evidence for open-ended continuation, not a machine-checked proof of the
universal statement over all k.
"""

HORIZON = 256
LARGE_INDICES = (0, 1, 2, 7, 31, 63, 127, 255, 511, 1023, 4095)


def bit(n: int, k: int) -> int:
    return (n >> k) & 1


def agrees_on_retained(x: int, y: int, retained: tuple[int, ...]) -> bool:
    return all(bit(x, j) == bit(y, j) for j in retained)


def residual_certificate(k: int, retained: tuple[int, ...]):
    """External exact witness for failure of b_k to descend through current quotient."""
    x, y = 0, 1 << k
    return {
        'k': k,
        'x': x,
        'y': y,
        'same_current_quotient': agrees_on_retained(x, y, retained),
        'new_consequence_separates': bit(x, k) != bit(y, k),
    }


def verifier(k: int, retained: tuple[int, ...]) -> bool:
    cert = residual_certificate(k, retained)
    return cert['same_current_quotient'] and cert['new_consequence_separates']


def initial_state():
    return {'retained': tuple(), 'available': (0,), 'queried': frozenset()}


def D(state, promote=True):
    """One frozen verifier-gated developmental step on the infinite domain N."""
    candidates = sorted(k for k in state['available'] if k not in state['queried'])
    for k in candidates:
        if not verifier(k, state['retained']):
            continue
        retained = state['retained'] + (k,)
        available = list(state['available'])
        if promote and (k + 1) not in available:
            available.append(k + 1)
        ns = {
            'retained': retained,
            'available': tuple(sorted(available)),
            'queried': state['queried'] | {k},
        }
        cert = residual_certificate(k, state['retained'])
        return ns, ('STEP', k, cert['x'], cert['y'], tuple(sorted(available)))
    return state, ('FIXED', len(state['retained']))


def run_prefix(steps: int, promote=True):
    state = initial_state()
    trace = []
    for _ in range(steps):
        ns, ev = D(state, promote=promote)
        trace.append(ev)
        if ns is state:
            return state, tuple(trace), True
        state = ns
    return state, tuple(trace), False


def parametric_witness_check(k: int) -> bool:
    retained = tuple(range(k))
    cert = residual_certificate(k, retained)
    # Independent structural checks: 2^k has no lower set bit and has its k-th bit set.
    lower_mask = (1 << k) - 1
    lower_bits_zero = ((1 << k) & lower_mask) == 0
    kth_bit_one = bit(1 << k, k) == 1
    zero_kth_bit_zero = bit(0, k) == 0
    return (cert['same_current_quotient'] and cert['new_consequence_separates']
            and lower_bits_zero and kth_bit_one and zero_kth_bit_zero)


def main():
    state, trace, fixed = run_prefix(HORIZON, promote=True)
    assert not fixed
    assert state['retained'] == tuple(range(HORIZON))
    assert HORIZON in state['available']

    # The next step must still have a certified residual, exactly where a finite-world
    # closure experiment would have stopped if it had exhausted all distinctions.
    next_cert = residual_certificate(HORIZON, state['retained'])
    assert next_cert['same_current_quotient']
    assert next_cert['new_consequence_separates']
    next_state, next_ev = D(state, promote=True)
    assert next_state is not state and next_ev[0] == 'STEP' and next_ev[1] == HORIZON

    # Sparse checks far beyond the executed developmental prefix ensure the witness
    # construction is not accidentally tied to the chosen horizon.
    large_ok = {k: parametric_witness_check(k) for k in LARGE_INDICES}
    assert all(large_ok.values())

    # Causal ablation: with promotion removed, the exact same controller verifies b_0
    # and then has no reachable new consequence, producing a terminal fixed point.
    no_prom, no_prom_trace, no_prom_fixed = run_prefix(8, promote=False)
    assert no_prom_fixed
    assert no_prom['retained'] == (0,)

    print('V16_DOMAIN=NATURALS_INFINITE')
    print('V16_HORIZON', HORIZON)
    print('V16_RETAINED_PREFIX', len(state['retained']))
    print('V16_FIXED_WITH_PROMOTION', fixed)
    print('V16_NEXT_RESIDUAL_K', HORIZON,
          'SAME_OLD_QUOTIENT', next_cert['same_current_quotient'],
          'SEPARATES', next_cert['new_consequence_separates'])
    print('V16_NEXT_STEP', next_ev)
    print('V16_LARGE_INDEX_CERTIFICATES', large_ok)
    print('V16_NO_PROMOTION_FIXED', no_prom_fixed,
          'RETAINED', no_prom['retained'], 'TRACE', no_prom_trace)
    print('INFINITE_DOMAIN_NO_ENUMERATION=PASS')
    print('VERIFIED_RESIDUAL_EXISTS_AFTER_256_DEVELOPMENTAL_STEPS=PASS')
    print('PARAMETRIC_NEXT_DISTINCTION_WITNESS_CONSTRUCTION=PASS')
    print('PROMOTION_ABLATION_RESTORES_TERMINAL_FIXED_POINT=PASS')
    print('FINITE_FIXED_POINT_DOES_NOT_SURVIVE_REMOVING_FINITE_WORLD=PASS')
    print('OPEN_ENDED_DEVELOPMENT_V16=PASS')
    print('BOUNDARY=execution validates a parametric construction on N and selected large indices; universal nontermination is mathematically transparent but is not yet Lean-machine-checked')


if __name__ == '__main__':
    main()
