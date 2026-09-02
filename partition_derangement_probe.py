"""Exact saturated four-row representation as three colored derangements.

Blind local classification. At total agreement 14, every column has one matching color:
A={01,23}, B={02,13}, C={03,12}. Because row 0 is identity, each color block is a subset
of the seven labels and the complementary agreeing pair defines a fixed-point-free
permutation of that same block. The partition plus three derangements determines all rows.
"""
from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

N=7
COLORS=('A','B','C')
PAIRS=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))


def derangements(block):
    block=tuple(sorted(block))
    if not block:
        return [dict()]
    out=[]
    for p in itertools.permutations(block):
        if all(x!=y for x,y in zip(block,p)):
            out.append(dict(zip(block,p)))
    return out


def rows_from(blocks,sigmas):
    rows=[[None]*N for _ in range(4)]
    rows[0]=list(range(N))
    for color in COLORS:
        for i in blocks[color]:
            s=sigmas[color][i]
            if color=='A':
                rows[1][i]=i; rows[2][i]=s; rows[3][i]=s
            elif color=='B':
                rows[2][i]=i; rows[1][i]=s; rows[3][i]=s
            else:
                rows[3][i]=i; rows[1][i]=s; rows[2][i]=s
    return tuple(tuple(r) for r in rows)


def shifted_ok(rows):
    return all(rows[u][i] != rows[t][(i+u-t)%N] for t,u in PAIRS for i in range(N))


def no_triple(rows):
    return all(max([rows[r][i] for r in range(4)].count(x) for x in set(rows[r][i] for r in range(4)))<3 for i in range(N))


def profile(rows):
    return tuple(sum(rows[a][i]==rows[b][i] for i in range(N)) for a,b in PAIRS)


def cycle_type(sigma,block):
    seen=set(); lens=[]
    for x in sorted(block):
        if x in seen: continue
        y=x; k=0
        while y not in seen:
            seen.add(y); k+=1; y=sigma[y]
        lens.append(k)
    return tuple(sorted(lens))


def enumerate_states():
    cache={}
    for mask in itertools.product(COLORS,repeat=N):
        blocks={c:tuple(i for i,x in enumerate(mask) if x==c) for c in COLORS}
        sizes=tuple(len(blocks[c]) for c in COLORS)
        if any(x==1 for x in sizes):
            continue
        ds=[]
        for c in COLORS:
            key=blocks[c]
            if key not in cache: cache[key]=derangements(key)
            ds.append(cache[key])
        for sa,sb,sc in itertools.product(*ds):
            sigmas={'A':sa,'B':sb,'C':sc}
            rows=rows_from(blocks,sigmas)
            assert all(sorted(r)==list(range(N)) for r in rows)
            assert no_triple(rows)
            assert sum(profile(rows))==14
            yield blocks,sigmas,rows


def main():
    total=0; shifted=0
    by_profile=Counter(); shifted_by_profile=Counter()
    by_size=Counter(); shifted_by_size=Counter()
    cycle_sigs=defaultdict(set); shifted_cycle_sigs=defaultdict(set)
    witnesses={}
    for blocks,sigmas,rows in enumerate_states():
        total+=1
        p=profile(rows); by_profile[p]+=1
        sizes=tuple(len(blocks[c]) for c in COLORS); by_size[sizes]+=1
        cs=tuple(cycle_type(sigmas[c],blocks[c]) for c in COLORS)
        cycle_sigs[sizes].add(cs)
        if shifted_ok(rows):
            shifted+=1; shifted_by_profile[p]+=1; shifted_by_size[sizes]+=1; shifted_cycle_sigs[sizes].add(cs)
            witnesses.setdefault(str(p),[list(r) for r in rows])
    out={
        'total_saturated_states':total,
        'shifted_saturated_states':shifted,
        'profile_counts':{str(k):v for k,v in sorted(by_profile.items())},
        'shifted_profile_counts':{str(k):v for k,v in sorted(shifted_by_profile.items())},
        'ordered_color_size_counts':{str(k):v for k,v in sorted(by_size.items())},
        'shifted_ordered_color_size_counts':{str(k):v for k,v in sorted(shifted_by_size.items())},
        'cycle_signatures_by_ordered_sizes':{str(k):[str(x) for x in sorted(v)] for k,v in sorted(cycle_sigs.items())},
        'shifted_cycle_signatures_by_ordered_sizes':{str(k):[str(x) for x in sorted(v)] for k,v in sorted(shifted_cycle_sigs.items())},
        'shifted_witnesses_by_profile':witnesses,
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/partition_derangement_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'total_saturated_states':total,
        'shifted_saturated_states':shifted,
        'shifted_profile_count':len(shifted_by_profile),
        'shifted_size_types':len(shifted_by_size),
        'shifted_cycle_signature_total':sum(len(v) for v in shifted_cycle_sigs.values()),
    },indent=2,sort_keys=True))
    if shifted==0:
        raise SystemExit('no shifted saturated state survived')

if __name__=='__main__':main()
