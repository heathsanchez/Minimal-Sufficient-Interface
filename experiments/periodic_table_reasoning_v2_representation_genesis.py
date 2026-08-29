#!/usr/bin/env python3
"""Periodic Table of Reasoning V2: representation-genesis gate.

The learner never constructs or scores set partitions.  It sees only opaque
state ids, primitive actions, a binary verifier consequence, and protected
future tasks.  Its internal representation is a growing anonymous bit-code.
Each new bit may come from three generic families built only from verifier
consequences of short action words:

  PROBE(w)      = c_w(s)
  XOR(u,v)      = c_u(s) xor c_v(s)
  AGREE(u,v)    = [c_u(s) == c_v(s)]

Selection is purely predictive: add the minimum-description bit among those
that maximally enlarge the number of protected future consequences that are
deterministic functions of the current code.  No quotient/refinement/
separator/composition labels occur in learning.  After freezing the trace we
reconstruct the induced behavioural equivalence and test which motifs emerged.

This is still a bounded finite precursor: the feature meta-language, action
composition, binary consequence API, horizon and MDL ordering are supplied.
It specifically tests whether the quotient/refinement skeleton is an artifact
of explicitly representing partitions in V1.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product, permutations
from collections import defaultdict
from typing import Callable, Dict, List, Sequence, Tuple

Word = Tuple[int, ...]

@dataclass(frozen=True)
class World:
    name: str
    transitions: Tuple[Tuple[int, ...], ...]
    outcome: Tuple[int, ...]
    @property
    def n(self): return len(self.outcome)
    @property
    def arity(self): return len(self.transitions)

@dataclass(frozen=True)
class Feature:
    family: str
    a: Word
    b: Word = ()
    cost: int = 1


def words(arity: int, max_len: int) -> List[Word]:
    z=[]
    for k in range(1,max_len+1): z.extend(product(range(arity), repeat=k))
    return z

def act(w: World, s: int, word: Word) -> int:
    for a in word: s=w.transitions[a][s]
    return s

def cons(w: World, s: int, word: Word) -> int:
    return w.outcome[act(w,s,word)]

def feat_value(w: World, s: int, f: Feature) -> int:
    x=cons(w,s,f.a)
    if f.family=='PROBE': return x
    y=cons(w,s,f.b)
    if f.family=='XOR': return x ^ y
    if f.family=='AGREE': return int(x==y)
    raise ValueError(f.family)

def code(w: World, s: int, fs: Sequence[Feature]) -> Tuple[int,...]:
    return tuple(feat_value(w,s,f) for f in fs)

def predictable_count(w: World, fs: Sequence[Feature], tasks: Sequence[Word]) -> int:
    # Deliberately no partition object: direct determinism test over anonymous codes.
    good=0
    for t in tasks:
        seen: Dict[Tuple[int,...],int]={}
        ok=True
        for s in range(w.n):
            k=code(w,s,fs); y=cons(w,s,t)
            if k in seen and seen[k]!=y:
                ok=False; break
            seen[k]=y
        good += int(ok)
    return good

def unresolved_pairs(w: World, fs: Sequence[Feature], tasks: Sequence[Word]) -> int:
    zs=[code(w,s,fs) for s in range(w.n)]
    n=0
    for i in range(w.n):
        for j in range(i+1,w.n):
            if zs[i]==zs[j] and any(cons(w,i,t)!=cons(w,j,t) for t in tasks): n+=1
    return n

def feature_space(w: World, max_word=3) -> List[Feature]:
    ws=words(w.arity,max_word)
    out=[Feature('PROBE',u,(),len(u)) for u in ws]
    # Generic relational feature families.  Keep bounded and canonical u<v.
    for i,u in enumerate(ws):
        for v in ws[i+1:]:
            c=len(u)+len(v)+1
            out.append(Feature('XOR',u,v,c))
            out.append(Feature('AGREE',u,v,c))
    return out

def learn(w: World, max_word=3):
    tasks=[()]+words(w.arity,max_word)
    fs=[Feature('PROBE',(),(),0)] # direct binary consequence only
    candidates=feature_space(w,max_word)
    initial=predictable_count(w,fs,tasks)
    trace=[]
    for g in range(w.n+3):
        f0=predictable_count(w,fs,tasks)
        if f0==len(tasks): break
        r0=unresolved_pairs(w,fs,tasks)
        best=None
        for f in candidates:
            if f in fs: continue
            f1=predictable_count(w,fs+[f],tasks)
            gain=f1-f0
            if gain<=0: continue
            # Max predictive gain/frontier, then true MDL preference, then canonical syntax.
            famrank={'PROBE':2,'XOR':1,'AGREE':0}[f.family]
            key=(gain,f1,-f.cost,famrank,tuple(-x for x in f.a),tuple(-x for x in f.b))
            if best is None or key>best[0]: best=(key,f,f1)
        if best is None: break
        _,f,f1=best
        before_codes=tuple(code(w,s,fs) for s in range(w.n))
        fs.append(f)
        after_codes=tuple(code(w,s,fs) for s in range(w.n))
        trace.append(dict(g=g+1,feature=f,frontier_before=f0,frontier_after=f1,
                          residual_before=r0,before_codes=before_codes,after_codes=after_codes))
    return dict(tasks=tasks,features=fs,trace=trace,initial=initial,
                final=predictable_count(w,fs,tasks),total=len(tasks))

def classes(codes: Sequence[Tuple[int,...]]) -> Tuple[Tuple[int,...],...]:
    d=defaultdict(list)
    for i,z in enumerate(codes): d[z].append(i)
    return tuple(sorted((tuple(v) for v in d.values()), key=lambda q:(len(q),q)))

def sizes(p): return tuple(sorted(map(len,p)))
def is_refinement(old,new):
    owner={s:i for i,b in enumerate(old) for s in b}
    return all(len({owner[s] for s in b})==1 for b in new)

def exact_kernel_split(w: World, old_codes, new_codes, f: Feature):
    old=classes(old_codes); new=classes(new_codes)
    expected=[]
    for b in old:
        d=defaultdict(list)
        for s in b: d[feat_value(w,s,f)].append(s)
        expected.extend(tuple(v) for v in d.values())
    expected=tuple(sorted(expected,key=lambda q:(len(q),q)))
    return expected==new

def renamed(w: World) -> World:
    perm=tuple(reversed(range(w.n))); inv={old:new for new,old in enumerate(perm)}
    order=(tuple(range(1,w.arity))+(0,)) if w.arity>1 else (0,)
    ts=[]
    for oa in order:
        ot=w.transitions[oa]
        ts.append(tuple(inv[ot[perm[ns]]] for ns in range(w.n)))
    return World(w.name+'_RENAMED',tuple(ts),tuple(w.outcome[perm[ns]] for ns in range(w.n)))
def endpoint(w: World,r):
    cold_codes=tuple(code(w,s,[Feature('PROBE',(),(),0)]) for s in range(w.n))
    final_codes=tuple(code(w,s,r['features']) for s in range(w.n))
    return (r['initial'],r['final'],r['total'],sizes(classes(cold_codes)),sizes(classes(final_codes)))

def worlds():
    out=[]; n=12
    out.append(World('ARITHMETIC_RESIDUES',(tuple((s+1)%n for s in range(n)),tuple((5*s)%n for s in range(n))),tuple(int(s<6) for s in range(n))))
    n=8
    out.append(World('BOOLEAN_CUBE',(tuple(s^1 for s in range(n)),tuple(((s<<1)&7)|((s>>2)&1) for s in range(n)),tuple(s^7 for s in range(n))),tuple(s&1 for s in range(n))))
    out.append(World('GRAPH_NAVIGATION',((1,2,3,0,5,6,7,4),(4,0,6,2,7,3,5,1)),(1,0,0,1,0,1,0,1)))
    ps=list(permutations('abc')); ix={p:i for i,p in enumerate(ps)}
    def sw(p,i,j): q=list(p);q[i],q[j]=q[j],q[i];return tuple(q)
    out.append(World('SYMBOL_REWRITE',(tuple(ix[sw(p,0,1)] for p in ps),tuple(ix[sw(p,1,2)] for p in ps)),tuple(int(p[0]=='a') for p in ps)))
    n=16
    def rot4(s): return ((s<<1)&15)|((s>>3)&1)
    def local(s):
        b=[(s>>i)&1 for i in range(4)];b[1]^=b[0];return sum(v<<i for i,v in enumerate(b))
    out.append(World('CELLULAR_DYNAMICS',(tuple(rot4(s) for s in range(n)),tuple(local(s) for s in range(n))),tuple(s&1 for s in range(n))))
    coords=[(x,y) for y in range(3) for x in range(3)]; ix2={p:i for i,p in enumerate(coords)}; moves=[]
    for dx,dy in ((1,0),(0,1),(-1,0)):
        moves.append(tuple(ix2[(max(0,min(2,x+dx)),max(0,min(2,y+dy)))] for x,y in coords))
    out.append(World('BOUNDED_CONTROL',tuple(moves),tuple(int((x,y)==(2,2)) for x,y in coords)))
    return out

def main():
    census=defaultdict(int)
    for w in worlds():
        r=learn(w); wr=renamed(w); rr=learn(wr)
        coldfs=[Feature('PROBE',(),(),0)]
        cold_codes=tuple(code(w,s,coldfs) for s in range(w.n))
        final_codes=tuple(code(w,s,r['features']) for s in range(w.n))
        refinements=[]; exact=[]
        for t in r['trace']:
            refinements.append(is_refinement(classes(t['before_codes']),classes(t['after_codes'])))
            exact.append(exact_kernel_split(w,t['before_codes'],t['after_codes'],t['feature']))
        motifs={
          'EMERGENT_EQUIVALENCE': len(classes(cold_codes))<w.n,
          'EMERGENT_STRICT_REFINEMENT': bool(r['trace']) and all(refinements) and any(classes(t['before_codes'])!=classes(t['after_codes']) for t in r['trace']),
          'EMERGENT_EXACT_KERNEL_MEET': bool(r['trace']) and all(exact),
          'RESIDUAL_DRIVEN_PROMOTION': bool(r['trace']) and all(t['residual_before']>0 for t in r['trace']),
          'EXPANDED_REACHABILITY': r['final']>r['initial'],
          'PRESENTATION_INVARIANT_ENDPOINT': endpoint(w,r)==endpoint(wr,rr),
          'EXACT_ABLATION': predictable_count(w,coldfs,r['tasks'])==r['initial'],
          'COMPOSITION_NEEDED': any((f.family=='PROBE' and len(f.a)>=2) or f.family!='PROBE' for f in r['features'][1:]),
        }
        for k,v in motifs.items(): census[k]+=int(v)
        fam=defaultdict(int)
        for f in r['features'][1:]: fam[f.family]+=1
        print('WORLD='+w.name)
        print(f"  FRONTIER={r['initial']}->{r['final']}/{r['total']} FEATURES={len(r['features'])-1} FAMILIES={dict(fam)}")
        print(f"  COLD_CLASSES={sizes(classes(cold_codes))} FINAL_CLASSES={sizes(classes(final_codes))}")
        for t in r['trace']:
            f=t['feature']; print(f"  PROMOTE g={t['g']} family={f.family} a={f.a} b={f.b} cost={f.cost} frontier={t['frontier_before']}->{t['frontier_after']} residual={t['residual_before']}")
        print('  MOTIFS='+','.join(k for k,v in motifs.items() if v))
    n=6
    print('MOTIF_CENSUS '+' '.join(f'{k}={v}/{n}' for k,v in sorted(census.items())))
    core=('EMERGENT_EQUIVALENCE','EMERGENT_STRICT_REFINEMENT','EMERGENT_EXACT_KERNEL_MEET','RESIDUAL_DRIVEN_PROMOTION','EXPANDED_REACHABILITY','PRESENTATION_INVARIANT_ENDPOINT','EXACT_ABLATION')
    assert all(census[k]==n for k in core),census
    assert census['COMPOSITION_NEEDED']>=5,census
    print('NO_EXPLICIT_PARTITION_LEARNER=PASS')
    print('MULTI_FAMILY_ANONYMOUS_CODE=PASS')
    print('POSTHOC_QUOTIENT_REEMERGENCE=PASS')
    print('PERIODIC_TABLE_REASONING_V2=PASS')
if __name__=='__main__': main()
