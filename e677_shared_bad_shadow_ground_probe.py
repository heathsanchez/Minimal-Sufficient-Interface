"""Quantifier-free ground projection of the shared Bad-shadow theory.

This is the verifier-language repair after the universal first-order encoding
returned UNKNOWN by timeout on both marked branches.  It changes no source
law: each universal law is instantiated only over the already named linked
two-mark fragment.  The result is QF_UF and therefore a decidable consequence
probe.

SAT means only that this ground projection is insufficient.  UNSAT is scoped
to the named projection and must be causally minimized before promotion.
"""
from __future__ import annotations
import json
from pathlib import Path
from z3 import Function, Solver, Implies, And, sat, unsat
from e677_linked_two_mark_probe import U, mul, C, names, BAD_NAMES, common_structural_assertions

shadow = Function('ground_bad_shadow', U, U, U)
carrier = Function('ground_bad_carrier', U, U, U)
kappa = Function('ground_bad_kappa', U, U)
BAD=[C[n] for n in BAD_NAMES]
ALL=[C[n] for n in names]

def sigma(x): return mul(mul(x,x),x)
def D(x): return mul(sigma(x),x)
def Bad(x): return D(x) != x
def Good(x): return D(x) == x
def e677(x,y): return x == mul(y,mul(x,mul(mul(y,x),y)))
def shadow_e677(x,y): return x == shadow(y,shadow(x,shadow(shadow(y,x),y)))

def add_ground_shared(s: Solver):
    # Original E677 and left-row injectivity on the named fragment.
    for x in ALL:
        for y in ALL: s.add(e677(x,y))
    for r in ALL:
        for i,a in enumerate(ALL):
            for b in ALL[i+1:]: s.add(Implies(mul(r,a)==mul(r,b),a==b))

    # ZERO-reuse/no-HIT band and no-fixer law on every named Bad input.
    for x in BAD:
        s.add(Bad(x))
        s.add(Good(mul(x,x)), Good(sigma(x)), Good(kappa(x)), Bad(D(x)))
        s.add(mul(x,sigma(x))==kappa(x), mul(x,kappa(x))==x)
        for r in ALL: s.add(mul(r,x) != x)

    # Shared off-diagonal Bad carrier law N_B(u,v)=1, ground-projected.
    for u in BAD:
        for v in BAD:
            cond=u!=v
            s.add(Implies(cond, Bad(mul(u,v))))
            c=carrier(u,v)
            s.add(Implies(cond, And(Bad(c),mul(c,u)==v)))
            for r in BAD:
                s.add(Implies(And(cond,mul(r,u)==v),r==c))

    # Idempotent Latin E677 shadow on the named Bad fragment.
    for x in BAD:
        s.add(shadow(x,x)==x)
        for y in BAD:
            s.add(Bad(shadow(x,y)))
            s.add(Implies(x!=y,shadow(x,y)==mul(x,y)))
            s.add(shadow_e677(x,y))
    for r in BAD:
        for a in BAD:
            for b in BAD:
                s.add(Implies(shadow(r,a)==shadow(r,b),a==b))
                s.add(Implies(shadow(a,r)==shadow(b,r),a==b))

def solve(branch: str):
    s=Solver()
    s.add(*common_structural_assertions(branch,include_injectivity=False,include_no_fixers=False))
    add_ground_shared(s)
    return s.check(),s

def main():
    f=json.load(open('program_frontier.json'))
    assert f['authoritative'] and f['schema_version']>=10
    assert f['live_residual']['type']=='REFRAME'
    assert 'ground' in f['live_residual']['text'].lower()
    results={}
    for branch in ('ZIPPER','GCROSS'):
        r,_=solve(branch); results[branch]=str(r)
    sats=[b for b,r in results.items() if r=='sat']; unsats=[b for b,r in results.items() if r=='unsat']
    if len(unsats)==2:
        cls='PROMOTE'; residual=('Both branches are UNSAT in the decidable ground projection of the shared Bad-shadow laws. Causally ablate axiom families and minimize the named core before symbolic promotion.')
    elif len(unsats)==1:
        cls='PROMOTE'; residual=(f'The ground shared-shadow projection excludes {unsats[0]} but leaves {sats[0]}. Minimize the excluded branch and route through the surviving branch.')
    else:
        cls='PARK'; residual=('Both branches remain SAT in the decidable ground projection of the shared Bad-shadow laws. The shared shadow at this ground locality is insufficient; attach the simultaneous Good-row/Bad-row renewal network with shared marks rather than adding local algebra.')
    out={'consumed_frontier_schema':f['schema_version'],'scope':'QF_UF ground projection of shared Bad-shadow laws over the 19 named linked-two-mark elements','results':results,'ground_e677_instances':len(ALL)**2,'named_bad_inputs':len(BAD),'finite_model_claimed':False,'counterexample_claimed':False,'global_e677_implication_claimed':False,'proposed_transition':{'classification':cls,'residual':residual}}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_shared_bad_shadow_ground_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True)); print('SHARED_BAD_SHADOW_GROUND_PROBE_VERIFIED')
if __name__=='__main__': main()
