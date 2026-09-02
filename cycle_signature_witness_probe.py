"""Extract the column-symbol cycle signature of one exact witness per shifted-surviving orientation."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from shifted_profile_orientation_probe import TYPES, orientations, test_vector

EDGE_ORDER=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
PAIR_COLOR={
    (0,1):'A',(2,3):'A',
    (0,2):'B',(1,3):'B',
    (0,3):'C',(1,2):'C',
}


def signature(rows):
    # Build the saturated equality-incidence multigraph C_i -- S_s, with one
    # edge for each agreeing row pair. Components are then read directly.
    adj={}
    edge_color={}
    eid=0
    for i in range(7):
        for a,b in EDGE_ORDER:
            if rows[a][i] != rows[b][i]:
                continue
            s=rows[a][i]
            cnode=('C',i); snode=('S',s)
            adj.setdefault(cnode,[]).append((eid,snode))
            adj.setdefault(snode,[]).append((eid,cnode))
            edge_color[eid]=PAIR_COLOR[(a,b)]
            eid+=1
    if eid != 14:
        raise AssertionError(f'expected 14 equality events, got {eid}')
    if any(len(v)!=2 for v in adj.values()) or len(adj)!=14:
        raise AssertionError('incidence graph is not saturated 2-regular')
    seen=set(); by={'A':[],'B':[],'C':[]}
    for start in sorted(adj):
        if start in seen: continue
        stack=[start]; nodes=[]; colors=set()
        while stack:
            x=stack.pop()
            if x in seen: continue
            seen.add(x); nodes.append(x)
            for e,y in adj[x]:
                colors.add(edge_color[e])
                if y not in seen: stack.append(y)
        if len(colors)!=1:
            raise AssertionError(f'mixed-color component: {colors}')
        color=next(iter(colors))
        by[color].append(len(nodes))
    return {k:sorted(v) for k,v in by.items()}


def main():
    results={}
    all_sigs=set()
    for typ in TYPES:
        key='-'.join(map(str,typ)); entries=[]
        for j,vec in enumerate(orientations(typ)):
            r=test_vector(vec,f'w_{key}_{j}')
            item={'vector':list(vec),'status':r['status']}
            if r['status']=='sat':
                sig=signature(r['rows'])
                item['cycle_signature']=sig
                all_sigs.add(json.dumps(sig,sort_keys=True))
            entries.append(item)
        results[key]=entries
    out={'types':results,'distinct_witness_signatures':len(all_sigs),'signatures':[json.loads(x) for x in sorted(all_sigs)]}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/cycle_signature_witness_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'distinct_witness_signatures':len(all_sigs),'by_type':{k:sum('cycle_signature' in x for x in v) for k,v in results.items()}},indent=2,sort_keys=True))

if __name__=='__main__': main()
