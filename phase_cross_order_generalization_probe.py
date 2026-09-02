"""Cross-order exact test of the saturated phase law for n=3..8.

For each n we independently enumerate all ordered three-color partitions and block
derangements, reconstruct the four rows, evaluate shifted constraints, derive all unary
phase atoms absent from positives, and test whether avoiding exactly those atoms is
necessary and sufficient. This is a generalization probe, not a proof for arbitrary n.
"""
from __future__ import annotations
import itertools, json
from collections import Counter
from pathlib import Path

COLORS=('A','B','C')
PAIRS=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))


def derangements(block):
    block=tuple(sorted(block))
    if not block: return [dict()]
    return [dict(zip(block,p)) for p in itertools.permutations(block) if all(x!=y for x,y in zip(block,p))]


def rows_from(n,blocks,sigmas):
    rows=[[None]*n for _ in range(4)]; rows[0]=list(range(n))
    for c in COLORS:
        for i in blocks[c]:
            s=sigmas[c][i]
            if c=='A': rows[1][i]=i; rows[2][i]=s; rows[3][i]=s
            elif c=='B': rows[2][i]=i; rows[1][i]=s; rows[3][i]=s
            else: rows[3][i]=i; rows[1][i]=s; rows[2][i]=s
    return tuple(tuple(r) for r in rows)


def shifted_ok(n,rows):
    return all(rows[u][i] != rows[t][(i+u-t)%n] for t,u in PAIRS for i in range(n))


def enumerate_states(n):
    cache={}
    for mask in itertools.product(COLORS,repeat=n):
        blocks={c:tuple(i for i,x in enumerate(mask) if x==c) for c in COLORS}
        ds=[]
        dead=False
        for c in COLORS:
            b=blocks[c]
            if b not in cache: cache[b]=derangements(b)
            if not cache[b]: dead=True; break
            ds.append(cache[b])
        if dead: continue
        for sa,sb,sc in itertools.product(*ds):
            sigmas={'A':sa,'B':sb,'C':sc}; rows=rows_from(n,blocks,sigmas)
            yield blocks,sigmas,rows


def support(n,blocks,sigmas):
    return frozenset((c,(sigmas[c][i]-i)%n) for c in COLORS for i in blocks[c])


def run_n(n):
    states=[]; positive_atoms=set(); total=pos=0
    for blocks,sigmas,rows in enumerate_states(n):
        s=support(n,blocks,sigmas); y=shifted_ok(n,rows)
        total+=1; pos+=int(y); states.append((s,y))
        if y: positive_atoms |= set(s)
    universe={(c,d) for c in COLORS for d in range(1,n)}
    forbidden=universe-positive_atoms
    fp=fn=0
    for s,y in states:
        pred=s.isdisjoint(forbidden)
        fp+=int(pred and not y); fn+=int(y and not pred)
    ablations={}
    for atom in sorted(forbidden):
        reduced=forbidden-{atom}
        afp=sum(s.isdisjoint(reduced) and not y for s,y in states)
        ablations[f'{atom[0]}:{atom[1]}']=afp
    return {
        'n':n,'total_states':total,'shifted_states':pos,
        'forbidden_atoms':[list(x) for x in sorted(forbidden)],
        'allowed':{c:[d for d in range(1,n) if (c,d) not in forbidden] for c in COLORS},
        'unary_exact':fp==0 and fn==0,'false_positives':fp,'false_negatives':fn,
        'unary_irredundant':bool(forbidden) and all(v>0 for v in ablations.values()),
        'ablation_false_positives':ablations,
    }


def main():
    results=[run_n(n) for n in range(3,9)]
    exact=[r['n'] for r in results if r['unary_exact']]
    out={'orders':results,'unary_exact_orders':exact,'all_tested_exact':len(exact)==len(results)}
    # Look for a simple order-independent description in terms of signed shifts.
    # Keep raw exact data primary; pattern inference is explicitly labeled candidate only.
    out['candidate_pattern']='Compare allowed displacement sets against complements of row-index shift differences; no arbitrary-n claim is made by this probe.'
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_cross_order_generalization_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('PHASE_CROSS_ORDER_GENERALIZATION_PROBE_PASS')

if __name__=='__main__': main()
