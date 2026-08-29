#!/usr/bin/env python3
"""Meta-discovery V2: exhaustive grammar-extension separation.

Question: can verified residuals select a reusable *discovery operator* whose
promotion changes the reachable hypothesis language, rather than merely making
an already-reachable feature convenient?

We use all 16 Boolean functions on two bits as anonymous worlds. The cold
language L0 has literals x,y and NOT. Binary operators are initially unknown
candidate methods {AND, OR, XOR, EQ}. A method is selected solely by verified
residual reduction on acquisition targets. It is then promoted as a constructor.

Deciding requirement on sealed targets under an exact expression-size budget B:
  target notin Reach_B(L0)
  target in Reach_B(L0 + learned_operator)
  target notin Reach_B(L0 + any nonselected single operator)
Thus removal of the learned method is an exhaustive reachability separation,
not an accuracy comparison. A second stage must discover a composition built
from the promoted method that was impossible before promotion.

Finite Boolean precursor; does not establish open-ended self-improvement.
"""
from functools import lru_cache

MASK=0b1111
# rows 00,01,10,11
X=0b1100; Y=0b1010
OPS={
 'AND':lambda a,b:a&b,
 'OR':lambda a,b:a|b,
 'XOR':lambda a,b:a^b,
 'EQ':lambda a,b:(~(a^b))&MASK,
}
def neg(a):return (~a)&MASK

def reach(opname,maxcost):
    """Exact exhaustive semantic reachability by tree node cost."""
    by={1:{X,Y}}
    allv={X,Y}
    for c in range(2,maxcost+1):
        z={neg(a) for a in by.get(c-1,set())}
        if opname:
            f=OPS[opname]
            for lc in range(1,c-1):
                rc=c-1-lc
                for a in by.get(lc,set()):
                    for b in by.get(rc,set()):z.add(f(a,b))
        z-=allv;by[c]=z;allv|=z
    return allv,by

def mincost(opname,limit=11):
    _,by=reach(opname,limit);d={}
    for c,z in by.items():
        for v in z:d.setdefault(v,c)
    return d

def choose(acq,B):
    # verifier-only score: how many acquisition behaviours become reachable
    scored=[]
    for name in OPS:
        r,_=reach(name,B);scored.append((sum(t in r for t in acq),name))
    scored.sort(key=lambda x:(-x[0],x[1]))
    return scored[0],scored

def main():
    # Search all acquisition subsets for a non-handpicked decisive instance.
    # Preregistered deterministic ordering: smallest acquisition cardinality,
    # lexicographic mask tuple, then smallest B.
    universe=tuple(range(16)); found=None
    from itertools import combinations
    for k in range(1,5):
      for acq in combinations(universe,k):
       for B in range(3,9):
        (score,win),scores=choose(acq,B)
        if score==0:continue
        # require unique selected discovery method by acquisition score
        if len(scores)>1 and scores[1][0]==score:continue
        cold,_=reach(None,B); warm,_=reach(win,B)
        others={n:reach(n,B)[0] for n in OPS if n!=win}
        sealed=[t for t in universe if t not in acq and t not in cold and t in warm and all(t not in r for r in others.values())]
        if sealed:
            found=(acq,B,win,score,scores,sealed);break
       if found:break
      if found:break
    assert found is not None
    acq,B,win,score,scores,sealed=found
    target=sealed[0]
    cold,_=reach(None,B);warm,_=reach(win,B)
    print('ACQUISITION',acq,'BUDGET',B,'SCORES',scores,'SELECTED',win)
    print('SEALED_TARGET',target,'cold',target in cold,'warm',target in warm)
    for n in OPS:
        r,_=reach(n,B);print('ABLATE_TO',n,'reachable',target in r)
    assert target not in cold and target in warm
    assert all(target not in reach(n,B)[0] for n in OPS if n!=win)

    # Recursive-method gate: after promotion, find a behaviour whose minimum
    # expression cost falls strictly below every alternative single-method grammar.
    mc=mincost(win,11); alt={n:mincost(n,11) for n in OPS if n!=win}; base=mincost(None,11)
    candidates=[]
    for t,c in mc.items():
        rival=min([base.get(t,99)]+[d.get(t,99) for d in alt.values()])
        if c<rival:candidates.append((rival-c,c,t,rival))
    assert candidates
    candidates.sort(reverse=True);gap,c2,t2,rival=candidates[0]
    print('RECURSIVE_TARGET',t2,'learned_cost',c2,'best_without_learned_method',rival,'gap',gap)
    assert c2<rival
    print('RESIDUAL_SELECTS_DISCOVERY_OPERATOR=PASS')
    print('PROMOTION_STRICTLY_EXTENDS_REACHABLE_LANGUAGE=PASS')
    print('EXHAUSTIVE_OPERATOR_ABLATION=PASS')
    print('RECURSIVE_METHOD_COMPOSITION_ADVANTAGE=PASS')
    print('META_DISCOVERY_GRAMMAR_EXTENSION_V2=PASS')
if __name__=='__main__':main()
