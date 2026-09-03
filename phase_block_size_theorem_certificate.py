"""Exact n=7 block-size theorem from the symbolic phase languages.

This certificate deliberately does NOT enumerate partition-derangement states.
It derives the feasible block sizes by local structural arguments, gives explicit
witnesses for every claimed feasible A/B size, imports the independently certified
C component theorem, and then solves only the integer equation a+b+c=7.

At n=7 the phase theorem gives:
  A allowed displacements {-3,-2,-1} = {4,5,6}
  B allowed displacements {+2,-3,-2} = {2,4,5}
  C allowed displacements {+3,-3} = {3,4}

Necessity:
  * Any nonempty block carrying a fixed-point-free permutation has size != 1.
  * A cannot have size 2: a permutation of two points is the transposition, so if
    their displacement is d, both d and -d must be A-allowed.  But
    {4,5,6} intersect {-4,-5,-6} mod 7 = {1,2,3} is empty.
  * C sizes are exactly 0,2,4,6,7 by phase_C_component_theorem_certificate.py.

Sufficiency for A and B is certified by one explicit local witness for every
remaining size.  Therefore:
  A sizes = {0,3,4,5,6,7}
  B sizes = {0,2,3,4,5,6,7}
  C sizes = {0,2,4,6,7}
and the exact feasible ordered size triples are the solutions of a+b+c=7.
"""
from __future__ import annotations

import json
from pathlib import Path

N = 7
ALLOWED = {
    'A': {4,5,6},
    'B': {2,4,5},
    'C': {3,4},
}

# Explicit witnesses: (domain subset, images in the same sorted-domain order).
WITNESSES = {
    'A': {
        0: ((), ()),
        3: ((0,1,4), (4,0,1)),
        4: ((0,1,2,4), (4,0,1,2)),
        5: ((0,1,2,3,4), (4,0,1,2,3)),
        6: ((0,1,2,3,4,5), (4,5,0,1,2,3)),
        7: ((0,1,2,3,4,5,6), (4,0,6,1,2,3,5)),
    },
    'B': {
        0: ((), ()),
        2: ((0,2), (2,0)),
        3: ((0,2,4), (4,0,2)),
        4: ((0,1,2,3), (2,3,0,1)),
        5: ((0,1,2,3,4), (2,3,4,0,1)),
        6: ((0,1,2,3,4,5), (2,3,4,5,1,0)),
        7: ((0,1,2,3,4,5,6), (2,3,4,5,6,0,1)),
    },
}


def check_witness(color: str, domain: tuple[int,...], images: tuple[int,...]) -> bool:
    if len(domain) != len(images) or set(domain) != set(images):
        return False
    return all(x != y and ((y-x) % N) in ALLOWED[color]
               for x,y in zip(domain, images))


def main() -> None:
    # Import only the already-certified C theorem result.  This file does not search
    # C subsets or permutations itself.
    c_path = Path('artifacts/phase_C_component_theorem_certificate.json')
    if not c_path.exists():
        raise RuntimeError('run phase_C_component_theorem_certificate.py first')
    cth = json.loads(c_path.read_text())
    assert cth['all_replays_exact']
    assert cth['n7_feasible_sizes'] == [0,2,4,6,7]

    # Structural A size-2 obstruction.
    a_allowed = ALLOWED['A']
    a_negatives = {(-d) % N for d in a_allowed}
    a_symmetric = a_allowed & a_negatives
    assert not a_symmetric

    witness_checks = {}
    for color in ('A','B'):
        witness_checks[color] = {}
        for size,(domain,images) in WITNESSES[color].items():
            ok = check_witness(color, domain, images)
            assert ok, (color,size,domain,images)
            witness_checks[color][str(size)] = {
                'domain': list(domain),
                'images': list(images),
                'valid': ok,
            }

    symbolic_sizes = {
        'A': [0,3,4,5,6,7],
        'B': [0,2,3,4,5,6,7],
        'C': cth['n7_feasible_sizes'],
    }

    # This is integer arithmetic only: no state, subset, or permutation enumeration.
    triples = [
        [a,b,c]
        for a in symbolic_sizes['A']
        for b in symbolic_sizes['B']
        for c in symbolic_sizes['C']
        if a+b+c == N
    ]

    # Independent comparison to the previous state-enumerating probe is verifier-only.
    blk_path = Path('artifacts/phase_block_feasibility_probe.json')
    if not blk_path.exists():
        raise RuntimeError('run phase_block_feasibility_probe.py first')
    blk = json.loads(blk_path.read_text())
    observed_sizes = {c: blk['local'][c]['feasible_sizes'] for c in ('A','B','C')}
    observed_triples = blk['feasible_ordered_size_triples']
    sizes_exact = symbolic_sizes == observed_sizes
    triples_exact = triples == observed_triples
    assert sizes_exact, (symbolic_sizes, observed_sizes)
    assert triples_exact, (triples, observed_triples)

    theorem = (
        'At n=7 under the saturated symbolic phase language, A-block sizes are exactly '
        '{0,3,4,5,6,7}, B-block sizes exactly {0,2,3,4,5,6,7}, and C-block sizes '
        'exactly {0,2,4,6,7}. Consequently the feasible ordered size triples are exactly '
        'the 11 solutions of a+b+c=7 drawn from those three sets.'
    )
    causal_core = {
        'fixed_point_free': 'excludes size 1 for every nonempty color block',
        'A_orientation_asymmetry': (
            'size 2 would force a transposition and hence both d and -d allowed; '
            'A allowed {4,5,6} has empty intersection with its negative {1,2,3}'
        ),
        'B_size2_witness': '0<->2 uses displacements +2 and -2=5, both B-allowed',
        'C_component_theorem': cth['n7_corollary'],
        'partition_equation': '|A|+|B|+|C|=7',
    }
    out = {
        'theorem': theorem,
        'symbolic_feasible_sizes': symbolic_sizes,
        'symbolic_feasible_ordered_size_triples': triples,
        'symbolic_feasible_ordered_size_triple_count': len(triples),
        'causal_core': causal_core,
        'A_allowed_intersection_negative': sorted(a_symmetric),
        'explicit_AB_sufficiency_witnesses': witness_checks,
        'independent_state_probe_sizes_exact': sizes_exact,
        'independent_state_probe_triples_exact': triples_exact,
        'observed_frontier_state_count': blk['legal_partition_derangement_states'],
        'state_enumeration_used_to_derive_theorem': False,
        'residual': (
            'The 11 size triples are now explained without state enumeration. '
            'Lift the local component/matching method from sizes to exact counts: derive '
            'the 141 shifted states as a symbolic sum over the 11 triples, identifying '
            'which A/B subset languages still require a counting lemma.'
        ),
    }
    assert len(triples) == 11
    assert blk['legal_partition_derangement_states'] == 141
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_block_size_theorem_certificate.json').write_text(
        json.dumps(out, indent=2, sort_keys=True) + '\n'
    )
    print(json.dumps({
        'theorem': theorem,
        'symbolic_feasible_sizes': symbolic_sizes,
        'symbolic_feasible_ordered_size_triples': triples,
        'triple_count': len(triples),
        'sizes_exact': sizes_exact,
        'triples_exact': triples_exact,
        'state_enumeration_used_to_derive_theorem': False,
        'residual': out['residual'],
    }, indent=2, sort_keys=True))
    print('PHASE_BLOCK_SIZE_THEOREM_CERTIFICATE_PASS')


if __name__ == '__main__':
    main()
