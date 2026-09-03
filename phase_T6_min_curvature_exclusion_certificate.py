"""Certify that the n=7 phase frontier excludes the entire kappa(D)=18 nonlinear layer.

Upstream facts being attached (Grisha-Pochuev/finite-magma-e677-to-e255):
  1. T6 PAIR-KERNEL is exactly
       U_t^-1(s)=U_u^-1(s) iff
       D(U_t(s)-t)-A(U_t(s)) = D(U_u(s)-u)-A(U_u(s)).
     The upstream pair-clique implementation computes x=(U-t)%7,
     rho=D[x]-A[U], and tests inverse_equal == rho_equal pointwise.
  2. The complete nonlinear minimum-curvature layer is kappa(D)=18 with 294 maps.
     Gauge + scalar conjugacy reduce that layer losslessly to exactly four D maps:
       0125634, 0145236, 1023546, 1024356.

Our independently gated four-row attachment exhausts all 141 phase states, all
720 normalized A fixing zero, and those four canonical D maps, and finds zero
PAIR-KERNEL witnesses.  Since every full seven-row T6 core must satisfy every
four-row projection, no completion in the kappa=18 layer exists.

Scope: this excludes kappa=18 only.  It does not claim E677->E255 is solved and
does not infer what the next attainable curvature value is.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from partition_derangement_probe import enumerate_states, shifted_ok
from phase_T6_four_row_attachment_probe import pair_kernel_ok, inverse, CANONICAL_D, A_FIX0

N=7
PAIRS=tuple(itertools.combinations(range(4),2))
EXPECTED_D={
    '0125634': (0,1,2,5,6,3,4),
    '0145236': (0,1,4,5,2,3,6),
    '1023546': (1,0,2,3,5,4,6),
    '1024356': (1,0,2,4,3,5,6),
}


def upstream_style_pair_kernel(rows,A,D):
    """Literal scalar transcription of upstream CliqueSearch.compatible kernel test."""
    inverses=tuple(inverse(r) for r in rows)
    for t,u in PAIRS:
        rho_t=tuple((D[(rows[t][s]-t)%N]-A[rows[t][s]])%N for s in range(N))
        rho_u=tuple((D[(rows[u][s]-u)%N]-A[rows[u][s]])%N for s in range(N))
        inverse_equal=tuple(inverses[t][s]==inverses[u][s] for s in range(N))
        rho_equal=tuple(rho_t[s]==rho_u[s] for s in range(N))
        if inverse_equal != rho_equal:
            return False
    return True


def main():
    assert CANONICAL_D == EXPECTED_D
    assert len(A_FIX0)==720

    attachment=json.loads(Path('artifacts/phase_T6_four_row_attachment_probe.json').read_text())
    assert attachment['baseline_phase_states']==141
    assert attachment['surviving_phase_states']==0
    assert attachment['rejected_phase_states']==141
    assert attachment['canonical_D']==list(EXPECTED_D)
    assert attachment['A_domain']=='all 720 permutations of Z7 fixing 0'

    # Independent convention audit.  Compare our predicate with a literal transcription
    # of the upstream implementation on every phase state for deterministic sentinel A's,
    # then on every A,D combination for the first phase state.  This catches index/sign
    # drift without simply calling the same function twice everywhere.
    states=[rows for _,_,rows in enumerate_states() if shifted_ok(rows)]
    assert len(states)==141
    sentinel_A=(A_FIX0[0],A_FIX0[1],A_FIX0[17],A_FIX0[119],A_FIX0[-1])
    comparisons=0
    for rows in states:
        for A in sentinel_A:
            for D in EXPECTED_D.values():
                assert pair_kernel_ok(rows,A,D)==upstream_style_pair_kernel(rows,A,D)
                comparisons += 1
    rows0=states[0]
    for A in A_FIX0:
        for D in EXPECTED_D.values():
            assert pair_kernel_ok(rows0,A,D)==upstream_style_pair_kernel(rows0,A,D)
            comparisons += 1

    out={
        'claim':(
            'Within the normalized cyclic-P T6 setting, no n=7 shifted four-row phase '
            'state extends through PAIR-KERNEL with any minimum-nonlinear-curvature D. '
            'Therefore the complete kappa(D)=18 nonlinear layer is excluded.'
        ),
        'phase_states':141,
        'normalized_A_count':720,
        'canonical_D':list(EXPECTED_D),
        'upstream_minimum_nonlinear_kappa':18,
        'upstream_labelled_maps_at_kappa18':294,
        'canonical_D_complete_symmetry_quotient_of_kappa18':True,
        'four_row_survivors':0,
        'pair_kernel_convention_comparisons':comparisons,
        'pair_kernel_convention_exact':True,
        'full_seven_row_completion_in_kappa18_possible':False,
        'next_curvature_value_claimed':False,
        'e677_implication_solved_claimed':False,
        'residual':(
            'The minimum nonlinear D layer kappa=18 is now excluded. Compute the exact '
            'next attainable nonlinear curvature layer(s), quotient them by the same valid '
            'gauge/symmetries, and test the cheapest four-row PAIR-KERNEL attachment first. '
            'If four-row contraction disappears, move to relative-pair TRIANGLE-COCYCLE '
            'rather than restoring raw seven-row search.'
        ),
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_T6_min_curvature_exclusion_certificate.json').write_text(
        json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'kappa_excluded':18,
        'labelled_maps_covered':294,
        'canonical_D_cases':4,
        'phase_states_killed':141,
        'pair_kernel_convention_comparisons':comparisons,
        'residual':out['residual'],
    },indent=2,sort_keys=True))
    print('PHASE_T6_MIN_CURVATURE_EXCLUSION_CERTIFICATE_PASS')

if __name__=='__main__': main()
