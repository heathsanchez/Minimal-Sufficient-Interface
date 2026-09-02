"""Use the symbolic phase theorem to classify feasible n=7 color blocks locally.

Instead of checking six global shifted row-pair constraints on four rows, enumerate only
one subset S of Z/7 and permutations sigma:S->S whose displacements lie in the legal
language for that color.  Then combine only feasible block sizes into ordered triples
summing to seven.  This measures the structural consequence of the theorem itself.
"""
from __future__ import annotations
import itertools, json
from collections import Counter, defaultdict
from pathlib import Path

N=7
COLORS=('A','B','C')
ALLOWED={
    'A':{4,5,6},
    'B':{2,4,5},
    'C':{3,4},
}


def legal_perms(S,color):
    S=tuple(sorted(S))
    out=[]
    for p in itertools.permutations(S):
        if all(x!=y and ((y-x)%N in ALLOWED[color]) for x,y in zip(S,p)):
            out.append(tuple(p))
    return out


def rotcanon(S):
    S=set(S)
    reps=[]
    for k in range(N):
        reps.append(tuple(sorted((x-k)%N for x in S)))
    return min(reps)


def main():
    local={}; feasible_sizes={}
    for c in COLORS:
        by_size=defaultdict(list); orbit_counts=Counter(); total_subsets=0; total_pairs=0
        for r in range(N+1):
            for S in itertools.combinations(range(N),r):
                ps=legal_perms(S,c)
                if ps:
                    total_subsets+=1; total_pairs+=len(ps)
                    by_size[r].append({'subset':list(S),'permutations':[list(p) for p in ps]})
                    orbit_counts[(r,rotcanon(S))]+=1
        feasible_sizes[c]=sorted(by_size)
        local[c]={
            'allowed_displacements':sorted(ALLOWED[c]),
            'feasible_sizes':sorted(by_size),
            'feasible_subset_counts_by_size':{str(k):len(v) for k,v in by_size.items()},
            'rotation_orbits_by_size':{str(k):len({rotcanon(tuple(x['subset'])) for x in v}) for k,v in by_size.items()},
            'legal_subset_count':total_subsets,
            'legal_subset_permutation_pairs':total_pairs,
        }

    triples=[]
    for a in feasible_sizes['A']:
        for b in feasible_sizes['B']:
            for c in feasible_sizes['C']:
                if a+b+c==N:
                    triples.append((a,b,c))

    # Independently count actual disjoint partitions admitting at least one local legal
    # permutation per block, without reconstructing rows or evaluating shifted pairs.
    partition_count=0; weighted_state_count=0; triple_counts=Counter()
    for mask in itertools.product(COLORS, repeat=N):
        blocks={c:tuple(i for i,x in enumerate(mask) if x==c) for c in COLORS}
        ps={c:legal_perms(blocks[c],c) for c in COLORS}
        if all(ps[c] for c in COLORS):
            partition_count+=1
            weight=1
            for c in COLORS: weight*=len(ps[c])
            weighted_state_count+=weight
            triple_counts[tuple(len(blocks[c]) for c in COLORS)]+=weight

    out={
        'n':N,'local':local,
        'feasible_ordered_size_triples':[list(x) for x in triples],
        'feasible_ordered_size_triple_count':len(triples),
        'legal_colored_partitions':partition_count,
        'legal_partition_derangement_states':weighted_state_count,
        'state_counts_by_size_triple':{str(k):v for k,v in sorted(triple_counts.items())},
        'expected_shifted_frontier_states':141,
        'reconstructs_entire_shifted_frontier':weighted_state_count==141,
        'residual':('The phase theorem factorizes the 141-state shifted frontier into three independent local constrained-permutation languages plus disjoint partitioning. Derive a non-enumerative counting/obstruction law from the feasible block languages, prioritizing the most restrictive C language.')
    }
    assert out['reconstructs_entire_shifted_frontier'], (weighted_state_count,triple_counts)
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_block_feasibility_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'feasible_sizes':feasible_sizes,
        'feasible_ordered_size_triples':out['feasible_ordered_size_triples'],
        'legal_colored_partitions':partition_count,
        'legal_partition_derangement_states':weighted_state_count,
        'state_counts_by_size_triple':out['state_counts_by_size_triple'],
        'reconstructs_entire_shifted_frontier':out['reconstructs_entire_shifted_frontier'],
        'residual':out['residual'],
    },indent=2,sort_keys=True))
    print('PHASE_BLOCK_FEASIBILITY_PROBE_PASS')

if __name__=='__main__': main()
