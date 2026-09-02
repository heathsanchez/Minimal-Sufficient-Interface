"""Exact quotient search for the saturated E677 shifted-realizability frontier.

Goal: find the coarsest tested representation that preserves whether a saturated state
satisfies the shifted row-pair constraints, without retaining the full four rows.
Every proposed quotient is evaluated over the complete 16,146-state saturated universe.
If a quotient aliases shifted/non-shifted states, emit an exact collision witness.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from partition_derangement_probe import COLORS, N, enumerate_states, profile, cycle_type, shifted_ok


def mask_word(blocks):
    owner={i:c for c in COLORS for i in blocks[c]}
    return tuple(owner[i] for i in range(N))


def canonical_rotation(word):
    rots=[word[k:]+word[:k] for k in range(N)]
    return min(rots)


def displacement_signature(sigmas, blocks):
    """Retain cyclic phase information but not point identities: multiset of displacements per color."""
    return tuple(tuple(sorted((sigmas[c][i]-i) % N for i in blocks[c])) for c in COLORS)


def displacement_transition_signature(sigmas, blocks):
    """Second-order cyclic geometry: multiset of (input gap, displacement) around each color block."""
    out=[]
    for c in COLORS:
        xs=sorted(blocks[c])
        if not xs:
            out.append(())
            continue
        vals=[]
        for j,i in enumerate(xs):
            nxt=xs[(j+1)%len(xs)]
            gap=(nxt-i)%N
            disp=(sigmas[c][i]-i)%N
            vals.append((gap,disp))
        out.append(tuple(sorted(vals)))
    return tuple(out)


def quotient_features(blocks,sigmas,rows):
    sizes=tuple(len(blocks[c]) for c in COLORS)
    p=profile(rows)
    cyc=tuple(cycle_type(sigmas[c],blocks[c]) for c in COLORS)
    word=mask_word(blocks)
    rotword=canonical_rotation(word)
    disp=displacement_signature(sigmas,blocks)
    trans=displacement_transition_signature(sigmas,blocks)
    return {
        'sizes': sizes,
        'profile': p,
        'cycle': cyc,
        'sizes+cycle': (sizes,cyc),
        'profile+cycle': (p,cyc),
        'rotation_partition+cycle': (rotword,cyc),
        'phase': disp,
        'cycle+phase': (cyc,disp),
        'rotation_partition+phase': (rotword,disp),
        'rotation_partition+cycle+phase': (rotword,cyc,disp),
        'transition_phase': trans,
        'cycle+transition_phase': (cyc,trans),
        'rotation_partition+transition_phase': (rotword,trans),
    }


def jsonify(x):
    if isinstance(x, tuple): return [jsonify(v) for v in x]
    if isinstance(x, list): return [jsonify(v) for v in x]
    return x


def main():
    partitions=defaultdict(lambda: defaultdict(lambda:{False:[],True:[]}))
    total=0; shifted=0
    for blocks,sigmas,rows in enumerate_states():
        total+=1
        y=shifted_ok(rows); shifted+=int(y)
        feats=quotient_features(blocks,sigmas,rows)
        compact={
            'blocks': {c:list(blocks[c]) for c in COLORS},
            'sigmas': {c:{str(k):v for k,v in sigmas[c].items()} for c in COLORS},
            'rows': [list(r) for r in rows],
        }
        for name,key in feats.items():
            bucket=partitions[name][key][y]
            if len(bucket)<1: bucket.append(compact)

    results={}; pure=[]
    for name,classes in partitions.items():
        mixed=[]
        for key,sides in classes.items():
            if sides[False] and sides[True]:
                mixed.append({
                    'feature': jsonify(key),
                    'nonshifted': sides[False][0],
                    'shifted': sides[True][0],
                })
        results[name]={
            'classes':len(classes),
            'mixed_classes':len(mixed),
            'pure':not mixed,
            'collision':mixed[0] if mixed else None,
        }
        if not mixed: pure.append(name)

    # Prefer fewer quotient classes among exact/pure tested representations.
    best=min(pure,key=lambda n:results[n]['classes']) if pure else None
    out={
        'total_states':total,
        'shifted_states':shifted,
        'tested_quotients':results,
        'pure_quotients':pure,
        'coarsest_tested_pure_quotient':best,
        'coarsest_tested_pure_classes':results[best]['classes'] if best else None,
        'full_state_classes':total,
        'compression_ratio_vs_full':(total/results[best]['classes']) if best else None,
        'residual':(
            'Promote the coarsest tested pure quotient and derive its invariant form.' if best else
            'All tested quotients alias shifted and non-shifted states; inspect the exact collision of the finest tested quotient and add only the missing relational phase variable.'
        ),
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/shifted_realizability_quotient_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'total_states':total,'shifted_states':shifted,'pure_quotients':pure,
        'coarsest_tested_pure_quotient':best,
        'coarsest_tested_pure_classes':out['coarsest_tested_pure_classes'],
        'compression_ratio_vs_full':out['compression_ratio_vs_full'],
        'residual':out['residual'],
    },indent=2,sort_keys=True))
    print('SHIFTED_REALIZABILITY_QUOTIENT_PROBE_PASS')

if __name__=='__main__': main()
