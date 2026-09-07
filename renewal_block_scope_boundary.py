r"""Scope-ablation verifier for clean Good-row A/B renewal cycles.

The earlier renewal_unique_fixer_boundary.py intentionally encoded only
length-one (SHORT) maximal Bad blocks.  The source lemma allows

    row r: g Good -> b=b0 -> ... -> x Bad -> z Good

with b0 and x distinct for a LONG block.  This verifier restores that missing
scope distinction.  Each renewal step independently chooses S (SHORT) or L
(LONG), while retaining only source-backed local equations:

    r*g=b0, r*x=z,
    a=r*b0, a*r=h, b0*h=g,
    w=r*z, q=w*r, z*q=x.

A transition identifies the next E crossing with (z,q,x); B identifies it
with (w,r,q).  Clean renewal requires h Good and the source-specified colours.
The test is still a partial row-injective system, not a full E677 magma.
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
    fn={}; out={}
    for r,x,y,tag in rows:
        key=(r,x)
        if key in fn and fn[key]!=y:
            return False,f'function-conflict:{key}:{fn[key]}!={y}'
        fn[key]=y; out.setdefault(r,{})[x]=y
    for r,m in out.items():
        seen={}
        for x,y in m.items():
            if y in seen and seen[y]!=x:
                return False,f'row-noninjective:{r}:{seen[y]},{x}->{y}'
            seen[y]=x
    return True,'ok'


def build(word:str, shapes:str, enforce_unique_fixer:bool):
    assert len(word)==len(shapes)
    n=len(word); uf=UF(); cells=[]; good=set(); bad=set(); inequalities=[]
    def v(k,i):
        s=f'{k}{i}'; uf.add(s); return s
    for i in range(n):
        r,g,b,x,z,a,h,w,q=[v(k,i) for k in ('r','g','b','x','z','a','h','w','q')]
        good |= {r,g,z,h}; bad |= {b,x}
        if shapes[i]=='S':
            uf.union(b,x); uf.union(a,z)  # r*b=r*x=z
        else:
            inequalities.append((b,x,'long-entry-exit-distinct'))
        cells += [
            (r,g,b,'entry'), (r,x,z,'exit'),
            (r,b,a,'entry-factor'), (a,r,h,'hinge'), (b,h,g,'return'),
            (r,z,w,'factor-1'), (w,r,q,'factor-2'), (z,q,x,'tau-companion'),
        ]
        j=(i+1)%n
        if word[i]=='A':
            uf.union(z,v('r',j)); uf.union(q,v('g',j)); uf.union(x,v('b',j)); good.add(q)
        else:
            uf.union(w,v('r',j)); uf.union(r,v('g',j)); uf.union(q,v('b',j)); good.add(w); bad.add(q)

    G={uf.find(t) for t in good}; B={uf.find(t) for t in bad}
    if G & B: return {'sat':False,'reason':'colour-conflict'}
    for p,q,why in inequalities:
        if uf.find(p)==uf.find(q): return {'sat':False,'reason':why}
    canon=[(uf.find(r),uf.find(x),uf.find(y),tag) for r,x,y,tag in cells]
    ok,reason=structural_check(canon)
    if not ok: return {'sat':False,'reason':reason}
    rows=list(canon)
    if enforce_unique_fixer:
        fixers={t:set() for t in G|B}
        for r,x,y,tag in rows:
            if x==y and x in fixers: fixers[x].add(r)
        if any(fixers[t] for t in B): return {'sat':False,'reason':'bad-has-fixer'}
        for idx,t in enumerate(sorted(G)):
            if len(fixers[t])>1: return {'sat':False,'reason':'good-has-multiple-fixers'}
            if not fixers[t]:
                fr=f'FIX:{idx}:{t}'; rows.append((fr,t,t,'unique-fixer')); fixers[t].add(fr)
        ok,reason=structural_check(rows)
        if not ok: return {'sat':False,'reason':reason}
    return {'sat':True,'reason':'partial-general-block-system-consistent'}


def main(max_len=5):
    rows=[]
    for n in range(1,max_len+1):
        for letters in product('AB',repeat=n):
            w=''.join(letters)
            for sh in product('SL',repeat=n):
                s=''.join(sh)
                base=build(w,s,False); fix=build(w,s,True)
                rows.append({'word':w,'shapes':s,'base_sat':base['sat'],'fixer_sat':fix['sat'],
                             'base_reason':base['reason'],'fixer_reason':fix['reason']})
    base=sum(r['base_sat'] for r in rows); fixed=sum(r['fixer_sat'] for r in rows)
    causal=[r for r in rows if r['base_sat'] and not r['fixer_sat']]
    survivors=[r for r in rows if r['fixer_sat']]
    words=sorted({r['word'] for r in rows},key=lambda x:(len(x),x))
    word_surv={w:any(r['fixer_sat'] for r in rows if r['word']==w) for w in words}
    globally_excluded=[w for w,v in word_surv.items() if not v]
    short_rows=[r for r in rows if set(r['shapes'])=={'S'}]
    short_causal=sum(r['base_sat'] and not r['fixer_sat'] for r in short_rows)
    assert survivors, 'general block abstraction unexpectedly closed; inspect before theorem claim'
    out={
      'max_len':max_len,'typed_cases':len(rows),'base_sat':base,'fixer_sat':fixed,
      'fixer_causal_typed_exclusions':len(causal),'short_only_causal_exclusions':short_causal,
      'transition_words':len(words),'globally_excluded_transition_words':globally_excluded,
      'surviving_transition_words':sum(word_surv.values()),
      'first_long_survivors':[r for r in survivors if 'L' in r['shapes']][:20],
      'scope':'general SHORT/LONG partial row-injective Good-row renewal abstraction; not full E677 and not a magma counterexample',
    }
    if globally_excluded:
        out['residual']='Some A/B words remain excluded across both SHORT and LONG block shapes; retain only those scope-stable exclusions and JOIN the surviving language with Bad-row C renewal/mixed E677 equations.'
    else:
        out['residual']='Every A/B transition word has a SHORT/LONG realization despite unique fixers; prior exclusions were block-scope dependent. Retire transition-word exclusion and JOIN full block geometry with Bad-row C renewal/mixed E677 equations.'
    print(json.dumps(out,indent=2,sort_keys=True))
    print('RENEWAL_BLOCK_SCOPE_BOUNDARY_VERIFIED')

if __name__=='__main__': main()