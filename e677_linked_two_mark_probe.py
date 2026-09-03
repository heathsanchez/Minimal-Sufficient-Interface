"""Exact linked two-mark consequence probe for the size-free ZERO-reuse residual.

The first mark is the already-tested FORK -> G-CROSS configuration at q.
Because h=H(q) is Bad, the same proved ZERO-reuse consequences apply at h.
The second canonical companion has exactly the proved ZIPPER/G-CROSS dichotomy,
so both branches are tested independently.

Multiplication remains an uninterpreted binary function.  We encode only:
- source-backed colour bands for x, q, h;
- first FORK context D(x)*q=x with D(q)!=x;
- the first G-CROSS at q;
- the canonical mixed collision at h;
- either ZIPPER or G-CROSS at h;
- named left-row injectivity;
- the proved no-Bad-fixer law on all named rows and named Bad inputs;
- every ground E677 instance on the named fragment.

SAT is only a negative boundary on this local consequence language, never a
finite magma/counterexample.  UNSAT is scoped to the selected second branch
and must be minimized/ablated before symbolic promotion.
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from z3 import Const, DeclareSort, Function, Solver, Implies, sat, unsat

U = DeclareSort('U2')
mul = Function('mul2', U, U, U)

# x -> first FORK input q -> H(q)=h -> second companion H(h)=j
names = [
    'x','d','q','e','h','rq','zq','sx','sigx','sq','tq','kq',
    'sh','th','kh','f','j','rh','zh'
]
C = {n: Const(n, U) for n in names}
BAD_NAMES = ['x','d','q','e','h','rq','f','j','rh']
GOOD_BASE_NAMES = ['sx','sigx','sq','tq','kq','zq','sh','th','kh']
BAD = [C[n] for n in BAD_NAMES]


def e677(a,b):
    return a == mul(b, mul(a, mul(mul(b,a), b)))


def common_structural_assertions(second_branch: str, include_injectivity: bool=True,
                                 include_no_fixers: bool=True):
    assert second_branch in {'ZIPPER','GCROSS'}
    x,d,q,e,h,rq,zq,sx,sigx,sq,tq,kq,sh,th,kh,f,j,rh,zh = (C[n] for n in names)
    A=[]

    good_names=list(GOOD_BASE_NAMES)
    if second_branch == 'GCROSS':
        good_names.append('zh')
    good=[C[n] for n in good_names]

    # Colour separation only: no same-colour name distinctness is assumed.
    for b in BAD:
        for g in good:
            A.append(b != g)

    # D-bands from the proved ZERO-reuse colour band.
    A += [mul(x,x)==sx, mul(sx,x)==sigx, mul(sigx,x)==d]
    A += [mul(q,q)==sq, mul(sq,q)==tq, mul(q,tq)==kq, mul(q,kq)==q, mul(tq,q)==e]
    A += [mul(h,h)==sh, mul(sh,h)==th, mul(h,th)==kh, mul(h,kh)==h, mul(th,h)==f]

    # Badness/no-HIT on the named D-images.
    A += [d != x, e != q, f != h]

    # First FORK: q=H(x), D(x)*q=x, while D(q) points elsewhere.
    A += [mul(d,q)==x, e != x]

    # First canonical mixed collision and the already-selected G-CROSS at q.
    # e=D(q), h=H(q)=e\q, tq=sigma(q), rq is the unique Bad carrier.
    A += [mul(e,h)==q, mul(rq,q)==e, mul(tq,q)==e]
    A += [mul(tq,e)==zq, mul(zq,tq)==h, mul(mul(rq,e),rq)==h]

    # Second canonical mixed collision at h. j=H(h)=f\h.
    A += [mul(f,j)==h, mul(rh,h)==f, mul(th,h)==f, mul(mul(rh,f),rh)==j]

    if second_branch == 'GCROSS':
        # zh=th*f is Good and zh*th=j is the second marked G-CROSS.
        A += [mul(th,f)==zh, mul(zh,th)==j]
    else:
        # C5 ZIPPER at h: z=th*f=j and th=kappa(j), hence j*th=j.
        # We use the latter defining cell directly; no anonymous kj is invented.
        A += [mul(th,f)==j, mul(j,th)==j]

    if include_injectivity:
        vals=[C[n] for n in names]
        for row in vals:
            for i,a in enumerate(vals):
                for b in vals[i+1:]:
                    A.append(Implies(mul(row,a)==mul(row,b), a==b))

    if include_no_fixers:
        # If u is Bad, no row fixes input u. Instantiate only named rows.
        for row_name in names:
            row=C[row_name]
            for u in BAD:
                A.append(mul(row,u) != u)

    return A


def solve(branch: str, *, add_e677: bool, include_injectivity: bool=True,
          include_no_fixers: bool=True):
    s=Solver()
    s.add(*common_structural_assertions(branch, include_injectivity, include_no_fixers))
    if add_e677:
        for a,b in product(names,names):
            s.add(e677(C[a],C[b]))
    return s.check(), s


def main():
    frontier=json.load(open('program_frontier.json'))
    assert frontier['authoritative']
    assert frontier['schema_version'] >= 8
    assert frontier['live_residual']['type']=='REFRAME'
    assert 'linked two-mark' in frontier['live_residual']['text']

    results={}
    for branch in ['ZIPPER','GCROSS']:
        shell,_=solve(branch,add_e677=False)
        assert shell==sat, f'{branch} structural shell must be consistent before E677'
        mixed,_=solve(branch,add_e677=True)
        noinj,_=solve(branch,add_e677=True,include_injectivity=False)
        nofix,_=solve(branch,add_e677=True,include_no_fixers=False)
        results[branch]={
            'shell':str(shell),
            'mixed':str(mixed),
            'without_injectivity':str(noinj),
            'without_no_fixer':str(nofix),
        }

    surviving=[b for b,r in results.items() if r['mixed']=='sat']
    excluded=[b for b,r in results.items() if r['mixed']=='unsat']

    if not surviving:
        classification='PROMOTE'
        residual=('Both source-backed second-mark continuations, ZIPPER and G-CROSS, are UNSAT in the linked two-mark ground consequence model. '
                  'Minimize E677/structural cores branch-by-branch and derive a symbolic two-mark obstruction before any wider claim.')
    elif len(surviving)==1:
        classification='PROMOTE'
        residual=(f'The linked two-mark model excludes {excluded[0]} but admits {surviving[0]}. '
                  f'Treat {excluded[0]} as a scoped branch obstruction after causal minimization, and route the live proof through the forced {surviving[0]} continuation rather than widening blindly.')
    else:
        classification='PARK'
        residual=('Both ZIPPER and G-CROSS second-mark branches remain SAT after all named ground E677 instances, left-row injectivity, and named no-Bad-fixer constraints. '
                  'Two isolated linked marks are insufficient. Stop adding local marks; next encode a shared Bad-shadow/renewal invariant (Latin Bad shadow/off-diagonal multiplicity or simultaneous renewal network) that couples multiple q globally.')

    out={
        'consumed_frontier_schema':frontier['schema_version'],
        'scope':'linked q -> H(q)=h two-mark partial uninterpreted model; second ZIPPER/GCROSS branches tested separately',
        'named_elements':len(names),
        'named_bad_inputs':len(BAD_NAMES),
        'ground_e677_pair_count':len(names)**2,
        'no_fixer_instance_count':len(names)*len(BAD_NAMES),
        'results':results,
        'surviving_branches':surviving,
        'excluded_branches':excluded,
        'finite_magma_claimed':False,
        'counterexample_claimed':False,
        'global_e677_implication_claimed':False,
        'proposed_transition':{'classification':classification,'residual':residual},
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_linked_two_mark_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('LINKED_TWO_MARK_PROBE_VERIFIED')

if __name__=='__main__':
    main()
