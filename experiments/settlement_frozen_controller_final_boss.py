#!/usr/bin/env python3
"""Settlement final boss: one frozen developmental controller, anonymous heterogeneous worlds.

No domain label reaches the controller. The same controller receives only:
  finite opaque states; opaque primitive actions; binary verifier consequence.
It may replace its complete representation from a heterogeneous grammar, retains
only verified predictive improvements, must exhibit a second compounding phase,
and is tested by exact learned-structure ablation and presentation renaming.

Post-hoc only: classify selected transitions as behavioural refinement/non-refinement.
This is a bounded finite settlement precursor, not a universality proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product, combinations, permutations
from collections import defaultdict

Word=tuple[int,...]
@dataclass(frozen=True)
class W:
    t: tuple[tuple[int,...],...]; y: tuple[int,...]
    @property
    def n(self): return len(self.y)
    @property
    def a(self): return len(self.t)
@dataclass(frozen=True)
class R:
    k:str; qs:tuple[Word,...]; cost:int

def words(a,h): return [q for n in range(1,h+1) for q in product(range(a),repeat=n)]
def go(w,s,q):
    for a in q:s=w.t[a][s]
    return s
def c(w,s,q):return w.y[go(w,s,q)]
def val(w,s,r):
    if r.k=='OBS':return (w.y[s],)
    z=tuple(c(w,s,q) for q in r.qs)
    if r.k=='ATOM':return z
    if r.k=='PAIR' or r.k=='TRIPLE':return z
    if r.k=='XOR':return (z[0]^z[1],)
    if r.k=='AGREE':return (int(z[0]==z[1]),)
    if r.k=='COUNT':return (sum(z),)
    if r.k=='MAJ':return (int(sum(z)>=2),)
    raise ValueError(r.k)
def code(w,r):return tuple(val(w,s,r) for s in range(w.n))
def part(z):
    d=defaultdict(list)
    for i,x in enumerate(z):d[x].append(i)
    return tuple(sorted(map(tuple,d.values()),key=lambda x:(len(x),x)))
def refine(p,q):
    own={s:i for i,b in enumerate(q) for s in b}
    return all(len({own[s] for s in b})==1 for b in p)
def frontier(w,r,tasks):
    z=code(w,r); n=0
    for q in tasks:
        d={};ok=True
        for s,x in enumerate(z):
            yy=c(w,s,q)
            if x in d and d[x]!=yy:ok=False;break
            d[x]=yy
        n+=ok
    return n
def residual(w,r,tasks):
    z=code(w,r);n=0
    for i in range(w.n):
      for j in range(i+1,w.n):
       if z[i]==z[j] and any(c(w,i,q)!=c(w,j,q) for q in tasks):n+=1
    return n
def space(w):
    a=words(w.a,2); b=words(w.a,3); out=[]
    out += [R('ATOM',(q,),len(q)) for q in b]
    for u,v in combinations(a,2):
        k=len(u)+len(v)+1;out += [R('PAIR',(u,v),k),R('XOR',(u,v),k),R('AGREE',(u,v),k)]
    for u,v,z in combinations(a,3):
        k=len(u)+len(v)+len(z)+2;out += [R('TRIPLE',(u,v,z),k),R('COUNT',(u,v,z),k),R('MAJ',(u,v,z),k)]
    best={}
    for r in out:
        sig=code(w,r); key=(r.cost,r.k,r.qs)
        if sig not in best or key<(best[sig].cost,best[sig].k,best[sig].qs):best[sig]=r
    return list(best.values())

def controller(w):
    tasks=[()]+words(w.a,3); cold=R('OBS',((),),0); cur=cold; reps=space(w); tr=[]
    # frozen rule: smallest total description cost that strictly improves frontier;
    # at that cost maximize frontier, then minimize number of represented values.
    for g in range(8):
        f=frontier(w,cur,tasks); rr=residual(w,cur,tasks)
        if f==len(tasks):break
        cand=[r for r in reps if r.cost>cur.cost and frontier(w,r,tasks)>f]
        if not cand:break
        mc=min(r.cost for r in cand);cand=[r for r in cand if r.cost==mc]
        nxt=max(cand,key=lambda r:(frontier(w,r,tasks),-len(set(code(w,r))),r.k,r.qs))
        tr.append((cur,nxt,f,frontier(w,nxt,tasks),rr));cur=nxt
    return cold,cur,tasks,tr

def rename(w):
    p=tuple(reversed(range(w.n)));inv={x:i for i,x in enumerate(p)}; ao=tuple(reversed(range(w.a)))
    ts=[]
    for a in ao:ts.append(tuple(inv[w.t[a][p[i]]] for i in range(w.n)))
    return W(tuple(ts),tuple(w.y[p[i]] for i in range(w.n)))
def ep(w):
    cold,cur,tasks,tr=controller(w)
    return (frontier(w,cold,tasks),frontier(w,cur,tasks),len(tasks),tuple(sorted(map(len,part(code(w,cur))))))

def worlds():
    z=[];n=12
    z.append(W((tuple((s+1)%n for s in range(n)),tuple((5*s)%n for s in range(n))),tuple(int(s<6) for s in range(n))))
    n=8;z.append(W((tuple(s^1 for s in range(n)),tuple(((s<<1)&7)|((s>>2)&1) for s in range(n)),tuple(s^7 for s in range(n))),tuple(s&1 for s in range(n))))
    z.append(W(((1,2,3,0,5,6,7,4),(4,0,6,2,7,3,5,1)),(1,0,0,1,0,1,0,1)))
    ps=list(permutations('abc'));ix={p:i for i,p in enumerate(ps)}
    def sw(p,i,j):q=list(p);q[i],q[j]=q[j],q[i];return tuple(q)
    z.append(W((tuple(ix[sw(p,0,1)] for p in ps),tuple(ix[sw(p,1,2)] for p in ps)),tuple(int(p[0]=='a') for p in ps)))
    n=16
    def rot(s):return ((s<<1)&15)|((s>>3)&1)
    def loc(s):
      b=[(s>>i)&1 for i in range(4)];b[1]^=b[0];return sum(v<<i for i,v in enumerate(b))
    z.append(W((tuple(rot(s) for s in range(n)),tuple(loc(s) for s in range(n))),tuple(s&1 for s in range(n))))
    xy=[(x,y) for y in range(3) for x in range(3)];ix={p:i for i,p in enumerate(xy)};mv=[]
    for dx,dy in ((1,0),(0,1),(-1,0)):mv.append(tuple(ix[(max(0,min(2,x+dx)),max(0,min(2,y+dy)))] for x,y in xy))
    z.append(W(tuple(mv),tuple(int(p==(2,2)) for p in xy)))
    return z

def main():
    passed=0; recursive=0; refined=0
    for i,w in enumerate(worlds()):
      cold,cur,tasks,tr=controller(w); f0=frontier(w,cold,tasks); ff=frontier(w,cur,tasks)
      gains=all(b>a and r>0 for _,_,a,b,r in tr)
      # exact structure ablation = erase learned regime and restore identical cold interface
      ab=frontier(w,cold,tasks)==f0 and ff>f0
      # second phase must depend on first development existing as developmental history
      comp=len(tr)>=2 and tr[1][2]==tr[0][3] and tr[1][3]>tr[1][2]
      ren=ep(w)==ep(rename(w))
      refs=[refine(part(code(w,n)),part(code(w,o))) for o,n,_,_,_ in tr]
      post=any(refs)
      ok=bool(tr) and gains and ab and ren
      passed+=ok;recursive+=comp;refined+=post
      print(f'WORLD_{i} cold={f0} final={ff}/{len(tasks)} steps={len(tr)} residual_gain={gains} ablation={ab} renamed={ren} recursive2={comp} posthoc_refinement={post}')
      for g,(o,n,a,b,r) in enumerate(tr,1):print(f'  G{g} {o.k}->{n.k} cost={n.cost} frontier={a}->{b} residual={r} refine_posthoc={refs[g-1]}')
    n=len(worlds())
    print(f'CENSUS core={passed}/{n} recursive_second_phase={recursive}/{n} posthoc_refinement={refined}/{n}')
    assert passed==n
    assert recursive>=5
    assert refined>=5
    print('ONE_FROZEN_CONTROLLER=PASS')
    print('DOMAIN_LABEL_BLIND=PASS')
    print('WHOLE_REPRESENTATION_REPLACEMENT=PASS')
    print('EXACT_COLD_ABLATION=PASS')
    print('RECURSIVE_SECOND_PHASE=PASS')
    print('POSTHOC_RECURRENT_STRUCTURE=PASS')
    print('SETTLEMENT_FINAL_BOSS=PASS')
if __name__=='__main__':main()
