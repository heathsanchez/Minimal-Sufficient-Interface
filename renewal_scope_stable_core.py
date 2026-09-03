r"""Extract and ablate the three A/B renewal words that remain excluded after SHORT/LONG scope widening.

This is a proof-search diagnostic over the source-backed partial Good-row block equations.
It does not claim a full E677 theorem.  It identifies which local equation families are
necessary for the scope-stable exclusions A, AB, BA and rejects any stronger wording.
"""
from __future__ import annotations
from itertools import product
import json
from renewal_block_scope_boundary import UF, structural_check

TARGETS=('A','AB','BA')
GROUPS=('entry','exit','entry_factor','hinge','return','factor1','factor2','tau','unique_fixer')

def check(word,shapes,enabled):
    n=len(word); uf=UF(); cells=[]; good=set(); bad=set(); inequalities=[]
    def v(k,i):
        s=f'{k}{i}'; uf.add(s); return s
    for i in range(n):
        r,g,b,x,z,a,h,w,q=[v(k,i) for k in ('r','g','b','x','z','a','h','w','q')]
        good|={r,g,z,h}; bad|={b,x}
        if shapes[i]=='S':
            uf.union(b,x); uf.union(a,z)
        else:
            inequalities.append((b,x))
        if 'entry' in enabled: cells.append((r,g,b,'entry'))
        if 'exit' in enabled: cells.append((r,x,z,'exit'))
        if 'entry_factor' in enabled: cells.append((r,b,a,'entry-factor'))
        if 'hinge' in enabled: cells.append((a,r,h,'hinge'))
        if 'return' in enabled: cells.append((b,h,g,'return'))
        if 'factor1' in enabled: cells.append((r,z,w,'factor-1'))
        if 'factor2' in enabled: cells.append((w,r,q,'factor-2'))
        if 'tau' in enabled: cells.append((z,q,x,'tau-companion'))
        j=(i+1)%n
        if word[i]=='A':
            uf.union(z,v('r',j)); uf.union(q,v('g',j)); uf.union(x,v('b',j)); good.add(q)
        else:
            uf.union(w,v('r',j)); uf.union(r,v('g',j)); uf.union(q,v('b',j)); good.add(w); bad.add(q)
    G={uf.find(t) for t in good}; B={uf.find(t) for t in bad}
    if G&B: return False,'colour-conflict'
    if any(uf.find(a)==uf.find(b) for a,b in inequalities): return False,'long-entry-exit-distinct'
    canon=[(uf.find(r),uf.find(x),uf.find(y),tag) for r,x,y,tag in cells]
    ok,reason=structural_check(canon)
    if not ok:return False,reason
    if 'unique_fixer' in enabled:
        rows=list(canon); fixers={t:set() for t in G|B}
        for r,x,y,tag in rows:
            if x==y and x in fixers:fixers[x].add(r)
        if any(fixers[t] for t in B):return False,'bad-has-fixer'
        for idx,t in enumerate(sorted(G)):
            if len(fixers[t])>1:return False,'good-has-multiple-fixers'
            if not fixers[t]:rows.append((f'FIX:{idx}:{t}',t,t,'unique-fixer'))
        ok,reason=structural_check(rows)
        if not ok:return False,reason
    return True,'consistent'

def excluded_all_shapes(word,enabled):
    details=[]
    for sh in map(''.join,product('SL',repeat=len(word))):
        sat,reason=check(word,sh,enabled); details.append((sh,sat,reason))
    return not any(s for _,s,_ in details),details

def main():
    full=set(GROUPS); out={}
    for word in TARGETS:
        ex,details=excluded_all_shapes(word,full); assert ex,(word,details)
        necessary=[]; dispensable=[]
        for g in GROUPS:
            ex2,_=excluded_all_shapes(word,full-{g})
            (dispensable if ex2 else necessary).append(g)
        # Greedy deletion to one inclusion-minimal core, replayed over every S/L shape.
        core=set(full)
        changed=True
        while changed:
            changed=False
            for g in list(sorted(core)):
                ex2,_=excluded_all_shapes(word,core-{g})
                if ex2:
                    core.remove(g); changed=True
        ex3,core_details=excluded_all_shapes(word,core); assert ex3
        out[word]={
          'all_shapes':details,'single_ablation_necessary':necessary,
          'single_ablation_dispensable':dispensable,'one_minimal_core':sorted(core),
          'minimal_core_all_shapes':core_details,
        }
    # Negative controls: known surviving words must remain realizable with the full system.
    controls={}
    for word in ('B','AA','BB','AAA','ABAB'):
        ex,details=excluded_all_shapes(word,full); controls[word]={'excluded':ex,'details':details}
        assert not ex,(word,details)
    print(json.dumps({'targets':out,'negative_controls':controls,
      'scope':'source-backed partial Good-row renewal block equations over all SHORT/LONG shapes; not full E677'},indent=2,sort_keys=True))
    print('RENEWAL_SCOPE_STABLE_CORE_VERIFIED')
if __name__=='__main__':main()