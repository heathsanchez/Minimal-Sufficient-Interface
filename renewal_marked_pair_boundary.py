r"""Exact partial-system boundary for two marked Good-row renewal strands.

Source-backed constraints added beyond renewal_unique_fixer_boundary.py:
- two distinct source rows r,s share one Good input u and one Bad target b;
- their first E-crossings are (r,u,b) and (s,u,b);
- the companion return hinge h=b\u is common;
- both strands stay in the clean A/B Good-row renewal system;
- the Good/Bad unique-fixer boundary is enforced exactly as in the prior
  partial-system test.

This is intentionally still weaker than a full E677 magma.  Its only purpose
is to ask whether the *marked ancestry* proved by the collision handoff has a
causal effect beyond single-cycle consistency.
"""
from __future__ import annotations
from itertools import product
import json

class UF:
    def __init__(self): self.p={}
    def add(self,x): self.p.setdefault(x,x)
    def find(self,x):
        self.add(x)
        if self.p[x]!=x: self.p[x]=self.find(self.p[x])
        return self.p[x]
    def union(self,a,b):
        ra,rb=self.find(a),self.find(b)
        if ra!=rb: self.p[rb]=ra


def structural_check(rows):
    function={}; row_outputs={}
    for r,x,y,tag in rows:
        key=(r,x)
        if key in function and function[key]!=y:
            return False,f'function-conflict:{key}:{function[key]}!={y}'
        function[key]=y
        row_outputs.setdefault(r,{})[x]=y
    for r,m in row_outputs.items():
        seen={}
        for x,y in m.items():
            if y in seen and seen[y]!=x:
                return False,f'row-noninjective:{r}:{seen[y]},{x}->{y}'
            seen[y]=x
    return True,'ok'


def add_strand(uf,cells,good,bad,prefix,word):
    n=len(word)
    def v(k,i):
        x=f'{prefix}:{k}{i}'; uf.add(x); return x
    for i in range(n):
        r,g,b,z,h,w,q=[v(k,i) for k in 'rgbzhwq']
        good |= {r,g,z,h}; bad.add(b)
        cells += [
            (r,g,b,f'{prefix}:entry'),
            (r,b,z,f'{prefix}:exit'),
            (z,r,h,f'{prefix}:hinge'),
            (b,h,g,f'{prefix}:return'),
            (r,z,w,f'{prefix}:factor-1'),
            (w,r,q,f'{prefix}:factor-2'),
            (z,q,b,f'{prefix}:tau-companion'),
        ]
        j=(i+1)%n
        if word[i]=='A':
            uf.union(z,v('r',j)); uf.union(q,v('g',j)); uf.union(b,v('b',j)); good.add(q)
        else:
            uf.union(w,v('r',j)); uf.union(r,v('g',j)); uf.union(q,v('b',j)); good.add(w); bad.add(q)
    return v


def build_pair(word1,word2,enforce_marked_pair=True,enforce_unique_fixer=True):
    uf=UF(); cells=[]; good=set(); bad=set()
    v1=add_strand(uf,cells,good,bad,'S1',word1)
    v2=add_strand(uf,cells,good,bad,'S2',word2)

    if enforce_marked_pair:
        # Exact residual collision page: r*u=b=s*u with r != s, u Good, b Bad,
        # and h=b\u common to both first maximal Bad blocks.
        uf.union(v1('g',0),v2('g',0))
        uf.union(v1('b',0),v2('b',0))
        uf.union(v1('h',0),v2('h',0))

    G={uf.find(x) for x in good}; B={uf.find(x) for x in bad}
    if G & B: return {'sat':False,'reason':'colour-conflict'}
    if enforce_marked_pair and uf.find(v1('r',0))==uf.find(v2('r',0)):
        return {'sat':False,'reason':'marked-source-rows-merged'}

    canon=[(uf.find(r),uf.find(x),uf.find(y),tag) for r,x,y,tag in cells]
    ok,reason=structural_check(canon)
    if not ok: return {'sat':False,'reason':reason}

    rows=list(canon)
    if enforce_unique_fixer:
        fixers={a:set() for a in G|B}
        for r,x,y,tag in rows:
            if x==y and x in fixers: fixers[x].add(r)
        if any(fixers[b] for b in B): return {'sat':False,'reason':'bad-has-fixer'}
        for idx,a in enumerate(sorted(G)):
            if len(fixers[a])>1: return {'sat':False,'reason':'good-has-multiple-fixers'}
            if not fixers[a]:
                fr=f'FIX:{idx}:{a}'; rows.append((fr,a,a,'unique-fixer')); fixers[a].add(fr)
        ok,reason=structural_check(rows)
        if not ok: return {'sat':False,'reason':reason}

    return {'sat':True,'reason':'partial-paired-system-consistent',
            'classes':len({uf.find(x) for x in uf.p}),'cells':len(rows)}


def words(max_len):
    return [''.join(x) for n in range(1,max_len+1) for x in product('AB',repeat=n)]


def main(max_len=5):
    ws=words(max_len)
    # Baseline: same two clean cycles with no shared collision ancestry.
    base={}; paired={}
    for a in ws:
        for b in ws:
            base[(a,b)]=build_pair(a,b,False,True)['sat']
            paired[(a,b)]=build_pair(a,b,True,True)['sat']
    base_n=sum(base.values()); pair_n=sum(paired.values())
    causal=[(a,b) for (a,b),ok in base.items() if ok and not paired[(a,b)]]
    gained=[(a,b) for (a,b),ok in paired.items() if ok and not base[(a,b)]]
    assert not gained, 'adding collision ancestry cannot create a previously inconsistent pair'
    # Do not assume causality: the experiment decides it.
    pairable={a:any(paired[(a,b)] or paired[(b,a)] for b in ws) for a in ws}
    unpairable=[a for a,v in pairable.items() if not v]
    out={
      'max_len':max_len,'words':len(ws),'ordered_pairs':len(ws)**2,
      'baseline_pair_survivors':base_n,'marked_pair_survivors':pair_n,
      'causal_pair_exclusions':len(causal),'unpairable_cycle_words':unpairable,
      'first_causal_pair_exclusions':[list(x) for x in causal[:30]],
      'scope':'partial row-injective Good-row renewal system; not full E677 and not a magma counterexample',
    }
    if causal:
        out['residual']='Marked shared-(u,b) ancestry is causal but not complete; retain it and next JOIN surviving paired strands with the Bad-row C renewal / mixed E677 cells.'
        print('MARKED_ANCESTRY_CAUSAL=True')
    else:
        out['residual']='Shared-(u,b) marked ancestry adds no exclusions at this abstraction; record a negative law and suppress ancestry-only refinement. Move directly to Bad-row C renewal / mixed E677 coupling.'
        print('MARKED_ANCESTRY_CAUSAL=False')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('RENEWAL_MARKED_PAIR_BOUNDARY_VERIFIED')

if __name__=='__main__': main()