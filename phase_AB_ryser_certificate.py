"""Structural n=7 certificate for the full A/B local counts 31 and 24.

The remaining full-block counts are permanents of 7x7 circulant 0-1 matrices.
This certificate derives them with Ryser's inclusion-exclusion identity and then
quotients the 2^7 column subsets by cyclic translation.  Thus the derivation uses
20 subset orbits rather than enumerating 7! permutations.

For an allowed displacement set D and M[x,y]=1 iff y-x in D,

  per(M) = sum_{S subset Z_7} (-1)^(7-|S|) prod_x |(x+D) intersect S|.

Because M is circulant, the summand is invariant under translation of S.  For
prime order 7, the empty and full subsets are singleton orbits and every other
subset orbit has size 7, giving exactly 20 translation orbits.

A brute-force permutation count is used only as an independent verifier, never
as the derivation.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

N = 7
ALLOWED = {
    'A': {4, 5, 6},
    'B': {2, 4, 5},
}


def translate(S: frozenset[int], r: int) -> frozenset[int]:
    return frozenset((x + r) % N for x in S)


def orbit(S: frozenset[int]) -> set[frozenset[int]]:
    return {translate(S, r) for r in range(N)}


def canon(S: frozenset[int]) -> tuple[int, ...]:
    return min(tuple(sorted(T)) for T in orbit(S))


def row_degrees(D: set[int], S: frozenset[int]) -> tuple[int, ...]:
    # Row x has allowed columns x+D.
    return tuple(sum(((x + d) % N) in S for d in D) for x in range(N))


def ryser_summand(D: set[int], S: frozenset[int]) -> int:
    prod = 1
    for deg in row_degrees(D, S):
        prod *= deg
    return ((-1) ** (N - len(S))) * prod


def ryser_orbit_table(D: set[int]) -> tuple[list[dict], int]:
    reps: dict[tuple[int, ...], frozenset[int]] = {}
    for mask in range(1 << N):
        S = frozenset(i for i in range(N) if mask & (1 << i))
        reps.setdefault(canon(S), S)

    rows = []
    total = 0
    for key in sorted(reps, key=lambda k: (len(k), k)):
        S = frozenset(key)
        orb = orbit(S)
        degs = row_degrees(D, S)
        term = ryser_summand(D, S)
        # Translation invariance is checked explicitly over the entire orbit.
        orbit_terms = {ryser_summand(D, T) for T in orb}
        orbit_degrees = {tuple(sorted(row_degrees(D, T))) for T in orb}
        assert orbit_terms == {term}
        assert len(orbit_degrees) == 1
        contribution = len(orb) * term
        total += contribution
        rows.append({
            'subset_rep': list(key),
            'subset_size': len(S),
            'orbit_size': len(orb),
            'row_degree_multiset': sorted(degs),
            'row_degree_product': abs(term),
            'ryser_sign': 1 if term >= 0 else -1,
            'representative_summand': term,
            'orbit_contribution': contribution,
        })
    return rows, total


def brute_permanent(D: set[int]) -> int:
    """Independent verifier only."""
    total = 0
    for p in itertools.permutations(range(N)):
        if all(((p[x] - x) % N) in D for x in range(N)):
            total += 1
    return total


def main() -> None:
    out = {
        'n': N,
        'identity': (
            'per(M)=sum_{S subset Z_7} (-1)^(7-|S|) product_x |(x+D) intersect S|'
        ),
        'translation_quotient_claim': (
            'For a circulant M the Ryser summand is translation invariant, so the 128 '
            'subsets collapse to 20 Z_7 translation orbits.'
        ),
        'permutation_enumeration_used_to_derive_counts': False,
        'colors': {},
    }

    expected = {'A': 31, 'B': 24}
    for color, D in ALLOWED.items():
        table, ryser_total = ryser_orbit_table(D)
        brute = brute_permanent(D)
        assert len(table) == 20, len(table)
        assert sum(r['orbit_size'] for r in table) == 128
        assert ryser_total == expected[color], (color, ryser_total)
        assert brute == ryser_total, (color, brute, ryser_total)

        # A second compression records how many distinct degree signatures actually
        # occur among the 20 orbit representatives.  This joins the earlier finding
        # that degree signature is the smallest tested exact local-count quotient.
        sigs = {}
        for r in table:
            sig = (r['subset_size'], tuple(r['row_degree_multiset']))
            sigs.setdefault(str(sig), {'orbit_count': 0, 'total_orbit_size': 0, 'contribution': 0})
            sigs[str(sig)]['orbit_count'] += 1
            sigs[str(sig)]['total_orbit_size'] += r['orbit_size']
            sigs[str(sig)]['contribution'] += r['orbit_contribution']

        out['colors'][color] = {
            'allowed_displacements': sorted(D),
            'translation_orbit_count': len(table),
            'ryser_orbit_table': table,
            'degree_signature_class_count': len(sigs),
            'degree_signature_aggregate': sigs,
            'ryser_permanent': ryser_total,
            'independent_bruteforce_permanent': brute,
            'independent_verifier_exact': brute == ryser_total,
        }

    out['all_counts_exact'] = all(
        out['colors'][c]['ryser_permanent'] == expected[c] for c in expected
    )
    out['residual'] = (
        'Replace every local permutation enumeration in the 13-orbit 141 certificate '
        'with a Ryser/degree-signature calculation.  If the weighted sum remains 141, '
        'the entire shifted frontier count is derived from phase laws, component structure, '
        'translation symmetry, and inclusion-exclusion, with global enumeration only as an '
        'independent verifier.'
    )

    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_AB_ryser_certificate.json').write_text(
        json.dumps(out, indent=2, sort_keys=True) + '\n'
    )
    print(json.dumps({
        'A': {
            'permanent': out['colors']['A']['ryser_permanent'],
            'translation_orbits': out['colors']['A']['translation_orbit_count'],
            'degree_signature_classes': out['colors']['A']['degree_signature_class_count'],
        },
        'B': {
            'permanent': out['colors']['B']['ryser_permanent'],
            'translation_orbits': out['colors']['B']['translation_orbit_count'],
            'degree_signature_classes': out['colors']['B']['degree_signature_class_count'],
        },
        'all_counts_exact': out['all_counts_exact'],
        'permutation_enumeration_used_to_derive_counts': False,
        'residual': out['residual'],
    }, indent=2, sort_keys=True))
    print('PHASE_AB_RYSER_CERTIFICATE_PASS')


if __name__ == '__main__':
    main()
