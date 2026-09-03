"""Exact symbolic boundary for clean Good-row A/B renewal cycles.

This does NOT encode the full magma or all E677 equations.  It encodes exactly
what the proved Good-row renewal lemma exposes for a length-one Bad block,
closes a word of A/B transitions, enforces row-functionality/injectivity and
then optionally enforces the proved Good<->unique-fixer law on every coloured
label in the partial system.

Purpose: determine which clean cycle words are already impossible at this
representation and, by ablation, whether unique-fixer information is actually
causal.  Survivors certify a negative boundary: more mixed E677/Bad-row
coupling is required.
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


def build(word: str, enforce_unique_fixer: bool):
    n=len(word); uf=UF(); cells=[]; good=set(); bad=set()
    def v(k,i):
        x=f'{k}{i}'; uf.add(x); return x
    for i in range(n):
        r,g,b,z,h,w,q=[v(k,i) for k in 'rgbzhwq']
        good |= {r,g,z,h}; bad.add(b)
        # exact local equations for a one-cell maximal Bad block in a Good row
        # r:g->b->z, h=(r*b)*r=b\g, w=r*z, q=w*r, z*q=b.
        cells += [
            (r,g,b,'entry'),
            (r,b,z,'exit'),
            (z,r,h,'hinge'),
            (b,h,g,'return'),
            (r,z,w,'factor-1'),
            (w,r,q,'factor-2'),
            (z,q,b,'tau-companion'),
        ]
        j=(i+1)%n
        if word[i]=='A':
            uf.union(z,v('r',j)); uf.union(q,v('g',j)); uf.union(b,v('b',j)); good.add(q)
        else:
            uf.union(w,v('r',j)); uf.union(r,v('g',j)); uf.union(q,v('b',j)); good.add(w); bad.add(q)

    # Canonicalize colour requirements after all transition identifications.
    G={uf.find(x) for x in good}; B={uf.find(x) for x in bad}
    if G & B:
        return {'sat':False,'reason':'colour-conflict','word':word}

    canon=[]
    for r,x,y,tag in cells:
        canon.append((uf.find(r),uf.find(x),uf.find(y),tag))

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

    ok,reason=structural_check(canon)
    if not ok: return {'sat':False,'reason':reason,'word':word}

    existing=list(canon)
    if enforce_unique_fixer:
        # Bad iff no row fixes it; Good iff exactly one row fixes it.
        fixers={a:set() for a in G|B}
        for r,x,y,tag in existing:
            if x==y and x in fixers: fixers[x].add(r)
        if any(fixers[b] for b in B):
            return {'sat':False,'reason':'bad-has-fixer','word':word}
        # Add one fresh unique fixer for each Good input lacking one; reject >1.
        for idx,a in enumerate(sorted(G)):
            if len(fixers[a])>1:
                return {'sat':False,'reason':'good-has-multiple-fixers','word':word}
            if not fixers[a]:
                fr=f'FIX{idx}:{a}'
                existing.append((fr,a,a,'unique-fixer'))
                fixers[a].add(fr)
        ok,reason=structural_check(existing)
        if not ok: return {'sat':False,'reason':reason,'word':word}
        assert all(len(fixers[a])==1 for a in G)
        assert all(len(fixers[b])==0 for b in B)

    return {
        'sat':True,'reason':'partial-system-consistent','word':word,
        'classes':len({uf.find(x) for x in uf.p}),
        'good_classes':len(G),'bad_classes':len(B),
        'cells':len(existing),
    }


def main(max_len=7):
    rows=[]
    for n in range(1,max_len+1):
        for letters in product('AB', repeat=n):
            w=''.join(letters)
            base=build(w,False); fix=build(w,True)
            rows.append({'word':w,'base_sat':base['sat'],'fixer_sat':fix['sat'],
                         'base_reason':base['reason'],'fixer_reason':fix['reason']})
    base_sat=sum(r['base_sat'] for r in rows)
    fixer_sat=sum(r['fixer_sat'] for r in rows)
    causal=[r for r in rows if r['base_sat'] and not r['fixer_sat']]
    survivors=[r for r in rows if r['fixer_sat']]
    # The abstraction itself must be nontrivial and unique-fixer must have a
    # measurable causal effect, but survivors must remain if the representation
    # is still insufficient.
    assert base_sat>0
    assert causal, 'unique-fixer had no causal exclusions'
    assert survivors, 'clean-cycle abstraction unexpectedly fully closed; inspect before claiming theorem'
    out={
        'max_len':max_len,'total_words':len(rows),'base_sat':base_sat,
        'fixer_sat':fixer_sat,'fixer_causal_exclusions':len(causal),
        'survivors':len(survivors),
        'first_causal_exclusions':causal[:20],
        'first_survivors':survivors[:20],
        'residual':'Unique-fixer information excludes some clean renewal words but surviving A/B cycles prove that unique-fixer + Good-row renewal alone is incomplete; JOIN the surviving cycle language with Bad-row renewal and mixed E677 companion equations.',
        'scope':'partial row-injective renewal system only; not a magma and not a counterexample',
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    print('RENEWAL_UNIQUE_FIXER_BOUNDARY_VERIFIED')

if __name__=='__main__': main()
