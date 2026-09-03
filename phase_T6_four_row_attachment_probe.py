"""First source-backed post-phase attachment: four-row T6 pair-kernel projection.

The 141 shifted saturated states are four permutation rows U_0,...,U_3.  Their
existing shifted test

    U_u(i) != U_t(i+u-t)

is exactly the upstream cyclic-Q PAIR-LATIN law after i=T-u.  The next upstream
law, T6 PAIR-KERNEL, is therefore attachable to the same rows without inventing
a correspondence:

    U_t^-1(s)=U_u^-1(s)
      iff
    D(U_t(s)-t)-A(U_t(s)) = D(U_u(s)-u)-A(U_u(s)).

This probe tests the necessary four-row projection only.  For each of the exact
141 phase states it asks whether there EXISTS a normalized permutation A fixing
0 and one of the four exact minimum-curvature canonical D maps such that
PAIR-KERNEL holds for every s and every pair among t=0,1,2,3.

A rejection is a genuine exclusion from that canonical-D layer because any full
seven-row T6 core must satisfy every four-row pair projection.  A survivor is
NOT a solution of E677->E255; it has passed only this necessary projection.

Sources (upstream Grisha-Pochuev/finite-magma-e677-to-e255):
  lemmas/e677_cyclic_P_T6_support_and_pair_clique_boundary.md
  lemmas/e677_cyclic_P_minimum_D_curvature_four_transversal_boundary.md
"""
from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

from partition_derangement_probe import enumerate_states, shifted_ok, COLORS
from phase_141_orbit_certificate import REPS

N=7
ROW_IDS=range(4)
ROW_PAIRS=tuple(itertools.combinations(ROW_IDS,2))
CANONICAL_D={
    '0125634': (0,1,2,5,6,3,4),
    '0145236': (0,1,4,5,2,3,6),
    '1023546': (1,0,2,3,5,4,6),
    '1024356': (1,0,2,4,3,5,6),
}
A_FIX0=tuple((0,)+p for p in itertools.permutations(range(1,N)))


def inverse(p):
    q=[None]*N
    for i,v in enumerate(p): q[v]=i
    return tuple(q)


def pair_kernel_ok(rows,A,D):
    invs=tuple(inverse(r) for r in rows)
    for t,u in ROW_PAIRS:
        Ut,Uu=rows[t],rows[u]
        It,Iu=invs[t],invs[u]
        for s in range(N):
            lhs=(It[s]==Iu[s])
            qt=Ut[s]; qu=Uu[s]
            rt=(D[(qt-t)%N]-A[qt])%N
            ru=(D[(qu-u)%N]-A[qu])%N
            if lhs != (rt==ru):
                return False
    return True


def fixed_collision_ok(rows,A,D):
    """Independent equivalent replay of upstream FIX-COLLISION for all 6 pairs."""
    for t,u in ROW_PAIRS:
        Ut,Uu=rows[t],rows[u]
        It=inverse(Ut)
        pi=tuple(Uu[It[q]] for q in range(N))  # U_u o U_t^-1
        fix={q for q in range(N) if pi[q]==q}
        H={q for q in range(N)
           if (D[(q-t)%N]-A[q])%N == (D[(pi[q]-u)%N]-A[pi[q]])%N}
        image_fix={Ut[s] for s in range(N) if s in fix}
        # Since q=U_t(s), U_t(Fix(pi)) in the upstream notation is the image
        # of fixed points viewed in the row-coordinate parameterization.
        # Directly, FIX-COLLISION is equivalent to H={q: U_t^-1(q)=U_u^-1(q)}.
        direct={q for q in range(N) if inverse(Ut)[q]==inverse(Uu)[q]}
        if H != direct:
            return False
    return True


def rotate_blocks(blocks,r):
    return tuple(tuple(sorted((x+r)%N for x in blocks[c])) for c in COLORS)


def block_orbit_key(blocks):
    return min(rotate_blocks(blocks,r) for r in range(N))


def rep_key(raw):
    part,_=raw
    return tuple(tuple(x for x in block) for block in part)


