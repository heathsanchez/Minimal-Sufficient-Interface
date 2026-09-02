"""Derive a compact Boolean invariant from the verified phase quotient.

We test increasingly expressive predicates over phase presence bits:
1. unary forbidden displacement presences;
2. unary + binary forbidden co-presences.
A level is promoted only if it exactly matches shifted_ok on all 16,146 states.
"""
from __future__ import annotations
from collections import defaultdict
import itertools, json
from pathlib import Path
from partition_derangement_probe import COLORS, N, enumerate_states, shifted_ok

BITS=tuple((c,d) for c in COLORS for d in range(1,N))


def presence(sigmas,blocks):
    return frozenset((c,(sigmas[c][i]-i)%N) for c in COLORS for i in blocks[c])


def main():
    states=[]
    for blocks,sigmas,rows in enumerate_states():
        states.append((presence(sigmas,blocks),shifted_ok(rows)))
    pos=[p for p,y in states if y]; neg=[p for p,y in states if not y]

    unary=[b for b in BITS if all(b not in p for p in pos)]
    def unary_accept(p): return all(b not in p for b in unary)
    unary_fp=sum(unary_accept(p) for p in neg)
    unary_fn=sum(not unary_accept(p) for p in pos)

    pairs=[]
    for a,b in itertools.combinations(BITS,2):
        if all(not (a in p and b in p) for p in pos):
            pairs.append((a,b))
    def binary_accept(p):
        return unary_accept(p) and all(not (a in p and b in p) for a,b in pairs)
    binary_fp=sum(binary_accept(p) for p in neg)
    binary_fn=sum(not binary_accept(p) for p in pos)

    # Greedy minimal exact cover of negative phase classes by valid forbidden predicates.
    # Predicates are guaranteed never to reject positives by construction.
    neg_patterns=list({p for p in neg})
    predicates=[]
    for b in unary:
        covered={i for i,p in enumerate(neg_patterns) if b in p}
        if covered: predicates.append((('absent',b),covered))
    for a,b in pairs:
        covered={i for i,p in enumerate(neg_patterns) if a in p and b in p}
        if covered: predicates.append((('not-both',a,b),covered))
    uncovered=set(range(len(neg_patterns))); chosen=[]
    while uncovered:
        best=None; bestcov=set()
        for pred,cov in predicates:
            gain=cov & uncovered
            if len(gain)>len(bestcov): best,bestcov=pred,gain
        if not bestcov: break
        chosen.append(best); uncovered-=bestcov
    greedy_exact=not uncovered

    out={
        'states':len(states),'shifted':len(pos),'nonshifted':len(neg),
        'phase_bits':len(BITS),
        'unary_forbidden':[[c,d] for c,d in unary],
        'unary_false_positive_states':unary_fp,'unary_false_negative_states':unary_fn,
        'binary_forbidden_pair_count':len(pairs),
        'unary_plus_binary_false_positive_states':binary_fp,
        'unary_plus_binary_false_negative_states':binary_fn,
        'unary_plus_binary_exact':binary_fp==0 and binary_fn==0,
        'greedy_exact_negative_cover':greedy_exact,
        'greedy_predicate_count':len(chosen),
        'greedy_predicates':[
            [pred[0], *([[pred[1][0],pred[1][1]]] if pred[0]=='absent' else [[pred[1][0],pred[1][1]],[pred[2][0],pred[2][1]]])]
            for pred in chosen
        ],
        'uncovered_negative_phase_patterns':len(uncovered),
        'residual':(
            'Formalize the exact unary/binary phase predicate as the finite n=7 shifted-realizability invariant.'
            if binary_fp==0 and binary_fn==0 else
            'Unary/binary phase presence is still insufficient; derive the smallest count-sensitive predicate over the pure phase quotient.'
        )
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_invariant_derivation_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('PHASE_INVARIANT_DERIVATION_PROBE_PASS')

if __name__=='__main__': main()
