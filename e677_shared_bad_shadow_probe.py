"""First-order shared Bad-shadow probe for the terminal ZERO-reuse/no-HIT regime.

This is the qualitative representation change earned by repeated SAT local
mark models.  Instead of appending a third G-CROSS, every mark is embedded in
one common size-free first-order theory containing the proved Bad-shadow laws.

The theory includes:
* global E677;
* global left-row injectivity;
* Good(x) iff D(x)=x, Bad(x) iff D(x)!=x;
* the ZERO-reuse/no-HIT colour band for every Bad x;
* no row fixes a Bad input;
* Bad off-diagonal closure;
* exact unique Bad carrier for each distinct Bad input/target pair (N_B=1);
* an idempotent Latin E677 shadow operation on Bad, linked to original
  multiplication off diagonal;
* the linked two-mark shell, with ZIPPER and G-CROSS second branches tested
  independently.

Quantifiers mean Z3 may answer UNKNOWN.  SAT is not a finite counterexample;
it is only a model boundary for these first-order consequences.  UNSAT is
scoped to this terminal regime and marked branch and still requires an
attachment audit before any global E677 -> E255 claim.
"""
from __future__ import annotations

import json
from pathlib import Path
from z3 import Function, ForAll, Implies, And, Or, Not, Solver, Consts, sat, unsat, unknown

from e677_linked_two_mark_probe import U, mul, C, names, common_structural_assertions

shadow = Function('bad_shadow_o', U, U, U)
carrier = Function('bad_shadow_carrier', U, U, U)
kappa = Function('bad_kappa', U, U)


def sigma(x):
    return mul(mul(x,x),x)


def D(x):
    return mul(sigma(x),x)


def Good(x):
    return D(x) == x


def Bad(x):
    return D(x) != x


def E677(x,y):
    return x == mul(y, mul(x, mul(mul(y,x),y)))


def shadow_E677(x,y):
    return x == shadow(y, shadow(x, shadow(shadow(y,x),y)))


def global_shadow_axioms():
    x,y,z,r,u,v,a,b,c = Consts('gx gy gz gr gu gv ga gb gc', U)
    A=[]

    # Original magma consequences used by the terminal source theorem.
    A += [ForAll([x,y], E677(x,y))]
    A += [ForAll([r,a,b], Implies(mul(r,a)==mul(r,b), a==b))]
    A += [ForAll([r,u], Implies(Bad(u), mul(r,u) != u))]

    # ZERO-reuse/no-HIT band for every Bad point.
    A += [ForAll([x], Implies(Bad(x), And(
        Good(mul(x,x)),
        Good(sigma(x)),
        Good(kappa(x)),
        Bad(D(x)),
        mul(x,sigma(x)) == kappa(x),
        mul(x,kappa(x)) == x
    )))]

    # Off-diagonal Bad closure.
    A += [ForAll([r,u], Implies(And(Bad(r),Bad(u),r!=u), Bad(mul(r,u))))]

    # Exact N_B(u,v)=1 for distinct Bad u,v, Skolemized by carrier(u,v).
    A += [ForAll([u,v], Implies(And(Bad(u),Bad(v),u!=v), And(
        Bad(carrier(u,v)),
        mul(carrier(u,v),u) == v
    )))]
    A += [ForAll([r,u,v], Implies(And(Bad(r),Bad(u),Bad(v),u!=v,mul(r,u)==v),
                                      r == carrier(u,v)))]

    # Idempotent Latin Bad shadow, linked to original multiplication off diagonal.
    A += [ForAll([x], Implies(Bad(x), shadow(x,x)==x))]
    A += [ForAll([x,y], Implies(And(Bad(x),Bad(y)), Bad(shadow(x,y))))]
    A += [ForAll([x,y], Implies(And(Bad(x),Bad(y),x!=y), shadow(x,y)==mul(x,y)))]
    A += [ForAll([r,a,b], Implies(And(Bad(r),Bad(a),Bad(b),shadow(r,a)==shadow(r,b)), a==b))]
    A += [ForAll([r,a,b], Implies(And(Bad(r),Bad(a),Bad(b),shadow(a,r)==shadow(b,r)), a==b))]
    A += [ForAll([x,y], Implies(And(Bad(x),Bad(y)), shadow_E677(x,y)))]
    return A


def solve(branch: str, timeout_ms: int=60000):
    s=Solver()
    s.set(timeout=timeout_ms)
    # Use the exact marked equations/colour separation, but let the global
    # theory supply injectivity and no-fixer consequences.
    s.add(*common_structural_assertions(branch, include_injectivity=False, include_no_fixers=False))
    s.add(*global_shadow_axioms())
    return s.check(), s


def main():
    frontier=json.load(open('program_frontier.json'))
    assert frontier['authoritative']
    assert frontier['schema_version'] >= 9
    assert frontier['live_residual']['type']=='REFRAME'
    assert 'Bad shadow' in frontier['live_residual']['text']

    results={}
    for branch in ('ZIPPER','GCROSS'):
        res,s=solve(branch)
        results[branch]={
            'result':str(res),
            'reason_unknown':s.reason_unknown() if res==unknown else '',
        }

    sats=[b for b,r in results.items() if r['result']=='sat']
    unsats=[b for b,r in results.items() if r['result']=='unsat']
    unknowns=[b for b,r in results.items() if r['result']=='unknown']

    if len(unsats)==2:
        classification='PROMOTE'
        residual=('Both marked continuations are UNSAT after attachment to the full first-order Bad-shadow theory. '
                  'Ablate the shadow axioms to isolate the minimal shared invariant, then formalize that invariant symbolically before widening scope.')
    elif unknowns:
        classification='REQUIRE_ATTACHMENT'
        residual=(f'The shared Bad-shadow first-order probe is verifier-inconclusive on {unknowns}. '
                  'Do not infer mathematics from timeout/UNKNOWN. Compile a finite-model/ground consequence projection of exactly these universal axioms or switch to a proof assistant derivation of the highest-leverage shadow identity.')
    else:
        classification='PARK'
        residual=('The shared first-order Bad-shadow theory still admits the marked configuration in every tested branch. '
                  'The Bad-shadow algebra alone is insufficient; attach the simultaneous Good-row/Bad-row renewal network, preserving shared marks, rather than extending local algebra.')

    out={
        'consumed_frontier_schema':frontier['schema_version'],
        'scope':'terminal ZERO-root equality + no-HIT first-order consequences with linked marked branches; no finiteness axiom',
        'results':results,
        'sat_branches':sats,
        'unsat_branches':unsats,
        'unknown_branches':unknowns,
        'finite_model_claimed':False,
        'finite_counterexample_claimed':False,
        'global_e677_implication_claimed':False,
        'proposed_transition':{'classification':classification,'residual':residual},
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_shared_bad_shadow_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('SHARED_BAD_SHADOW_PROBE_FINISHED')

if __name__=='__main__':
    main()