def main():
    expected_rep_keys={rep_key(r) for r in REPS}
    states=[]
    for blocks,sigmas,rows in enumerate_states():
        if shifted_ok(rows):
            states.append((blocks,sigmas,rows))
    assert len(states)==141

    baseline_by_orbit=Counter()
    survivors_by_orbit=Counter()
    survivors_by_D=Counter()
    witness_by_orbit={}
    rejected_examples={}
    independent_equivalence_checks=0

    for idx,(blocks,sigmas,rows) in enumerate(states):
        key=block_orbit_key(blocks)
        assert key in expected_rep_keys, key
        baseline_by_orbit[str(key)]+=1
        witnesses=[]
        for dname,D in CANONICAL_D.items():
            found_A=None
            for A in A_FIX0:
                if pair_kernel_ok(rows,A,D):
                    # Independent check using the set-form equivalent.
                    assert fixed_collision_ok(rows,A,D)
                    independent_equivalence_checks += 1
                    found_A=A
                    break
            if found_A is not None:
                witnesses.append((dname,found_A))
                survivors_by_D[dname]+=1
        if witnesses:
            survivors_by_orbit[str(key)]+=1
            witness_by_orbit.setdefault(str(key),{
                'rows':[list(r) for r in rows],
                'witnesses':[{'D':d,'A':list(A)} for d,A in witnesses],
            })
        else:
            rejected_examples.setdefault(str(key),[list(r) for r in rows])

    surviving=sum(survivors_by_orbit.values())
    rejected=len(states)-surviving
    orbit_rows=[]
    for key in sorted(baseline_by_orbit):
        b=baseline_by_orbit[key]; s=survivors_by_orbit[key]
        orbit_rows.append({'partition_orbit':key,'baseline_states':b,'surviving_states':s,'rejected_states':b-s})

    # Scope/attachment guards.
    assert sum(baseline_by_orbit.values())==141
    assert len(baseline_by_orbit)==13
    # Do not require contraction here: zero contraction is an admissible verified
    # negative result and must change future search rather than fail CI.

    out={
        'scope':'necessary four-row projection of the minimum-curvature canonical-D T6 layer',
        'source_pair_latin':'U_t(T-t) != U_u(T-u)',
        'local_phase_equivalent':'U_u(i) != U_t(i+u-t), i=T-u',
        'source_pair_kernel':(
            'U_t^-1(s)=U_u^-1(s) iff D(U_t(s)-t)-A(U_t(s)) '
            '= D(U_u(s)-u)-A(U_u(s))'
        ),
        'rows_tested':[0,1,2,3],
        'A_domain':'all 720 permutations of Z7 fixing 0',
        'canonical_D':list(CANONICAL_D),
        'baseline_phase_states':141,
        'surviving_phase_states':surviving,
        'rejected_phase_states':rejected,
        'contraction':141-surviving,
        'survivors_by_D':dict(sorted(survivors_by_D.items())),
        'partition_orbit_breakdown':orbit_rows,
        'partition_orbits_with_survivor':sum(r['surviving_states']>0 for r in orbit_rows),
        'partition_orbits_fully_killed':sum(r['surviving_states']==0 for r in orbit_rows),
        'witness_by_surviving_orbit':witness_by_orbit,
        'rejected_example_by_orbit':rejected_examples,
        'independent_fix_collision_witness_checks':independent_equivalence_checks,
        'full_seven_row_core_claimed':False,
        'e677_implication_solved_claimed':False,
    }
    if rejected:
        out['residual']=(
            'T6 PAIR-KERNEL causally contracts the 141-state phase frontier on its '
            'source-backed four-row projection. Extract the minimal pair/s target core '
            'for each killed partition orbit, then test whether the same core generalizes '
            'across canonical D and survives row-choice ablation before promoting a lemma.'
        )
    else:
        out['residual']=(
            'The source-backed four-row T6 PAIR-KERNEL projection does not contract the '
            '141 phase states when A and canonical D are existentially quantified. Retain '
            'this as a negative attachment law and move to the first genuinely multi-row '
            'constraint: TRIANGLE-COCYCLE / extension from four to five or seven rows.'
        )

    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_T6_four_row_attachment_probe.json').write_text(
        json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'baseline':141,
        'surviving':surviving,
        'rejected':rejected,
        'contraction':141-surviving,
        'partition_orbits_fully_killed':out['partition_orbits_fully_killed'],
        'partition_orbits_with_survivor':out['partition_orbits_with_survivor'],
        'survivors_by_D':out['survivors_by_D'],
        'independent_fix_collision_witness_checks':independent_equivalence_checks,
        'residual':out['residual'],
    },indent=2,sort_keys=True))
    print('PHASE_T6_FOUR_ROW_ATTACHMENT_PROBE_PASS')

if __name__=='__main__': main()
