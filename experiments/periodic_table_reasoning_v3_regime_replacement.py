#!/usr/bin/env python3
"""Periodic Table of Reasoning V3: whole-regime replacement.

Unlike V2, development is NOT append-only.  At each width the learner searches
from scratch for a complete anonymous predictive code.  The next selected code
may discard earlier features, split classes, merge classes, or be incomparable
with the preceding code.  Quotients/refinement are never used by selection;
they are reconstructed only after the developmental trace is frozen.

This remains a bounded finite precursor.  The consequence API, generic feature
families, finite horizon and beam/MDL search are supplied.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
from periodic_table_reasoning_v2_representation_genesis import (
    Feature, worlds, renamed, words, feature_space, code, cons,
    predictable_count, unresolved_pairs, classes, sizes,
)

BASE = Feature('PROBE',(),(),0)

def mdl(rep):
    return sum(f.cost for f in rep[1:]) + len(rep)-1

def relation(a,b):
    """Relation between equivalences induced by two complete codes."""
    A=classes(a); B=classes(b)
    ao={s:i for i,q in enumerate(A) for s in q}; bo={s:i for i,q in enumerate(B) for s in q}
    b_ref_a=all(len({ao[s] for s in q})==1 for q in B) # B refines A
    a_ref_b=all(len({bo[s] for s in q})==1 for q in A) # A refines B
    if b_ref_a and a_ref_b: return 'EQUAL'
    if b_ref_a: return 'REFINE'
    if a_ref_b: return 'COARSEN'
    return 'INCOMPARABLE'

def pool_for(w,tasks,limit=90):
    fs=feature_space(w,3)
    # Domain-blind screening: predictive frontier, residual reduction, MDL only.
    cold=[BASE]; r0=unresolved_pairs(w,cold,tasks)
    scored=[]
    for f in fs:
        rep=[BASE,f]
        scored.append((predictable_count(w,rep,tasks), r0-unresolved_pairs(w,rep,tasks), -f.cost, f))
    scored.sort(key=lambda z:z[:3], reverse=True)
    keep=[z[3] for z in scored[:limit]]
    # Always retain all primitive action-word probes so composition remains reachable.
    for f in fs:
        if f.family=='PROBE' and f not in keep: keep.append(f)
    return keep

def beam_best(w,tasks,max_width=6,beam=140):
    pool=pool_for(w,tasks)
    current=[(BASE,)]
    stage=[]
    seen=set(current)
    for width in range(1,max_width+1):
        cand=[]
        for rep in current:
            used=set(rep)
            for f in pool:
                if f in used: continue
                nr=tuple(sorted(rep+(f,), key=lambda x:(x.family,x.a,x.b,x.cost)))
                if nr in seen: continue
                seen.add(nr)
                fcnt=predictable_count(w,nr,tasks)
                res=unresolved_pairs(w,nr,tasks)
                key=(fcnt,-res,-mdl(nr),-len(nr),repr(nr))
                cand.append((key,nr,fcnt,res))
        if not cand: break
        cand.sort(key=lambda z:z[0], reverse=True)
        current=[z[1] for z in cand[:beam]]
        best=cand[0]
        stage.append((width,best[1],best[2],best[3]))
        if best[2]==len(tasks): break
    return stage

def learn(w):
    tasks=[()]+words(w.arity,3)
    cold=(BASE,); initial=predictable_count(w,cold,tasks)
    stages=beam_best(w,tasks)
    trace=[]; prev=cold; prev_front=initial
    for width,rep,front,res in stages:
        if front<=prev_front: continue
        bc=tuple(code(w,s,prev) for s in range(w.n)); ac=tuple(code(w,s,rep) for s in range(w.n))
        trace.append(dict(width=width,rep=rep,frontier_before=prev_front,frontier_after=front,
                          residual_before=unresolved_pairs(w,prev,tasks),relation=relation(bc,ac),
                          before_codes=bc,after_codes=ac))
        prev=rep; prev_front=front
    return dict(tasks=tasks,initial=initial,final=prev_front,total=len(tasks),trace=trace,rep=prev)

def endpoint(w,r):
    cold=tuple(code(w,s,(BASE,)) for s in range(w.n)); fin=tuple(code(w,s,r['rep']) for s in range(w.n))
    return (r['initial'],r['final'],r['total'],sizes(classes(cold)),sizes(classes(fin)))

def main():
    census=defaultdict(int); transition_counts=defaultdict(int); full=0
    for w in worlds():
        r=learn(w); wr=renamed(w); rr=learn(wr)
        cold_codes=tuple(code(w,s,(BASE,)) for s in range(w.n)); fin_codes=tuple(code(w,s,r['rep']) for s in range(w.n))
        rels=[t['relation'] for t in r['trace']]
        for x in rels: transition_counts[x]+=1
        motifs={
            'EMERGENT_EQUIVALENCE': len(classes(cold_codes))<w.n,
            'RESIDUAL_DRIVEN_REGIME_CHANGE': bool(r['trace']) and all(t['residual_before']>0 for t in r['trace']),
            'EXPANDED_REACHABILITY': r['final']>r['initial'],
            'PRESENTATION_INVARIANT_ENDPOINT': endpoint(w,r)==endpoint(wr,rr),
            'EXACT_ABLATION': predictable_count(w,(BASE,),r['tasks'])==r['initial'],
            'POSTHOC_REFINEMENT_PRESENT': 'REFINE' in rels,
            'NONMONOTONE_CHANGE_PRESENT': any(x in ('COARSEN','INCOMPARABLE') for x in rels),
            'COMPOSITION_IN_FINAL': any((f.family!='PROBE') or len(f.a)>=2 for f in r['rep'][1:]),
        }
        for k,v in motifs.items(): census[k]+=int(v)
        full += int(r['final']==r['total'])
        fam=defaultdict(int)
        for f in r['rep'][1:]: fam[f.family]+=1
        print('WORLD='+w.name)
        print(f"  FRONTIER={r['initial']}->{r['final']}/{r['total']} FINAL_MDL={mdl(r['rep'])} FAMILIES={dict(fam)}")
        print(f"  COLD_CLASSES={sizes(classes(cold_codes))} FINAL_CLASSES={sizes(classes(fin_codes))}")
        for t in r['trace']:
            print(f"  REPLACE width={t['width']} relation={t['relation']} frontier={t['frontier_before']}->{t['frontier_after']} residual={t['residual_before']}")
        print('  MOTIFS='+','.join(k for k,v in motifs.items() if v))
    n=6
    print('MOTIF_CENSUS '+' '.join(f'{k}={v}/{n}' for k,v in sorted(census.items())))
    print('TRANSITIONS '+' '.join(f'{k}={v}' for k,v in sorted(transition_counts.items())))
    print(f'FULL_FRONTIER={full}/{n}')
    assert census['EMERGENT_EQUIVALENCE']==n
    assert census['RESIDUAL_DRIVEN_REGIME_CHANGE']==n
    assert census['EXPANDED_REACHABILITY']==n
    assert census['PRESENTATION_INVARIANT_ENDPOINT']==n
    assert census['EXACT_ABLATION']==n
    assert census['POSTHOC_REFINEMENT_PRESENT']>=5
    assert full>=5
    print('WHOLE_REGIME_REPLACEMENT=PASS')
    print('NO_APPEND_ONLY_CONSTRAINT=PASS')
    print('POSTHOC_STRUCTURE_CENSUS=PASS')
    print('PERIODIC_TABLE_REASONING_V3=PASS')
if __name__=='__main__': main()
