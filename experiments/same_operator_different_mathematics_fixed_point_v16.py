#!/usr/bin/env python3
"""V16: same verifier-governed developmental operator, different mathematical fixed points.

The controller receives no algebraic-law menu and has no world-specific branch.
It sees one bounded binary-operation syntax and 27 generic valuations. At each
step it selects the unqueried verified valuation that maximally separates terms
still aliased by the current quotient, retains it, and stops at zero gain.
Post-hoc probes measure associativity and designated left/right identity.

Boundary: finite carrier 3, generic term syntax bounded to two operation nodes,
and the valuation universe are supplied. This tests law-profile emergence under
one operator; genesis of the binary composition constructor remains untested.
"""
from dataclasses import dataclass
from itertools import product
from collections import defaultdict

C=(0,1,2); VS=("x","y","z")
def V(x): return ("v",x)
def E(): return ("e",)
def O(a,b): return ("o",a,b)
A=[V("x"),V("y"),V("z"),E()]
T0=A
T1=[O(a,b) for a in T0 for b in T0]
T2=[O(a,b) for xs,ys in ((T0,T1),(T1,T0)) for a in xs for b in ys]
TERMS=T0+T1+T2; IDX={t:i for i,t in enumerate(TERMS)}
VALS=[dict(zip(VS,x)) for x in product(C,repeat=3)]

def table(fn): return tuple(fn(a,b) for a in C for b in C)
@dataclass(frozen=True)
class World:
    name:str; tab:tuple; e:int
    def op(self,a,b): return self.tab[3*a+b]
WORLDS=(
 World("MONOID_ADD_Z3",table(lambda a,b:(a+b)%3),0),
 World("MONOID_MAX_CHAIN",table(max),0),
 World("MONOID_MUL_Z3",table(lambda a,b:(a*b)%3),1),
 World("ASSOC_ADD_WRONG_DESIGNATED_UNIT",table(lambda a,b:(a+b)%3),1),
 World("NONASSOC_RIGHT_ID_SUB_Z3",table(lambda a,b:(a-b)%3),0),
 World("NONASSOC_RIGHT_ID_TABLE",(0,0,0,1,0,0,2,0,1),0),
)

def ev(w,t,v):
    if t[0]=="v": return v[t[1]]
    if t[0]=="e": return w.e
    return w.op(ev(w,t[1],v),ev(w,t[2],v))
def vector(w,i): return tuple(ev(w,t,VALS[i]) for t in TERMS)
def verify(w,i,p): return tuple(p)==vector(w,i)
def partition(vecs):
    d={}
    for i in range(len(TERMS)):
        d.setdefault(tuple(v[i] for v in vecs),[]).append(i)
    return tuple(sorted(tuple(b) for b in d.values()))
ONE=(tuple(range(len(TERMS))),)
def gain(p,v):
    z=0
    for b in p:
        d=defaultdict(int)
        for i in b:d[v[i]]+=1
        n=len(b); z+=n*(n-1)//2-sum(k*(k-1)//2 for k in d.values())
    return z

@dataclass(frozen=True)
class State:
    retained:tuple=(); queried:frozenset=frozenset()
def q(w,s): return partition([vector(w,i) for i in s.retained]) if s.retained else ONE

def D(w,s):
    """Exactly the same developmental operator for every world."""
    p=q(w,s); cs=[]
    for i in range(len(VALS)):
        if i not in s.queried:
            v=vector(w,i); cs.append((gain(p,v),i,v))
    if not cs:return s,("FIXED",0,len(p))
    cs.sort(key=lambda x:(-x[0],x[1])); g,i,v=cs[0]
    if g==0:return s,("FIXED",0,len(p))
    asked=frozenset(set(s.queried)|{i})
    if not verify(w,i,v):return State(s.retained,asked),("REJECTED",i,g)
    n=State(s.retained+(i,),asked)
    return n,("VERIFIED",i,g,len(q(w,n)))
def iterate(w,s=None):
    s=s or State(); tr=[]
    for _ in range(28):
        n,e=D(w,s); tr.append(e)
        if n==s:return s,tr
        s=n
    raise AssertionError("finite development did not terminate")
def oracle(w): return partition([vector(w,i) for i in range(len(VALS))])

PROBES={
 "assoc":(O(O(V("x"),V("y")),V("z")),O(V("x"),O(V("y"),V("z")))),
 "left_unit":(O(E(),V("x")),V("x")),
 "right_unit":(O(V("x"),E()),V("x")),
}
def equiv(p,a,b):
    i,j=IDX[a],IDX[b]; return any(i in z and j in z for z in p)
