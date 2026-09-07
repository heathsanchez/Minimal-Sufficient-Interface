"""Exact symbolic phase law for the live seven-row T6 relative-permutation frontier.

For permutation rows U_t on Z/n, define sigma_tu = U_u^{-1} o U_t.
The shifted-row inequality
    U_t(T-t) != U_u(T-u) for every T
is equivalent to the unary relative-phase exclusion
    sigma_tu(x)-x != t-u (mod n) for every x.

Moreover, an agreement edge {t,u} at target s, meaning
    U_t^{-1}(s)=U_u^{-1}(s),
is exactly a fixed point of sigma_tu, with s=U_t(x)=U_u(x).
Thus the colored matching frontier is a fixed-point statistic of a cocycle of
relative permutations subject to pair-specific forbidden nonzero phases.
"""
from __future__ import annotations

import itertools, json
from pathlib import Path


def inv(p):
    q=[None]*len(p)
    for i,v in enumerate(p): q[v]=i
    return tuple(q)


def compose(p,q):
    return tuple(p[q[x]] for x in range(len(p)))


def sigma(Ut,Uu):
    return compose(inv(Uu),Ut)


def shifted_pair_ok(Ut,Uu,t,u):
    n=len(Ut)
    return all(Ut[(T-t)%n] != Uu[(T-u)%n] for T in range(n))


def phase_pair_ok(Ut,Uu,t,u):
    n=len(Ut); s=sigma(Ut,Uu); forbidden=(t-u)%n
    return all((s[x]-x)%n != forbidden for x in range(n))


def agreement_targets(Ut,Uu):
    it,iu=inv(Ut),inv(Uu)
    return {s for s in range(len(Ut)) if it[s]==iu[s]}


def fixed_points(p):
    return {x for x,v in enumerate(p) if x==v}


def symbolic_derivation():
    return {
        'forward': [
            'write x=T-t, so T-u=x+(t-u)',
            'a shifted equality is U_t(x)=U_u(x+(t-u))',
            'apply U_u^{-1}: sigma_tu(x)=x+(t-u)',
            'therefore shifted inequality for every T is exactly exclusion of displacement t-u for sigma_tu',
        ],
        'agreement_edge': [
            'U_t^{-1}(s)=U_u^{-1}(s)=x iff U_t(x)=U_u(x)=s',
            'applying U_u^{-1} gives sigma_tu(x)=x',
            'hence colored agreement targets are in bijection with fixed points of sigma_tu',
        ],
        'cocycle': 'sigma_tv = sigma_uv o sigma_tu because U_v^{-1}U_t=(U_v^{-1}U_u)(U_u^{-1}U_t)',
    }


def finite_replay():
    # Exhaustive small-order replay is independent of the symbolic algebra.  n<=5
    # is enough to catch sign/order mistakes while keeping CI tiny.
    checked=0
    for n in range(2,6):
        perms=list(itertools.permutations(range(n)))
        for Ut in perms:
            for Uu in perms:
                for t in range(n):
                    for u in range(n):
                        if t==u: continue
                        assert shifted_pair_ok(Ut,Uu,t,u)==phase_pair_ok(Ut,Uu,t,u)
                        sgm=sigma(Ut,Uu)
                        assert len(agreement_targets(Ut,Uu))==len(fixed_points(sgm))
                        # stronger pointwise correspondence s <-> x
                        it=inv(Ut); iu=inv(Uu)
                        for s in range(n):
                            assert (it[s]==iu[s]) == (sgm[it[s]]==it[s])
                        checked+=1
    return checked


def main():
    attachment=json.load(open('artifacts/e677_live_frontier_attachment_probe.json'))
    assert attachment['mechanism_attachment_verified']
    checked=finite_replay()
    out={
        'theorem': 'For every n>=2 and t!=u, shifted pair-Latin inequality U_t(T-t)!=U_u(T-u) for all T iff relative permutation sigma_tu=U_u^{-1}oU_t avoids displacement t-u at every x.',
        'agreement_corollary': 'For each target s, {t,u} is an agreement edge iff sigma_tu has the corresponding fixed point x=U_t^{-1}(s); edge multiplicity across targets equals |Fix(sigma_tu)|.',
        'triangle_cocycle': 'sigma_tv = sigma_uv o sigma_tu',
        'symbolic_derivation': symbolic_derivation(),
        'finite_replay_pair_cases': checked,
        'direct_live_phase_attachment_verified': True,
        'old_four_row_block_assumptions_required': False,
        'residual': ('Join the pair-specific forbidden phases, fixed-point edge multiplicities, and triangle cocycle. '
                     'Derive the smallest invariant of the 21 relative permutations that restricts the fourteen-edge '
                     'uniform matching multigraph beyond uncolored degrees/profiles; test the two affine triangle types '
                     '{0,1,2} and {0,1,3} first, then lift any separator globally.'),
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/t6_relative_phase_theorem_certificate.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('T6_RELATIVE_PHASE_THEOREM_PASS')


if __name__=='__main__': main()
