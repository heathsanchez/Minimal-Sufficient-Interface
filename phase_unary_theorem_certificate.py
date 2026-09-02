"""Independent finite certificate for the n=7 unary phase invariant.

For every saturated partition/derangement state, define phase support as the set of
(color, cyclic displacement) pairs attained by its colored derangements.
The candidate theorem is:

  shifted_ok  <->  phase_support is disjoint from FORBIDDEN.

We exhaust the complete saturated universe, then ablate each forbidden atom to prove
that every atom is necessary inside this unary language.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from partition_derangement_probe import COLORS, N, PAIRS, enumerate_states

FORBIDDEN=frozenset({
    ('A',1),('A',2),('A',3),
    ('B',1),('B',3),('B',6),
    ('C',1),('C',2),('C',5),('C',6),
})
ALLOWED={c:tuple(d for d in range(1,N) if (c,d) not in FORBIDDEN) for c in COLORS}


def shifted_direct(rows):
    # Reimplemented here rather than importing shifted_ok.
    for t,u in PAIRS:
        delta=u-t
        for i in range(N):
            if rows[u][i] == rows[t][(i+delta)%N]:
                return False
    return True


def support(blocks,sigmas):
    return frozenset((c,(sigmas[c][i]-i)%N) for c in COLORS for i in blocks[c])


def unary_accept(s, forbidden=FORBIDDEN):
    return s.isdisjoint(forbidden)


def main():
    total=pos=0; fp=fn=0
    forbidden_occurrences=Counter(); allowed_positive_occurrences=Counter()
    witnesses={}
    all_states=[]
    for blocks,sigmas,rows in enumerate_states():
        s=support(blocks,sigmas); y=shifted_direct(rows); pred=unary_accept(s)
        total+=1; pos+=int(y); fp+=int(pred and not y); fn+=int(y and not pred)
        all_states.append((s,y))
        for atom in s & FORBIDDEN: forbidden_occurrences[atom]+=1
        if y:
            for atom in s: allowed_positive_occurrences[atom]+=1
        if pred != y and 'mismatch' not in witnesses:
            witnesses['mismatch']={'support':sorted(s),'rows':[list(r) for r in rows]}

    assert total==16146
    assert pos==141
    assert fp==0 and fn==0

    ablations={}
    for atom in sorted(FORBIDDEN):
        reduced=FORBIDDEN-{atom}
        afp=sum(unary_accept(s,reduced) and not y for s,y in all_states)
        afn=sum((not unary_accept(s,reduced)) and y for s,y in all_states)
        # If dropping an atom never changes the accepted set, it is redundant.
        ablations[f'{atom[0]}:{atom[1]}']={'false_positives':afp,'false_negatives':afn,'necessary':afp>0}
        assert afp>0 and afn==0, (atom,afp,afn)

    # Every non-forbidden phase atom should actually appear in a positive state;
    # otherwise the allowed language could still be shrunk without consequence.
    live_allowed={atom for atom,n in allowed_positive_occurrences.items() if n>0}
    expected_allowed={(c,d) for c in COLORS for d in range(1,N)}-set(FORBIDDEN)
    assert live_allowed==expected_allowed, (live_allowed,expected_allowed)

    out={
        'n':N,'total_states':total,'shifted_states':pos,
        'theorem':'shifted_ok iff phase support avoids the ten forbidden color-displacement atoms',
        'forbidden_atoms':[list(x) for x in sorted(FORBIDDEN)],
        'allowed_displacements':{c:list(ALLOWED[c]) for c in COLORS},
        'false_positives':fp,'false_negatives':fn,
        'all_allowed_atoms_realized_by_shifted_states':True,
        'forbidden_atom_occurrences':{f'{c}:{d}':forbidden_occurrences[(c,d)] for c,d in sorted(FORBIDDEN)},
        'single_atom_ablations':ablations,
        'unary_irredundant':all(x['necessary'] for x in ablations.values()),
        'residual':'Derive the ten forbidden displacement sets from the six shifted row-pair inequalities symbolically, then feed this theorem back into the recursive compiler as a promoted law/capability.'
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_unary_theorem_certificate.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:out[k] for k in ('total_states','shifted_states','allowed_displacements','false_positives','false_negatives','unary_irredundant','residual')},indent=2,sort_keys=True))
    print('PHASE_UNARY_THEOREM_CERTIFICATE_PASS')

if __name__=='__main__': main()
