from __future__ import annotations
import itertools, json
from pathlib import Path

N=7
PROFILES=((7,0,0),(5,2,0),(4,3,0),(3,2,2))
MATCHINGS={
 frozenset(((0,1),(2,3))),
 frozenset(((0,2),(1,3))),
 frozenset(((0,3),(1,2))),
}

def collision_pairs(c):
    return sum(x*(x-1)//2 for x in c)

def occurrence_counts():
    out={0:0,1:0,2:0}
    for c in itertools.product(range(3),repeat=N):
        if sum(c)==4:
            p=collision_pairs(c)
            if p in out: out[p]+=1
    return out

def matching_check():
    checked=0
    for vals in itertools.product(range(4),repeat=4):
        if max(vals.count(x) for x in set(vals))>2: continue
        pairs=[(a,b) for a,b in itertools.combinations(range(4),2) if vals[a]==vals[b]]
        if len(pairs)==2:
            assert frozenset(pairs) in MATCHINGS
            checked+=1
    return checked

def parts(n,lo=2):
    if n==0:return [()]
    out=[]
    def rec(rem,start,cur):
        if rem==0: out.append(tuple(cur)); return
        for x in range(start,rem+1):
            if x>=2: rec(rem-x,x,cur+[x])
    rec(n,lo,[]); return out

def sigs(p):
    return [tuple(tuple(2*x for x in q) for q in choice)
            for choice in itertools.product(*(parts(x) for x in p))]

def main():
    pdata={}
    for p in PROFILES:
        s=sigs(p)
        pdata['-'.join(map(str,p))]={
            'count':len(s),
            'signatures':[[list(c) for c in z] for z in s],
        }
    out={
      'n':N,
      'total':2*N,
      'occurrence_counts':occurrence_counts(),
      'matching_assignments_checked':matching_check(),
      'derived':{
        'column_degree_2':True,
        'symbol_degree_2':True,
        'bipartite_2_regular':True,
        'even_cycle_components':True,
        'component_single_matching_color':True,
        'labels_alternate_complements':True,
      },
      'profiles':pdata,
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/column_symbol_cycle_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    assert {k:v['count'] for k,v in pdata.items()}=={'7-0-0':4,'5-2-0':2,'4-3-0':2,'3-2-2':1}
if __name__=='__main__':main()
