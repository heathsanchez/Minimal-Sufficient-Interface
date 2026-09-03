"""Finite exact certificate for the pair-local T6 image-intersection theorem at order 7.

Let F_t(q)=D(q-t)-A(q).  The preceding EdgeTransport law says an agreement edge
with phase x is T6-compatible exactly when F_t(a)=F_u(b) for the two local
second-iterate inputs a,b.  We certify that for every nonzero row offset and every
phase x, the shifted-Latin + Badness pair language realizes every ordered pair
(a,b) in Z_7^2.  Hence pair-local T6 feasibility is exactly Im(F_t)∩Im(F_u) != ∅.
"""
from __future__ import annotations
import itertools, json
from collections import Counter, defaultdict
from pathlib import Path
N=7
CANONICAL_D=('0125634','0145236','1023546','1024356')
PERMS=list(itertools.permutations(range(N)))
AS=[p for p in PERMS if p[0]==0]
def parse(s): return tuple(map(int,s))
Ds=[parse(s) for s in CANONICAL_D]
def legal_sigma(p,d): return all((p[x]-x)%N != d%N for x in range(N))
def F(D,A,t,q): return (D[(q-t)%N]-A[q])%N

def local_ab_coverage():
    # Cache U witnesses by (x,s,r,k) as in the quotient probe.
    cache=defaultdict(set)
    for U in PERMS:
        if U[0]==0: continue
        for x in range(N):
            s=U[x]
            for r in range(N):
                a=U[r]; b=U[s]
                for k in range(N):
                    if U[k]!=0: cache[(x,s,r,k)].add((a,b))
    result={}
    full={(a,b) for a in range(N) for b in range(N)}
    for d in range(1,N):
        by_phase={x:set() for x in range(N)}
        for sig in PERMS:
            if not legal_sigma(sig,d): continue
            k=sig[0]
            for x in range(N):
                if sig[x]!=x: continue
                for s in range(N):
                    r=sig[s]
                    by_phase[x] |= cache.get((x,s,r,k),set())
        assert all(by_phase[x]==full for x in range(N)), (d,{x:len(v) for x,v in by_phase.items()})
        result[str(d)]={str(x):len(by_phase[x]) for x in range(N)}
    return result

def edge_graph(D,A):
    edges=[]
    images=[]
    for t in range(N): images.append(set(F(D,A,t,q) for q in range(N)))
    for t in range(N):
        for u in range(t+1,N):
            if images[t].isdisjoint(images[u]): edges.append((t,u))
    return tuple(edges)
def degree_signature(edges):
    deg=[0]*N
    for t,u in edges: deg[t]+=1; deg[u]+=1
    return tuple(sorted(deg))

def main():
    prior=json.load(open('artifacts/t6_pair_transport_quotient_probe.json'))
    coverage=local_ab_coverage()
    spectrum=Counter(); extreme=[]; total_forbidden=0
    per_D=Counter()
    for name,D in zip(CANONICAL_D,Ds):
        for ai,A in enumerate(AS):
            e=edge_graph(D,A); total_forbidden += len(e); per_D[name]+=len(e)
            key=(len(e),degree_signature(e)); spectrum[key]+=1
            if len(e)>=6:
                extreme.append({'D':name,'A_index':ai,'A':list(A),'forbidden_edges':[list(x) for x in e],
                                'degree_signature':list(degree_signature(e))})
    assert total_forbidden==prior['impossible_pair_cases']==1680
    assert all(per_D[d]==420 for d in CANONICAL_D)
    assert len(extreme)==40
    assert sum(1 for x in extreme if len(x['forbidden_edges'])==7)==12
    assert sum(1 for x in extreme if len(x['forbidden_edges'])==6)==28
    assert all(x['degree_signature']==[2]*7 for x in extreme if len(x['forbidden_edges'])==7)
    assert all(x['degree_signature']==[1,1,1,1,1,1,6] for x in extreme if len(x['forbidden_edges'])==6)
    out={
      'theorem':'At order 7, for canonical D and normalized A, a row pair {t,u} admits a locally shifted-Latin, Bad, T6-compatible agreement edge at every phase iff Im(F_t) intersects Im(F_u), where F_t(q)=D(q-t)-A(q).',
      'local_ab_coverage_by_offset_phase':coverage,
      'forbidden_edge_occurrences':total_forbidden,
      'forbidden_occurrences_per_canonical_D':dict(per_D),
      'forbidden_graph_spectrum':{f'edges={k[0]},degrees={k[1]}':v for k,v in sorted(spectrum.items())},
      'extreme_graph_cases':extreme,
      'seven_edge_cases':12,
      'six_edge_cases':28,
      'residual':('Lift the image-intersection obstruction from pairs to the Latin phase matrix. First test the 40 extreme '
                  'forbidden-edge graphs (12 seven-cycles, 28 stars): determine whether seven row permutations can realize '
                  'the uniform (2,2,1,1,1) phase profile with every duplicated row pair lying in the allowed-edge complement. '
                  'If all survive, join image-intersection with EdgeTransport labels at triangles rather than adding magma state.'),
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/t6_pair_image_intersection_certificate.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'forbidden_edge_occurrences':total_forbidden,'forbidden_graph_spectrum':out['forbidden_graph_spectrum'],
                      'seven_edge_cases':12,'six_edge_cases':28,'residual':out['residual']},indent=2,sort_keys=True))
    print('T6_PAIR_IMAGE_INTERSECTION_THEOREM_PASS')
if __name__=='__main__': main()
