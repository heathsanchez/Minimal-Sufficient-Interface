"""Extract minimal shifted row-pair constraint cores responsible for phase exclusions.

For each tested order and each forbidden color/displacement atom, enumerate saturated
states containing that atom, record which of the six shifted pair families each state
satisfies, then find the smallest conjunction(s) of pair families that exclude the atom.
This converts the cross-order phase pattern into a sharper proof residual.
"""
from __future__ import annotations
import itertools, json
from collections import defaultdict
from pathlib import Path
from phase_cross_order_generalization_probe import COLORS, PAIRS, enumerate_states, support

PAIR_NAMES=tuple(f'{t}{u}' for t,u in PAIRS)


def pair_mask(n,rows):
    mask=0
    for k,(t,u) in enumerate(PAIRS):
        delta=u-t
        ok=all(rows[u][i] != rows[t][(i+delta)%n] for i in range(n))
        if ok: mask |= 1<<k
    return mask


def minimal_cores(masks):
    """Smallest pair subsets S such that no atom-containing state satisfies all S."""
    full=(1<<len(PAIRS))-1
    out=[]
    for size in range(1,len(PAIRS)+1):
        for inds in itertools.combinations(range(len(PAIRS)),size):
            req=sum(1<<i for i in inds)
            if all((m & req) != req for m in masks):
                out.append(tuple(PAIR_NAMES[i] for i in inds))
        if out: break
    return out


def formula_forbidden(n,c,d):
    d%=n
    sets={
        'A':{1%n,2%n,3%n},
        'B':{1%n,3%n,(-1)%n},
        'C':{1%n,2%n,(-2)%n,(-1)%n},
    }
    return d!=0 and d in sets[c]


def run_n(n):
    atom_masks=defaultdict(set); positive_atoms=set(); total=shifted=0
    allmask=(1<<len(PAIRS))-1
    for blocks,sigmas,rows in enumerate_states(n):
        total+=1; m=pair_mask(n,rows); s=support(n,blocks,sigmas)
        if m==allmask:
            shifted+=1; positive_atoms |= set(s)
        for atom in s: atom_masks[atom].add(m)
    universe={(c,d) for c in COLORS for d in range(1,n)}
    empirical_forbidden=universe-positive_atoms
    formula={atom for atom in universe if formula_forbidden(n,*atom)}
    assert empirical_forbidden==formula, (n,empirical_forbidden,formula)
    cores={}
    for atom in sorted(empirical_forbidden):
        cs=minimal_cores(atom_masks[atom])
        assert cs, (n,atom)
        cores[f'{atom[0]}:{atom[1]}']=[list(x) for x in cs]
    return {
        'n':n,'total_states':total,'shifted_states':shifted,
        'formula_matches_empirical':True,
        'forbidden_formula':{
            'A':['+1','+2','+3'],
            'B':['+1','+3','-1'],
            'C':['+1','+2','-2','-1'],
        },
        'minimal_pair_cores':cores,
    }


def main():
    rows=[run_n(n) for n in range(3,9)]
    # Compare stable core families for each symbolic atom across nondegenerate n>=6.
    symbolic={
        'A:+1':lambda n:'A:1','A:+2':lambda n:'A:2','A:+3':lambda n:'A:3',
        'B:+1':lambda n:'B:1','B:+3':lambda n:'B:3','B:-1':lambda n:f'B:{n-1}',
        'C:+1':lambda n:'C:1','C:+2':lambda n:'C:2','C:-2':lambda n:f'C:{n-2}','C:-1':lambda n:f'C:{n-1}',
    }
    stable={}
    for label,keyfn in symbolic.items():
        core_sets=[]
        for row in rows:
            n=row['n']
            if n<6: continue
            core_sets.append(tuple(tuple(x) for x in row['minimal_pair_cores'][keyfn(n)]))
        stable[label]={'same_minimal_cores_n6_to_n8':len(set(core_sets))==1,'cores':core_sets[0] if core_sets else ()}
    out={
        'orders':rows,
        'stable_symbolic_cores':stable,
        'all_formula_matches':all(r['formula_matches_empirical'] for r in rows),
        'all_symbolic_cores_stable_n6_to_n8':all(v['same_minimal_cores_n6_to_n8'] for v in stable.values()),
        'residual':'Use the stable minimal row-pair cores to derive each modular displacement exclusion locally; then prove their conjunction is equivalent to all six shifted pair constraints for saturated partition-derangement states.'
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_pair_responsibility_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'all_formula_matches':out['all_formula_matches'],'all_symbolic_cores_stable_n6_to_n8':out['all_symbolic_cores_stable_n6_to_n8'],'stable_symbolic_cores':stable,'residual':out['residual']},indent=2,sort_keys=True))
    print('PHASE_PAIR_RESPONSIBILITY_PROBE_PASS')

if __name__=='__main__': main()
