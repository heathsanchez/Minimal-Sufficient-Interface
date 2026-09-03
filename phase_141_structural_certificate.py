"""Fully structural n=7 derivation of the 141 shifted saturated states.

Inputs already earned by independent certificates:
  * symbolic phase theorem -> local displacement languages A/B/C;
  * exact C component theorem -> C local counts from induced +/-3 components;
  * translation reduction -> 13 colored-partition orbit representatives.

This certificate removes the last local permutation enumeration from the derivation.
For every A/B block S it evaluates the permanent of the induced allowed-displacement
matrix by Ryser inclusion-exclusion over subsets of S.  For C it uses the structural
component formula.  Translation symmetry supplies the orbit multiplicity.

No global partition-derangement state enumeration and no local permutation
enumeration are used to derive 141.  The earlier enumerative certificates are loaded
only after the structural sum is complete, as independent verification targets.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from phase_141_orbit_certificate import REPS
from phase_C_component_theorem_certificate import predicted_count as c_component_count

N = 7
ALLOWED = {
    'A': {4, 5, 6},
    'B': {2, 4, 5},
}


def induced_ryser_permanent(color: str, S0: tuple[int, ...]) -> tuple[int, list[dict]]:
    """Permanent of the induced local language via Ryser, never permutations."""
    S = tuple(sorted(S0))
    k = len(S)
    if k == 0:
        return 1, [{'column_subset': [], 'row_sums': [], 'term': 1}]
    D = ALLOWED[color]
    terms = []
    total = 0
    for mask in range(1 << k):
        T = {S[j] for j in range(k) if mask & (1 << j)}
        row_sums = [sum(((y - x) % N) in D for y in T) for x in S]
        prod = 1
        for d in row_sums:
            prod *= d
        term = ((-1) ** (k - len(T))) * prod
        total += term
        terms.append({
            'column_subset': sorted(T),
            'row_sums': row_sums,
            'term': term,
        })
    return total, terms


def rotate_part(part: tuple[tuple[int, ...], ...], r: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(sorted((x + r) % N for x in block)) for block in part)


def orbit_size(part: tuple[tuple[int, ...], ...]) -> int:
    return len({rotate_part(part, r) for r in range(N)})


def main() -> None:
    rows = []
    structural_total = 0
    local_ryser_evaluations = 0
    local_ryser_subset_terms = 0

    for raw_part, old_expected_factors in REPS:
        part = tuple(tuple(x for x in block) for block in raw_part)
        A, B, C = part
        a_count, a_terms = induced_ryser_permanent('A', A)
        b_count, b_terms = induced_ryser_permanent('B', B)
        c_count = c_component_count(N, frozenset(C))
        factors = (a_count, b_count, c_count)

        # The previously recorded local factors are verifier targets only; they are
        # checked after the three structural calculations above have completed.
        assert factors == old_expected_factors, (part, factors, old_expected_factors)

        osz = orbit_size(part)
        weight = a_count * b_count * c_count
        contribution = osz * weight
        structural_total += contribution
        local_ryser_evaluations += 2
        local_ryser_subset_terms += len(a_terms) + len(b_terms)
        rows.append({
            'A': list(A), 'B': list(B), 'C': list(C),
            'size_triple': [len(A), len(B), len(C)],
            'orbit_size': osz,
            'A_ryser_permanent': a_count,
            'B_ryser_permanent': b_count,
            'C_component_count': c_count,
            'local_factor_product': weight,
            'contribution': contribution,
            'A_ryser_term_count': len(a_terms),
            'B_ryser_term_count': len(b_terms),
        })

    assert len(rows) == 13
    assert structural_total == 141, structural_total

    # Independent verifier 1: prior 13-orbit certificate, whose local factors came
    # from permutation enumeration.  It is not part of this derivation.
    old_orbit = json.loads(Path('artifacts/phase_141_orbit_certificate.json').read_text())
    assert old_orbit['weighted_orbit_sum'] == structural_total
    assert old_orbit['rotation_orbit_count'] == 13

    # Independent verifier 2: original 16,146-state global enumeration.
    old_global = json.loads(Path('artifacts/phase_block_feasibility_probe.json').read_text())
    assert old_global['legal_partition_derangement_states'] == structural_total

    # Independent verifier 3: full-block Ryser orbit certificate.
    full_ryser = json.loads(Path('artifacts/phase_AB_ryser_certificate.json').read_text())
    full_A = next(r for r in rows if r['size_triple'] == [7, 0, 0])
    full_B = next(r for r in rows if r['size_triple'] == [0, 7, 0])
    assert full_A['A_ryser_permanent'] == full_ryser['colors']['A']['ryser_permanent'] == 31
    assert full_B['B_ryser_permanent'] == full_ryser['colors']['B']['ryser_permanent'] == 24

    out = {
        'claim': (
            'At n=7 the 141 shifted saturated states are the structural weighted sum '
            'over 13 translation-orbit representatives, with A/B factors computed by '
            'induced Ryser permanents and C factors by the +/-3 component theorem.'
        ),
        'orbit_rows': rows,
        'orbit_count': 13,
        'structural_weighted_sum': structural_total,
        'local_ryser_evaluations': local_ryser_evaluations,
        'local_ryser_subset_terms': local_ryser_subset_terms,
        'local_permutation_enumeration_used_to_derive_141': False,
        'global_state_enumeration_used_to_derive_141': False,
        'independent_prior_orbit_certificate_exact': old_orbit['weighted_orbit_sum'] == structural_total,
        'independent_global_enumeration_exact': old_global['legal_partition_derangement_states'] == structural_total,
        'independent_full_ryser_certificate_exact': True,
        'derivation_stack': [
            'symbolic phase displacement exclusions',
            '13 colored-partition translation-orbit representatives',
            'Ryser inclusion-exclusion for every induced A/B permanent',
            'exact C +/-3 component counting theorem',
            'translation orbit multiplicity',
            'weighted sum = 141',
        ],
        'residual': (
            'The n=7 shifted frontier count is now structural rather than enumerative. '
            'The next consequential question is attachment: join this 141-state structural '
            'classification back to the E677->E255 magma equations and determine which '
            'phase/orbit class is killed by the first source-backed mixed constraint. '
            'Do not refine the counting representation further unless attachment exposes '
            'a new residual.'
        ),
    }
    Path('artifacts/phase_141_structural_certificate.json').write_text(
        json.dumps(out, indent=2, sort_keys=True) + '\n'
    )
    print(json.dumps({
        'orbit_count': out['orbit_count'],
        'structural_weighted_sum': out['structural_weighted_sum'],
        'local_permutation_enumeration_used': False,
        'global_state_enumeration_used': False,
        'derivation_stack': out['derivation_stack'],
        'residual': out['residual'],
    }, indent=2, sort_keys=True))
    print('PHASE_141_STRUCTURAL_CERTIFICATE_PASS')


if __name__ == '__main__':
    main()
