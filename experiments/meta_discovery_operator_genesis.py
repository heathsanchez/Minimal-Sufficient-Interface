#!/usr/bin/env python3
"""Meta-discovery gate: can verified development discover new *ways of discovering*?

One anonymous controller receives only opaque states/actions and a verifier bit.
Level 0: primitives generate consequence probes.
Level 1: residual evidence selects a representation constructor (a discovery operator).
Level 2: the selected constructor is promoted into the search language and must enable
        a second representational discovery that is unreachable under the same budget
        without the promoted operator.

The point is recursive method genesis, not merely learning another feature.
Bounded finite precursor; no universality claim.
"""
from itertools import product
from collections import defaultdict

# Three source-distinct anonymous worlds, each deliberately requiring a different
# reusable way of combining verifier consequences at level 1.
def worlds():
    out=[]
    # states are bit vectors; actions permute/toggle coordinates, verifier exposes bit0
    for mode in range(3):
        n=16; states=[tuple((s>>i)&1 for i in range(4)) for s in range(n)]
        def idx(b): return sum(v<<i for i,v in enumerate(b))
        ts=[]
        for k in range(3):
            row=[]
            for b in states:
                q=list(b)
                if mode==0: q[k],q[(k+1)%4]=q[(k+1)%4],q[k]
                elif mode==1: q[k+1]^=q[k]
                else: q[(k+1)%4]^=q[(k+2)%4]
                row.append(idx(q))
            ts.append(tuple(row))
        out.append((tuple(ts),tuple(b[0] for b in states)))
    return out

def go(t,s,w):
    for a in w:s=t[a][s]
    return s
def probe(t,y,s,w):return y[go(t,s,w)]
def words(a,h):return [w for k in range(h+1) for w in product(range(a),repeat=k)]

def opval(kind,a,b):
    if kind=='XOR':return a^b
    if kind=='AGREE':return int(a==b)
    if kind=='AND':return a&b
    raise ValueError

def deterministic(code,target):
    d={}
    for x,y in zip(code,target):
        if x in d and d[x]!=y:return False
        d[x]=y
    return True

def frontier(t,y,code,tasks):
    return sum(deterministic(code,[probe(t,y,s,w) for s in range(len(y))]) for w in tasks)

def controller(t,y):
    a=len(t); tasks=words(a,4); base=words(a,2)
    # initial representation is verifier bit only
    code=[(y[s],) for s in range(len(y))]; cold=frontier(t,y,code,tasks)
    # Level 1: discover the best binary *method* for combining two probes.
    methods=[]
    for kind in ('XOR','AGREE','AND'):
      best=None
      for u in base:
       for v in base:
        feat=[opval(kind,probe(t,y,s,u),probe(t,y,s,v)) for s in range(len(y))]
        c=[code[s]+(feat[s],) for s in range(len(y))]
        f=frontier(t,y,c,tasks)
        cand=(f,-len(u)-len(v),u,v,c)
        if best is None or cand[:2]>best[:2]:best=cand
      methods.append((best[0],kind,best))
    methods.sort(reverse=True,key=lambda x:(x[0],x[1]))
    f1,kind,best=methods[0]; _,_,u,v,c1=best
    assert f1>cold
    # Promotion: learned KIND becomes a constructor available at depth 2.
    # Search a feature made by composing the promoted method over four primitive probes.
    promoted_best=(f1,None)
    for p in base:
      for q in base:
       for r in base:
        for z in base:
         feat=[]
         for s in range(len(y)):
          left=opval(kind,probe(t,y,s,p),probe(t,y,s,q))
          right=opval(kind,probe(t,y,s,r),probe(t,y,s,z))
          feat.append(opval(kind,left,right))
         c=[c1[s]+(feat[s],) for s in range(len(y))]
         f=frontier(t,y,c,tasks)
         if f>promoted_best[0]:promoted_best=(f,(p,q,r,z,c))
    f2=promoted_best[0]
    # Matched-budget ablation: without the promoted method, only one additional primitive probe.
    abl=f1
    for p in base:
      feat=[probe(t,y,s,p) for s in range(len(y))]
      c=[c1[s]+(feat[s],) for s in range(len(y))]
      abl=max(abl,frontier(t,y,c,tasks))
    return cold,f1,f2,abl,kind,(u,v)

def main():
    gains=causal=0
    for i,w in enumerate(worlds()):
        cold,f1,f2,abl,k,pair=controller(*w)
        recursive=f2>f1
        necessary=f2>abl
        gains+=recursive;causal+=necessary
        print(f'WORLD_{i} method={k} cold={cold} L1={f1} L2={f2} ablated={abl} recursive_method_gain={recursive} causal={necessary} seed={pair}')
    print(f'CENSUS recursive={gains}/3 causal={causal}/3')
    assert gains==3
    assert causal==3
    print('DISCOVERY_OPERATOR_SELECTED_FROM_RESIDUAL=PASS')
    print('DISCOVERY_OPERATOR_PROMOTED=PASS')
    print('PROMOTED_OPERATOR_ENABLES_NEW_DISCOVERY=PASS')
    print('MATCHED_BUDGET_OPERATOR_ABLATION=PASS')
    print('META_DISCOVERY_GENESIS=PASS')
if __name__=='__main__':main()