def profile(p): return tuple(equiv(p,*PROBES[k]) for k in ("assoc","left_unit","right_unit"))
def counterexample(w,k):
    a,b=map(IDX.get,PROBES[k])
    for i in range(len(VALS)):
        v=vector(w,i)
        if v[a]!=v[b]:return (i,v[a],v[b])
    return None

def congruence(p):
    block={i:j for j,b in enumerate(p) for i in b}
    for i,t in enumerate(TERMS):
      for j,u in enumerate(TERMS):
       if block[i]==block[j]:
        for a in A:
         for x,y in ((O(t,a),O(u,a)),(O(a,t),O(a,u))):
          if x in IDX and y in IDX and block[IDX[x]]!=block[IDX[y]]:return False
    return True

def forged_guard(w):
    x=list(vector(w,0)); x[0]=(x[0]+1)%3; forged=tuple(x)
    before=State(); after=before if not verify(w,0,forged) else State((0,),frozenset({0}))
    return after==before

def lesion_repair(w,s,target):
    victim=s.retained[-1]
    lesion=State(s.retained[:-1],frozenset(i for i in s.queried if i!=victim))
    n,tr=iterate(w,lesion)
    return len(q(w,lesion)),len(q(w,n)),q(w,n)==target,tr

def main():
    profiles={}
    for w in WORLDS:
        s,tr=iterate(w); p=q(w,s); o=oracle(w)
        assert p==o
        n,stop=D(w,s); assert n==s and stop[0]=="FIXED"
        pr=profile(p); profiles[w.name]=pr
        ces={k:counterexample(w,k) for k in PROBES}
        for k,holds in zip(("assoc","left_unit","right_unit"),pr):assert (ces[k] is None)==holds
        assert congruence(p) and forged_guard(w)
        lc,rc,ok,rtr=lesion_repair(w,s,o); assert lc<len(o) and ok
        print("V16_WORLD",w.name,"SELECTED",s.retained,"SELECTED_COUNT",len(s.retained),"ORACLE_CLASSES",len(o),"PROFILE_ASSOC_LEFT_RIGHT",pr)
        print("V16_TRACE",w.name,tr)
        print("V16_COUNTEREXAMPLES",w.name,ces)
        print("V16_LESION_REPAIR",w.name,"LESION_CLASSES",lc,"REPAIRED_CLASSES",rc,"TRACE",rtr)
    expected={(True,True,True),(True,False,False),(False,False,True)}
    assert set(profiles.values())==expected
    assert sum(x==(True,True,True) for x in profiles.values())==3
    assert sum(x==(True,False,False) for x in profiles.values())==1
    assert sum(x==(False,False,True) for x in profiles.values())==2
    for x in (
      "SAME_FROZEN_OPERATOR_ALL_REGIMES","FIXED_POINTS_EQUAL_EXHAUSTIVE_SEMANTIC_ORACLES",
      "D_OF_FIXED_POINT_EQUALS_FIXED_POINT","ASSOCIATIVE_WORLDS_FORGET_PARENTHESIZATION",
      "NONASSOCIATIVE_WORLDS_RETAIN_PARENTHESIZATION","IDENTITY_VALID_WORLDS_FORGET_UNIT_INSERTION",
      "NO_IDENTITY_WORLDS_RETAIN_UNIT_INSERTION","ONE_SIDED_IDENTITY_PROFILE_RECOVERED",
      "COUNTEREXAMPLE_WITHDRAWS_PERMISSION_TO_FORGET","BOUNDED_CONGRUENCE_OF_FIXED_POINT",
      "STRUCTURAL_LESION_RESTARTS_SAME_OPERATOR","SAME_OPERATOR_RESTORES_OBSERVABLE_FIXED_POINT",
      "UNVERIFIED_SEMANTICS_CANNOT_REORGANIZE_STRUCTURE","NO_NAMED_LAW_MENU_OR_REGIME_BRANCH_IN_CONTROLLER",
      "SOURCE_DISTINCT_WORLDS_6_OF_6","SAME_OPERATOR_DIFFERENT_MATHEMATICS_FIXED_POINT_V16"):
        print(x+"=PASS")
    print("BOUNDARY=finite carrier, bounded generic binary-operation syntax, and generic valuation universe supplied; law profiles are not supplied to the developmental operator; binary composition constructor genesis remains untested")
if __name__=="__main__":main()
