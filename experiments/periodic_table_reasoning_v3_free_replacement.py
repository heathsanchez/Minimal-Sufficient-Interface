#!/usr/bin/env python3
"""Periodic Table of Reasoning V3: free representation replacement.

V2 still grew an append-only code. V3 removes that constraint. At every
residual, the learner may REPLACE its entire internal representation with an
independently generated candidate. Replacements may split, merge, or reorganize
old behavioural classes; no transition is required to refine the previous one.

The learner sees opaque states, primitive actions, and a binary verifier
consequence. Candidate representations are generic consequence programs:
  ATOM(w)              one future bit
  XOR(u,v)             relational bit
  AGREE(u,v)           equality bit
  PAIR(u,v)            fresh two-coordinate code
  COUNT3(u,v,z)        number of true consequences
  MAJ3(u,v,z)          majority consequence
  TRIPLE(u,v,z)        fresh three-coordinate code
None refers to the previous representation.

Developmental rule: when the current representation cannot determine all
protected consequences, enlarge the description budget by the minimum amount
needed to find any strict predictive improvement, then choose maximum protected
future frontier with MDL tie-breaks. The old representation is discarded.

After the trace is frozen, and only then, reconstruct behavioural equivalence
classes and test whether the chosen free replacements nevertheless form the
same refinement/reachability motif. We additionally require that non-refining
strict improvers existed somewhere in the search, proving refinement was not a
hard architectural constraint.

Bounded pilot: finite worlds, supplied action composition, binary verifier,
finite generic representation grammar, protected horizon 3.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product, combinations
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

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
class Rep:
    kind: str
    ws: Tuple[Word, ...]
    cost: int


def words(arity: int, max_len: int) -> List[Word]:
    out=[]
    for k in range(1,max_len+1): out.extend(product(range(arity), repeat=k))
    return out

def act(w: World, s: int, q: Word) -> int:
    for a in q: s=w.transitions[a][s]
    return s

def cons(w: World, s: int, q: Word) -> int:
    return w.outcome[act(w,s,q)]

def value(w: World, s: int, r: Rep):
    if r.kind=='OBS': return (w.outcome[s],)
    ys=tuple(cons(w,s,q) for q in r.ws)
    if r.kind=='ATOM': return (ys[0],)
    if r.kind=='XOR': return (ys[0]^ys[1],)
    if r.kind=='AGREE': return (int(ys[0]==ys[1]),)
    if r.kind=='PAIR': return ys
    if r.kind=='COUNT3': return (sum(ys),)
    if r.kind=='MAJ3': return (int(sum(ys)>=2),)
    if r.kind=='TRIPLE': return ys
    raise ValueError(r.kind)

def codes(w: World, r: Rep): return tuple(value(w,s,r) for s in range(w.n))
def classes_from_codes(zs):
    d=defaultdict(list)
    for s,z in enumerate(zs): d[z].append(s)
    return tuple(sorted((tuple(v) for v in d.values()),key=lambda b:(len(b),b)))
def sizes(p): return tuple(sorted(map(len,p)))
def refines(new,old):
    owner={s:i for i,b in enumerate(old) for s in b}
    return all(len({owner[s] for s in b})==1 for b in new)

def frontier(w: World, r: Rep, tasks: Sequence[Word]) -> int:
    zs=codes(w,r); good=0
    for t in tasks:
        seen: Dict[Tuple[int,...],int]={}; ok=True
        for s,z in enumerate(zs):
            y=cons(w,s,t)
            if z in seen and seen[z]!=y: ok=False; break
            seen[z]=y
        good += int(ok)
    return good

def residual_pairs(w: World, r: Rep, tasks: Sequence[Word]) -> int:
    zs=codes(w,r); n=0
    for i in range(w.n):
        for j in range(i+1,w.n):
            if zs[i]==zs[j] and any(cons(w,i,t)!=cons(w,j,t) for t in tasks): n+=1
    return n

def rep_space(w: World) -> List[Rep]:
    allw=words(w.arity,3)
    short=words(w.arity,2)
    reps=[]
    for q in allw: reps.append(Rep('ATOM',(q,),len(q)))
    for u,v in combinations(short,2):
        c=len(u)+len(v)+1
        reps += [Rep('XOR',(u,v),c),Rep('AGREE',(u,v),c),Rep('PAIR',(u,v),c)]
    # triples only over one-step and two-step words keeps the search bounded
    for u,v,z in combinations(short,3):
        c=len(u)+len(v)+len(z)+2
        reps += [Rep('COUNT3',(u,v,z),c),Rep('MAJ3',(u,v,z),c),Rep('TRIPLE',(u,v,z),c)]
    # behaviourally deduplicate, retaining lowest-cost/canonical program
    best={}
    for r in reps:
        sig=codes(w,r)
        key=(r.cost,r.kind,r.ws)
        if sig not in best or key<(best[sig].cost,best[sig].kind,best[sig].ws): best[sig]=r
    return list(best.values())

def learn(w: World):
    tasks=[()]+words(w.arity,3)
    cur=Rep('OBS',((),),0)
    reps=rep_space(w)
    trace=[]; all_nonrefining=0
    for g in range(w.n+4):
        f0=frontier(w,cur,tasks); r0=residual_pairs(w,cur,tasks)
        if f0==len(tasks): break
        oldp=classes_from_codes(codes(w,cur))
        # Count genuine alternatives that improve prediction while violating refinement.
        for cand in reps:
            if frontier(w,cand,tasks)>f0:
                newp=classes_from_codes(codes(w,cand))
                if not refines(newp,oldp): all_nonrefining += 1
        # Find smallest TOTAL description budget with an improver. No inheritance.
        eligible=[cand for cand in reps if cand.cost>cur.cost and frontier(w,cand,tasks)>f0]
        if not eligible: break
        mincost=min(c.cost for c in eligible)
        pool=[c for c in eligible if c.cost==mincost]
        scored=[]
        for cand in pool:
            f1=frontier(w,cand,tasks)
            # max consequence frontier; then fewer code values; then canonical syntax
            nvals=len(set(codes(w,cand)))
            scored.append(((f1,-nvals,cand.kind,tuple(tuple(-a for a in q) for q in cand.ws)),cand))
        _, nxt=max(scored,key=lambda x:x[0])
        f1=frontier(w,nxt,tasks); newp=classes_from_codes(codes(w,nxt))
        trace.append(dict(g=g+1,old=cur,new=nxt,cost=mincost,
                          frontier_before=f0,frontier_after=f1,residual_before=r0,
                          old_sizes=sizes(oldp),new_sizes=sizes(newp),
                          refines=refines(newp,oldp)))
        cur=nxt
    return dict(tasks=tasks,trace=trace,initial=frontier(w,Rep('OBS',((),),0),tasks),
                final=frontier(w,cur,tasks),total=len(tasks),final_rep=cur,
                nonrefining_improvers=all_nonrefining)

def renamed(w: World) -> World:
    perm=tuple(reversed(range(w.n))); inv={old:new for new,old in enumerate(perm)}
    order=(tuple(range(1,w.arity))+(0,)) if w.arity>1 else (0,)
    ts=[]
    for oa in order:
        ot=w.transitions[oa]
        ts.append(tuple(inv[ot[perm[ns]]] for ns in range(w.n)))
    return World(w.name+'_RENAMED',tuple(ts),tuple(w.outcome[perm[ns]] for ns in range(w.n)))
def endpoint(w: World,r):
    cold=Rep('OBS',((),),0)
    return (r['initial'],r['final'],r['total'],sizes(classes_from_codes(codes(w,cold))),
            sizes(classes_from_codes(codes(w,r['final_rep']))))

def worlds():
    from itertools import permutations
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
    census=defaultdict(int); worlds_with_nonref=0
    for w in worlds():
        r=learn(w); wr=renamed(w); rr=learn(wr)
        chosen_ref=bool(r['trace']) and all(t['refines'] for t in r['trace'])
        strict_gain=bool(r['trace']) and all(t['frontier_after']>t['frontier_before'] for t in r['trace'])
        residual=bool(r['trace']) and all(t['residual_before']>0 for t in r['trace'])
        nonref=r['nonrefining_improvers']>0
        worlds_with_nonref += int(nonref)
        motifs={
          'FREE_REPLACEMENT_CHOSE_REFINEMENT': chosen_ref,
          'RESIDUAL_DRIVEN_REGIME_CHANGE': residual,
          'EXPANDED_REACHABILITY': strict_gain and r['final']>r['initial'],
          'PRESENTATION_INVARIANT_ENDPOINT': endpoint(w,r)==endpoint(wr,rr),
          'NONREFINING_ALTERNATIVES_EXISTED': nonref,
          'FULL_FRONTIER_REACHED': r['final']==r['total'],
        }
        for k,v in motifs.items(): census[k]+=int(v)
        print('WORLD='+w.name)
        print(f"  FRONTIER={r['initial']}->{r['final']}/{r['total']} STEPS={len(r['trace'])} NONREFINING_IMPROVERS={r['nonrefining_improvers']}")
        for t in r['trace']:
            q=t['new']; print(f"  REPLACE g={t['g']} kind={q.kind} ws={q.ws} cost={q.cost} frontier={t['frontier_before']}->{t['frontier_after']} residual={t['residual_before']} classes={t['old_sizes']}->{t['new_sizes']} refines={t['refines']}")
        print('  MOTIFS='+','.join(k for k,v in motifs.items() if v))
    n=6
    print('MOTIF_CENSUS '+' '.join(f'{k}={v}/{n}' for k,v in sorted(census.items())))
    print(f'WORLDS_WITH_NONREFINING_IMPROVERS={worlds_with_nonref}/{n}')
    # Strong gate: representation replacement is unconstrained, yet chosen developmental
    # moves should recover refinement in a clear majority, with explicit counterfactual
    # non-refining improvements present in a clear majority of worlds.
    assert census['RESIDUAL_DRIVEN_REGIME_CHANGE']==n,census
    assert census['EXPANDED_REACHABILITY']==n,census
    assert census['PRESENTATION_INVARIANT_ENDPOINT']==n,census
    assert census['FREE_REPLACEMENT_CHOSE_REFINEMENT']>=5,census
    assert worlds_with_nonref>=4,census
    print('NO_APPEND_ONLY_REPRESENTATION=PASS')
    print('FREE_REPLACEMENT_SEARCH=PASS')
    print('NONREFINING_COUNTERFACTUALS_PRESENT=PASS')
    print('POSTHOC_REFINEMENT_REEMERGENCE=PASS')
    print('PERIODIC_TABLE_REASONING_V3=PASS')
if __name__=='__main__': main()
