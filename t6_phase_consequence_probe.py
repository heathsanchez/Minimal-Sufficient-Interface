"""Read consequences of the verified live T6 relative-phase theorem.

Three gates are intentionally separated:
1. exact triangle fixed-count classification under phase+cocycle+matching;
2. Latin phase-balance law in the published uniform-profile seed;
3. the minimal edge-transport coordinate that attaches a fixed point to T6 rho equality.

The goal is to reject low-leverage summaries early and retain only the coordinate that
actually predicts pair-kernel success/failure.
"""
from __future__ import annotations
import itertools, json
from collections import Counter
from pathlib import Path

N=7
FIX_COUNTS=(0,1,2,3,4,5,7)


def inv(p):
    q=[0]*N
    for i,v in enumerate(p): q[v]=i
    return tuple(q)

def comp(p,q): return tuple(p[q[x]] for x in range(N))
def fix(p): return frozenset(i for i,v in enumerate(p) if i==v)
def avoids(p,d): return all((p[i]-i)%N != d%N for i in range(N))


def triangle_patterns(vertices):
    t,u,v=vertices
    da,db,dc=(t-u)%N,(u-v)%N,(t-v)%N
    perms=list(itertools.permutations(range(N)))
    left=[p for p in perms if avoids(p,da)]
    right=[p for p in perms if avoids(p,db)]
    patterns=Counter(); states=0
    for a in left:
        fa=fix(a)
        for b in right:
            c=comp(b,a)
            if not avoids(c,dc): continue
            fb,fc=fix(b),fix(c)
            # Uniform target profiles are matchings: a target cannot contain two
            # adjacent edges, which is exactly pairwise-disjoint fixed locations.
            if fa&fb or fa&fc or fb&fc: continue
            patterns[(len(fa),len(fb),len(fc))]+=1; states+=1
    compatible={x for x in itertools.product(FIX_COUNTS,repeat=3) if sum(x)<=N}
    missing=sorted(compatible-set(patterns))
    return {
        'vertices':list(vertices),'forbidden_phases':[da,db,dc],
        'realizable_count_patterns':len(patterns),'realizable_states':states,
        'matching_compatible_count_patterns':len(compatible),
        'missing_count_patterns':[list(x) for x in missing],
        'all_total_at_most_6_realizable':all(x in patterns for x in compatible if sum(x)<=6),
    }


def parse(s): return tuple(map(int,s))

# Published best uniform-profile seed from the external T6 matching boundary.
D=parse('0125634'); A=parse('0342651')
U=[parse(x) for x in ('4501326','2104635','4325016','6045312','6120435','3460521','1236450')]


def z_matrix():
    ii=[inv(p) for p in U]
    return [[ii[t][s] for t in range(N)] for s in range(N)]

def rho(s,t):
    q=U[t][s]
    return (D[(q-t)%N]-A[q])%N

def g(t,x):
    # On an agreement edge x is a common fixed location for the relative pair,
    # s=U_t(x), and rho_s(t) becomes this second-iterate observable.
    y=U[t][U[t][x]]
    return (D[(y-t)%N]-A[y])%N


def phase_balance_and_transport():
    Z=z_matrix()
    # For fixed row t, s -> z_s(t)=U_t^{-1}(s) is itself a permutation.
    rows_are_perms=all(sorted(Z[s][t] for s in range(N))==list(range(N)) for t in range(N))
    duplicate=Counter(); missing=Counter(); edge_rows=[]
    for s in range(N):
        counts=Counter(Z[s])
        assert sorted(counts.values(),reverse=True)==[2,2,1,1,1]
        for d,c in counts.items():
            if c==2: duplicate[d]+=1
        for d in range(N):
            if counts[d]==0: missing[d]+=1
        for t in range(N):
            for u in range(t+1,N):
                if Z[s][t]!=Z[s][u]: continue
                x=Z[s][t]
                # z equality means U_t(x)=U_u(x)=s.
                assert U[t][x]==s and U[u][x]==s
                rho_equal=rho(s,t)==rho(s,u)
                transport_equal=g(t,x)==g(u,x)
                assert rho_equal==transport_equal
                edge_rows.append({'target':s,'pair':[t,u],'phase':x,'rho_equal':rho_equal,'edge_transport_equal':transport_equal})
    assert rows_are_perms
    assert duplicate==missing
    matched=sum(e['rho_equal'] for e in edge_rows)
    return {
        'rows_of_phase_matrix_are_permutations':rows_are_perms,
        'duplicate_phase_counts':dict(sorted(duplicate.items())),
        'missing_phase_counts':dict(sorted(missing.items())),
        'duplicate_missing_balance_exact':duplicate==missing,
        'uniform_z_edges':len(edge_rows),
        'rho_matched_edges':matched,
        'rho_failed_edges':len(edge_rows)-matched,
        'edge_transport_equivalent_to_rho_on_z_edges':True,
        'edges':edge_rows,
    }


def main():
    theorem=json.load(open('artifacts/t6_relative_phase_theorem_certificate.json'))
    assert theorem['direct_live_phase_attachment_verified']
    tri012=triangle_patterns((0,1,2)); tri013=triangle_patterns((0,1,3))
    assert tri012['all_total_at_most_6_realizable'] and tri013['all_total_at_most_6_realizable']
    assert tri012['missing_count_patterns']==tri013['missing_count_patterns']
    consequence=phase_balance_and_transport()
    out={
        'triangle_types':[tri012,tri013],
        'fixed_count_verdict':'LOW_LEVERAGE: all matching-compatible fixed-count triples of total <=6 are realizable for both affine triangle types.',
        'phase_balance':consequence,
        'retained_coordinate':('EdgeTransport G_t(x)=D(U_t(U_t(x))-t)-A(U_t(U_t(x)); on a z-agreement edge '
                               'with common phase x, exact T6 requires G_t(x)=G_u(x).'),
        'residual':('Classify phase-labelled agreement edges by the pair (x, G_t(x)) and use triangle cocycle plus the '
                    'Latin phase-matrix row-permutation law to derive a compatibility condition across the fourteen '
                    'uniform edges. Fixed-point counts and uncolored graph degrees are now certified too weak; do not '
                    'return to them. Test whether edge-transport labels force a repeated contradiction before adding '
                    'any richer magma state.'),
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/t6_phase_consequence_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'triangle_012':tri012,'triangle_013':tri013,
        'phase_balance_exact':consequence['duplicate_missing_balance_exact'],
        'uniform_z_edges':consequence['uniform_z_edges'],
        'rho_matched_edges':consequence['rho_matched_edges'],
        'rho_failed_edges':consequence['rho_failed_edges'],
        'retained_coordinate':out['retained_coordinate'],'residual':out['residual']
    },indent=2,sort_keys=True))
    print('T6_PHASE_CONSEQUENCE_PROBE_PASS')

if __name__=='__main__': main()
