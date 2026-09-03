"""Finite n=7 certificate reconstructing the 141 shifted states from 13 partition orbits.

This is a compression certificate, not an arbitrary-n theorem.  It uses the already
proved phase/block-size laws and the local constrained-permutation languages.  The
actual derivation is the explicit list of 13 Z/7 rotation-orbit representatives and
their local weights.  Completeness is independently replayed over the 3^7 color
assignments only; the 16,146 global partition-derangement states are never enumerated.

For a colored partition (A,B,C), its weight is
  per_A(A) * per_B(B) * per_C(C),
where per_color is the number of legal local permutations.  Translation preserves
all displacement languages, so weight is constant on a rotation orbit.  Mixed
partitions have orbit size 7 because 7 is prime; monochromatic partitions have orbit
size 1.  The 13 representatives therefore give the exact total 141.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

N=7
ALLOWED={'A':{4,5,6},'B':{2,4,5},'C':{3,4}}

# (A,B,C), expected local factor triple (a,b,c).
REPS=[
    (((),(),(0,1,2,3,4,5,6)), (1,1,2)),
    ((((),(0,2,4),(1,3,5,6))), (1,1,1)),
    ((((),(0,1,2,4,5),(3,6))), (1,2,1)),
    ((((),(0,1,2,3,4,5,6),())), (1,24,1)),
    ((((0,1,4),(),(2,3,5,6))), (1,1,1)),
    ((((0,2,4),(),(1,3,5,6))), (1,1,1)),
    ((((0,1,4),(3,5),(2,6))), (1,1,1)),
    ((((0,1,4),(2,3,5,6),())), (1,1,1)),
    ((((0,2,4),(1,3,5,6),())), (1,1,1)),
    ((((0,1,3,5),(2,4,6),())), (1,1,1)),
    ((((0,1,2,4,5),(),(3,6))), (2,1,1)),
    ((((0,1,2,3,5),(4,6),())), (1,1,1)),
    ((((0,1,2,3,4,5,6),(),())), (31,1,1)),
]


def local_count(color,S):
    xs=tuple(S)
    if not xs: return 1
    total=0
    for ys in itertools.permutations(xs):
        if all(x!=y and ((y-x)%N) in ALLOWED[color] for x,y in zip(xs,ys)):
            total+=1
    return total


def rotate(part,r):
    return tuple(tuple(sorted((x+r)%N for x in block)) for block in part)


def canon(part):
    return min(rotate(part,r) for r in range(N))


def orbit(part):
    return {rotate(part,r) for r in range(N)}


def weight(part):
    return local_count('A',part[0])*local_count('B',part[1])*local_count('C',part[2])


def main():
    normalized=[]
    represented=set()
    weighted_terms=[]
    for part,expected_factors in REPS:
        part=tuple(tuple(x for x in block) for block in part)
        assert canon(part)==part, part
        assert set(part[0])|set(part[1])|set(part[2])==set(range(N))
        assert not (set(part[0])&set(part[1]) or set(part[0])&set(part[2]) or set(part[1])&set(part[2]))
        factors=tuple(local_count(c,b) for c,b in zip(('A','B','C'),part))
        assert factors==expected_factors,(part,factors,expected_factors)
        orb=orbit(part)
        orbit_size=len(orb)
        w=factors[0]*factors[1]*factors[2]
        represented |= orb
        weighted_terms.append(orbit_size*w)
        normalized.append({
            'A':list(part[0]),'B':list(part[1]),'C':list(part[2]),
            'size_triple':[len(x) for x in part],
            'local_factors':list(factors),'weight':w,'orbit_size':orbit_size,
            'contribution':orbit_size*w,
        })

    assert len(REPS)==13
    assert len(represented)==73
    assert sum(weighted_terms)==141

    # Independent completeness verifier over colored partitions only (3^7=2187).
    # This does not enumerate any local-permutation choices or the 16,146 global states.
    legal_partitions=set()
    legal_by_triple={}
    for colors in itertools.product(range(3), repeat=N):
        part=tuple(tuple(i for i,c in enumerate(colors) if c==k) for k in range(3))
        w=weight(part)
        if w:
            legal_partitions.add(part)
            key=str(tuple(len(x) for x in part))
            legal_by_triple[key]=legal_by_triple.get(key,0)+w
    assert legal_partitions==represented
    assert sum(weight(p) for p in legal_partitions)==141

    expected_by_triple={
        '(0, 0, 7)':2,'(0, 3, 4)':7,'(0, 5, 2)':14,'(0, 7, 0)':24,
        '(3, 0, 4)':14,'(3, 2, 2)':7,'(3, 4, 0)':14,'(4, 3, 0)':7,
        '(5, 0, 2)':14,'(5, 2, 0)':7,'(7, 0, 0)':31,
    }
    assert legal_by_triple==expected_by_triple,(legal_by_triple,expected_by_triple)

    # Previous 16,146-state probe is used only as a final independent target comparison.
    blk=json.loads(Path('artifacts/phase_block_feasibility_probe.json').read_text())
    assert blk['legal_partition_derangement_states']==141
    assert blk['state_counts_by_size_triple']==expected_by_triple

    out={
        'claim':'At n=7 the shifted saturated frontier is exactly the weighted union of 13 rotation orbits of colored partitions.',
        'rotation_orbit_representatives':normalized,
        'rotation_orbit_count':13,
        'legal_colored_partition_count':73,
        'weighted_orbit_terms':weighted_terms,
        'weighted_orbit_sum':sum(weighted_terms),
        'state_counts_by_size_triple':legal_by_triple,
        'global_16146_state_enumeration_used_to_derive_certificate':False,
        'independent_colored_partition_assignments_checked':3**7,
        'independent_completeness_exact':legal_partitions==represented,
        'residual':(
            'The 141 frontier is now compressed to 13 translation-orbit representatives. '
            'Derive the local A/B degree-signature counting law itself (especially the full '
            'counts 31 and 24) without permutation enumeration, e.g. by a transfer matrix '
            'or cycle-cover recurrence, so the 141 count becomes fully structural.'
        ),
    }
    Path('artifacts/phase_141_orbit_certificate.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'rotation_orbits':13,'legal_colored_partitions':73,
        'weighted_terms':weighted_terms,'weighted_sum':sum(weighted_terms),
        'independent_colored_partition_assignments_checked':3**7,
        'global_16146_state_enumeration_used':False,
        'residual':out['residual'],
    },indent=2,sort_keys=True))
    print('PHASE_141_ORBIT_CERTIFICATE_PASS')

if __name__=='__main__': main()
