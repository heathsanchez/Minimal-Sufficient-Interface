"""Exact pair-local quotient for the live T6 EdgeTransport coordinate.

We classify whether one z-agreement edge can satisfy the T6 transport equality for
canonical D, every normalized A (A(0)=0), every row pair, and every agreement phase.
The search is exact but avoids magma variables and avoids 5040^2 raw row-pair search:
it factors a pair into a legal relative permutation sigma=U_u^{-1}U_t and a second
row U_u, then caches only the local values needed by EdgeTransport.
"""
from __future__ import annotations
import itertools, json
from collections import defaultdict, Counter
from pathlib import Path

N=7
CANONICAL_D=('0125634','0145236','1023546','1024356')

def parse(s): return tuple(map(int,s))
Ds=[parse(s) for s in CANONICAL_D]
PERMS=list(itertools.permutations(range(N)))
AS=[p for p in PERMS if p[0]==0]

def inv(p):
    q=[0]*N
    for i,v in enumerate(p): q[v]=i
    return tuple(q)

def legal_sigma(p,d): return all((p[x]-x)%N != d%N for x in range(N))
def F(D,A,t,q): return (D[(q-t)%N]-A[q])%N

# Cache possible (a,b)=(U(r),U(s)) for a partial local signature under
# U(x)=s, U(0)!=0, and U(k)!=0.  The second condition U(k)!=0 is exactly
# Badness of U_t(0)=U_u(sigma(0)) when k=sigma(0).
def build_u_cache():
    cache=defaultdict(set)
    for U in PERMS:
        if U[0]==0: continue
        for x in range(N):
            s=U[x]
            for r in range(N):
                a=U[r]; b=U[s]
                for k in range(N):
                    if U[k]==0: continue
                    cache[(x,s,r,k)].add((a,b))
    return cache


def pair_local_signatures(d,cache):
    # signature (x,s,a,b), where x is an agreement phase and s the agreement target.
    out=set(); sigma_count=0
    for sig in PERMS:
        if not legal_sigma(sig,d): continue
        sigma_count+=1
        k=sig[0]
        for x in range(N):
            if sig[x]!=x: continue
            for s in range(N):
                r=sig[s]
                for a,b in cache.get((x,s,r,k),()):
                    out.add((x,s,a,b))
    return out,sigma_count


def main():
    prior=json.load(open('artifacts/t6_phase_consequence_probe.json'))
    assert 'EdgeTransport' in prior['retained_coordinate']
    cache=build_u_cache()
    by_offset={}
    for d in range(1,N):
        sigs,nlegal=pair_local_signatures(d,cache)
        by_offset[d]={'signatures':sigs,'legal_relative_permutations':nlegal}

    rows=[]; impossible_cases=[]; phase_missing_cases=[]
    global_counts=Counter()
    for di,D in enumerate(Ds):
        for ai,A in enumerate(AS):
            for t in range(N):
                for u in range(t+1,N):
                    d=(t-u)%N
                    sigs=by_offset[d]['signatures']
                    good=[z for z in sigs if F(D,A,t,z[2])==F(D,A,u,z[3])]
                    phases=sorted({z[0] for z in good})
                    targets=sorted({z[1] for z in good})
                    rec={'D':CANONICAL_D[di],'A_index':ai,'t':t,'u':u,'offset':d,
                         'candidate_signatures':len(sigs),'transport_good_signatures':len(good),
                         'good_phases':phases,'good_targets':targets}
                    rows.append(rec)
                    global_counts[(CANONICAL_D[di],d,'cases')]+=1
                    if good:
                        global_counts[(CANONICAL_D[di],d,'viable')]+=1
                    else:
                        impossible_cases.append(rec)
                    if len(phases)<N:
                        phase_missing_cases.append(rec)

    # Summaries by canonical D and pair offset.
    summaries={}
    for D in CANONICAL_D:
        for d in range(1,N):
            subset=[r for r in rows if r['D']==D and r['offset']==d]
            summaries[f'{D}:d{d}']={
                'cases':len(subset),
                'impossible':sum(r['transport_good_signatures']==0 for r in subset),
                'all_7_phases_viable':sum(len(r['good_phases'])==N for r in subset),
                'min_good_phase_count':min(len(r['good_phases']) for r in subset),
                'max_good_phase_count':max(len(r['good_phases']) for r in subset),
                'min_transport_good_signatures':min(r['transport_good_signatures'] for r in subset),
            }

    out={
        'canonical_D':list(CANONICAL_D),
        'normalized_A_count':len(AS),
        'row_pair_cases':len(rows),
        'legal_relative_permutations_by_offset':{str(d):by_offset[d]['legal_relative_permutations'] for d in by_offset},
        'local_signature_counts_by_offset':{str(d):len(by_offset[d]['signatures']) for d in by_offset},
        'impossible_pair_cases':len(impossible_cases),
        'phase_restricted_pair_cases':len(phase_missing_cases),
        'summaries':summaries,
        'pair_local_verdict':('OBSTRUCTION' if impossible_cases else ('PHASE_RESTRICTION' if phase_missing_cases else 'PERMISSIVE')),
        'residual': '',
    }
    if impossible_cases:
        out['residual']=('Exploit the exact pair-local EdgeTransport exclusions: quotient impossible (D,A,row-pair) types, '
                         'then impose triangle cocycle to test whether any normalized A can support all 21 row pairs and fourteen uniform edges.')
    elif phase_missing_cases:
        out['residual']=('Pair-local EdgeTransport never kills a whole row pair but restricts agreement phases in some cases. '
                         'Compile the allowed phase sets into triangle constraints and impose sigma_tv=sigma_uv o sigma_tu; '
                         'test whether the 35 row triangles admit a globally consistent fourteen-edge uniform matching.')
    else:
        out['residual']=('Pair-local EdgeTransport is fully permissive across canonical D, normalized A, row pairs, and phases. '
                         'Retire pair-local classification. Move directly to triangle compatibility of phase-labelled transport edges '
                         'under the relative-permutation cocycle, retaining shared A,D but no richer magma state.')

    Path('artifacts').mkdir(exist_ok=True)
    # Keep full rows out of artifact unless needed; summaries are the retained consequence.
    Path('artifacts/t6_pair_transport_quotient_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:out[k] for k in ('normalized_A_count','row_pair_cases','legal_relative_permutations_by_offset','local_signature_counts_by_offset','impossible_pair_cases','phase_restricted_pair_cases','pair_local_verdict','residual')},indent=2,sort_keys=True))
    print('T6_PAIR_TRANSPORT_QUOTIENT_PROBE_PASS')

if __name__=='__main__': main()
