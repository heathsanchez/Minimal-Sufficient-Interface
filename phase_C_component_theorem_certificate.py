"""Symbolic component/counting theorem for the restrictive C phase language.

On a saturated state the symbolic phase theorem says that C may use only phases
outside {+1,+2,-2,-1}.  At n=7 this leaves exactly {+3,-3}.  More generally this
module studies the local language in which every C map edge is x -> x +/- 3.

Let G_n be the undirected graph on Z/n with edges x--(x+3).  It is a disjoint union
of gcd(n,3) cycles.  For S subset Z/n, a bijection sigma:S->S using only +/-3 edges
exists iff every connected component of the induced graph G_n[S] is either:
  * an even path; or
  * an entire base cycle of G_n.
Moreover the number of such bijections factors over components.  An even path has
one (the forced adjacent matching); a full cycle has 1 cover at length 2, 2 covers
at odd length >=3, and 4 covers at even length >=4.

The proof certificate is structural; exhaustive replay for n=4..10 is only an
independent verifier of the formula, not the source of the theorem.
"""
from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from pathlib import Path

STEP = 3


def neighbours(n: int, x: int) -> set[int]:
    return {(x + STEP) % n, (x - STEP) % n} - {x}


def base_orbit(n: int, x: int) -> frozenset[int]:
    seen = set()
    y = x
    while y not in seen:
        seen.add(y)
        y = (y + STEP) % n
    return frozenset(seen)


def induced_components(n: int, S: frozenset[int]) -> list[frozenset[int]]:
    unseen = set(S)
    out = []
    while unseen:
        root = next(iter(unseen))
        stack = [root]
        comp = set()
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            for y in neighbours(n, x):
                if y in S and y not in comp:
                    stack.append(y)
        unseen -= comp
        out.append(frozenset(comp))
    return out


def component_kind(n: int, comp: frozenset[int]) -> str:
    if not comp:
        raise ValueError('empty component')
    if comp == base_orbit(n, next(iter(comp))):
        return 'full-cycle'
    return 'path'


def cycle_cover_count(length: int) -> int:
    if length == 2:
        return 1
    if length >= 3 and length % 2:
        return 2
    if length >= 4 and length % 2 == 0:
        return 4
    raise AssertionError(length)


def predicted_count(n: int, S: frozenset[int]) -> int:
    if not S:
        return 1
    count = 1
    for comp in induced_components(n, S):
        kind = component_kind(n, comp)
        if kind == 'path':
            if len(comp) % 2:
                return 0
            # A finite even path has a unique perfect matching, and bijectivity
            # forces each matched edge to be used in both directions.
        else:
            count *= cycle_cover_count(len(comp))
    return count


def exhaustive_count(n: int, S: frozenset[int]) -> int:
    """Independent local verifier: enumerate at most two allowed images per vertex."""
    if not S:
        return 1
    xs = tuple(sorted(S))
    choices = [tuple(sorted(neighbours(n, x) & S)) for x in xs]
    if any(not c for c in choices):
        return 0
    total = 0
    for ys in itertools.product(*choices):
        if len(set(ys)) == len(xs):
            total += 1
    return total


def structural_proof_record() -> dict:
    return {
        'necessity': [
            'A legal sigma is a directed cycle cover of the induced +/-3 graph.',
            'Every proper induced component of a base cycle is a path.',
            'A path has a cycle cover only by disjoint 2-cycles, hence only at even order.',
            'A component equal to an entire base cycle admits the directed base-cycle covers.'
        ],
        'sufficiency': [
            'Pair consecutive vertices on each even path; use both directions on each matched edge.',
            'On each full base cycle use a directed rotation; this is fixed-point-free for n>=4.',
            'Components are disjoint, so the local covers combine to a bijection of S.'
        ],
        'counting': [
            'Even path: unique perfect matching, hence exactly one directed bijection.',
            'Full 2-cycle: the two +/-3 neighbours coincide, giving one bijection.',
            'Full odd cycle length >=3: no perfect matching, only the two directed rotations.',
            'Full even cycle length >=4: two directed rotations plus the two perfect matchings.'
        ]
    }


def main() -> None:
    replay = {}
    all_exact = True
    for n in range(4, 11):
        mismatches = []
        feasible_sizes = Counter()
        predicted_feasible_sizes = Counter()
        for mask in range(1 << n):
            S = frozenset(i for i in range(n) if mask & (1 << i))
            obs = exhaustive_count(n, S)
            pred = predicted_count(n, S)
            if obs:
                feasible_sizes[len(S)] += 1
            if pred:
                predicted_feasible_sizes[len(S)] += 1
            if obs != pred:
                mismatches.append({'subset': sorted(S), 'observed': obs, 'predicted': pred})
        exact = not mismatches and feasible_sizes == predicted_feasible_sizes
        all_exact &= exact
        replay[str(n)] = {
            'gcd_n_3': math.gcd(n, STEP),
            'base_cycle_length': n // math.gcd(n, STEP),
            'exact': exact,
            'mismatch_count': len(mismatches),
            'feasible_subset_counts_by_size': {str(k): v for k, v in sorted(feasible_sizes.items())},
        }

    n = 7
    c7 = replay['7']
    expected_sizes = {'0', '2', '4', '6', '7'}
    assert set(c7['feasible_subset_counts_by_size']) == expected_sizes, c7
    assert all_exact, replay

    theorem = (
        'For n>=4, a subset S of Z/n admits a fixed-point-free permutation using only '
        'displacements +/-3 iff every component of the induced +/-3 graph on S is an '
        'even path or an entire +/-3 base cycle. The number of legal permutations factors '
        'over components: 1 per even path; for a full cycle, 1 at length 2, 2 at odd '
        'length >=3, and 4 at even length >=4.'
    )
    n7_corollary = (
        'At n=7 the +/-3 graph is one 7-cycle. Hence every proper legal C block is a '
        'disjoint union of even paths and therefore has even cardinality; the only odd '
        'legal C block is the whole 7-cycle. Thus C-block sizes are exactly 0,2,4,6,7.'
    )
    out = {
        'theorem': theorem,
        'structural_proof': structural_proof_record(),
        'cross_order_exhaustive_replay_n4_to_n10': replay,
        'all_replays_exact': all_exact,
        'n7_corollary': n7_corollary,
        'n7_feasible_subset_counts_by_size': c7['feasible_subset_counts_by_size'],
        'n7_feasible_sizes': sorted(int(k) for k in c7['feasible_subset_counts_by_size']),
        'residual': (
            'Join the exact C-component theorem with the A/B derangement block constraints '
            'and the disjoint size equation |A|+|B|+|C|=7. Derive the strongest '
            'non-enumerative restriction on feasible ordered block-size triples and test '
            'whether it reconstructs the phase-block frontier before any state enumeration.'
        ),
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_C_component_theorem_certificate.json').write_text(
        json.dumps(out, indent=2, sort_keys=True) + '\n'
    )
    print(json.dumps({
        'theorem': theorem,
        'n7_corollary': n7_corollary,
        'n7_feasible_subset_counts_by_size': c7['feasible_subset_counts_by_size'],
        'all_replays_exact': all_exact,
        'residual': out['residual'],
    }, indent=2, sort_keys=True))
    print('PHASE_C_COMPONENT_THEOREM_CERTIFICATE_PASS')


if __name__ == '__main__':
    main()
