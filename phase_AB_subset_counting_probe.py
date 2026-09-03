"""Diagnostic quotient search for the remaining A/B counting residual at n=7.

The qualitative frontier is already explained symbolically.  This probe asks which
small subset invariant is sufficient to determine the number of legal local A/B
permutations.  It enumerates only the 2^7 subsets for each color and their local
bijections; it does not enumerate global partition-derangement states.

Candidate quotients are deliberately ordered from coarse to fine:
  size
  size + sorted cyclic gaps
  size + allowed-graph degree multiset
  size + sorted gaps + degree multiset
  rotation orbit (exact subset modulo translation)
The first pure quotient with zero count collisions becomes the next representation
candidate; the state-enumerating 141 frontier is never consulted here.
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

N=7
ALLOWED={'A':{4,5,6}, 'B':{2,4,5}}


def local_count(color, S):
    S=tuple(sorted(S))
    if not S:
        return 1
    total=0
    for ys in itertools.permutations(S):
        if all(x != y and ((y-x)%N) in ALLOWED[color] for x,y in zip(S,ys)):
            total += 1
    return total


def rotcanon(S):
    S=frozenset(S)
    if not S:
        return ()
    reps=[]
    for r in range(N):
        reps.append(tuple(sorted((x-r)%N for x in S)))
    return min(reps)


def cyclic_gaps(S):
    xs=sorted(S)
    if not xs:
        return ()
    return tuple(sorted(((xs[(i+1)%len(xs)]-xs[i])%N) for i in range(len(xs))))


def degree_multiset(color,S):
    S=set(S)
    out=[]
    for x in sorted(S):
        outdeg=sum(((y-x)%N) in ALLOWED[color] for y in S if y!=x)
        indeg=sum(((x-y)%N) in ALLOWED[color] for y in S if y!=x)
        out.append((outdeg,indeg))
    return tuple(sorted(out))


def key_for(name,color,S):
    if name=='size': return (len(S),)
    if name=='size+gaps': return (len(S),cyclic_gaps(S))
    if name=='size+degrees': return (len(S),degree_multiset(color,S))
    if name=='size+gaps+degrees': return (len(S),cyclic_gaps(S),degree_multiset(color,S))
    if name=='rotation-orbit': return rotcanon(S)
    raise KeyError(name)


def quotient_report(color, rows, name):
    buckets=defaultdict(lambda: defaultdict(list))
    for row in rows:
        S=frozenset(row['subset'])
        buckets[str(key_for(name,color,S))][row['count']].append(row['subset'])
    collisions=[]
    for key,counts in buckets.items():
        if len(counts)>1:
            collisions.append({'key':key,'counts':sorted(counts),'examples':{str(k):v[:2] for k,v in counts.items()}})
    return {'bucket_count':len(buckets),'collision_count':len(collisions),'collisions':collisions[:12]}


def main():
    names=['size','size+gaps','size+degrees','size+gaps+degrees','rotation-orbit']
    out={'n':N,'colors':{},'global_state_enumeration_used':False}
    for color in ('A','B'):
        rows=[]
        orbit_summary=defaultdict(lambda:{'members':0,'count':None,'size':None,'gaps':None,'degrees':None})
        for mask in range(1<<N):
            S=frozenset(i for i in range(N) if mask&(1<<i))
            cnt=local_count(color,S)
            row={'subset':sorted(S),'size':len(S),'count':cnt,'rotation_orbit':list(rotcanon(S)),
                 'gaps':list(cyclic_gaps(S)),'degrees':[list(x) for x in degree_multiset(color,S)]}
            rows.append(row)
            k=str(rotcanon(S)); o=orbit_summary[k]
            o['members']+=1; o['count']=cnt; o['size']=len(S); o['gaps']=list(cyclic_gaps(S)); o['degrees']=row['degrees']
        quotients={name:quotient_report(color,rows,name) for name in names}
        exact=[name for name in names if quotients[name]['collision_count']==0]
        out['colors'][color]={
            'allowed':sorted(ALLOWED[color]),
            'feasible_sizes':sorted({r['size'] for r in rows if r['count']>0}),
            'full_block_count':next(r['count'] for r in rows if r['size']==N),
            'rotation_orbits':orbit_summary,
            'quotients':quotients,
            'coarsest_tested_exact_quotient':exact[0] if exact else None,
        }
    out['residual']=(
        'Use the coarsest collision-free A/B subset-count quotient to derive a symbolic '
        'weighted count over the 11 certified size triples.  The target is the exact 141 '
        'without enumerating the 16,146 global states.'
    )
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_AB_subset_counting_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({c:{
        'feasible_sizes':out['colors'][c]['feasible_sizes'],
        'full_block_count':out['colors'][c]['full_block_count'],
        'coarsest_tested_exact_quotient':out['colors'][c]['coarsest_tested_exact_quotient'],
        'quotient_collision_counts':{k:v['collision_count'] for k,v in out['colors'][c]['quotients'].items()},
        'rotation_orbit_count':len(out['colors'][c]['rotation_orbits']),
    } for c in ('A','B')},indent=2,sort_keys=True))
    print(out['residual'])
    print('PHASE_AB_SUBSET_COUNTING_PROBE_PASS')

if __name__=='__main__': main()
