import ast
import itertools
import random
from pathlib import Path
from collections import defaultdict, deque

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'orbit': ROOT / 'experiments/natural_orbit_recursive_genesis_v3b.py',
    'boolean': ROOT / 'tests/test_blind_recursive_cross_grammar_genesis.py',
    'category': ROOT / 'tests/test_final_boss_task_only_category_genesis.py',
    'group': ROOT / 'tests/test_final_leap_cross_lens_rank2_world.py',
    'lean': ROOT / 'experiments/lean_external_capability_synthesis.py',
}


def local_call_graph(path):
    tree = ast.parse(path.read_text())
    defs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, node)
    names = sorted(defs)
    idx = {n:i for i,n in enumerate(names)}
    edges=set()
    for name,node in defs.items():
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            callee=None
            if isinstance(sub.func, ast.Name): callee=sub.func.id
            elif isinstance(sub.func, ast.Attribute): callee=sub.func.attr
            if callee in idx and callee != name:
                edges.add((idx[name],idx[callee]))
    # retain only non-isolated nodes; names are discarded immediately after this
    live={u for e in edges for u in e}
    remap={old:i for i,old in enumerate(sorted(live))}
    return len(live), {(remap[a],remap[b]) for a,b in edges if a in live and b in live}


def weak_connected(k, es):
    if k < 2:return True
    adj=[set() for _ in range(k)]
    for a,b in es: adj[a].add(b);adj[b].add(a)
    seen={0};q=[0]
    while q:
        u=q.pop()
        for v in adj[u]-seen:seen.add(v);q.append(v)
    return len(seen)==k


def canon(k, es):
    best=None
    for p in itertools.permutations(range(k)):
        s=''.join('1' if (p[i],p[j]) in es else '0' for i in range(k) for j in range(k) if i!=j)
        if best is None or s<best:best=s
    return best


def graphlets(n, es, k):
    out=defaultdict(list)
    if n<k:return out
    for subset in itertools.combinations(range(n),k):
        mp={old:i for i,old in enumerate(subset)}
        sub={(mp[a],mp[b]) for a,b in es if a in mp and b in mp}
        if weak_connected(k,sub):out[canon(k,sub)].append(set(subset))
    return out


def reachability_score(n, es):
    def total(skip=None):
        adj=[[] for _ in range(n)]
        for a,b in es:
            if a==skip or b==skip:continue
            adj[a].append(b)
        s=0
        for src in range(n):
            if src==skip:continue
            seen={src};q=[src]
            while q:
                u=q.pop()
                for v in adj[u]:
                    if v not in seen and v!=skip:seen.add(v);q.append(v)
            s += len(seen)-1
        return s
    base=total()
    losses=[base-total(v) for v in range(n)]
    m=max(losses) if losses else 0
    return {i for i,x in enumerate(losses) if x==m and x>0},m


def random_order_graph(n, m, rng):
    order=list(range(n));rng.shuffle(order)
    pos={v:i for i,v in enumerate(order)}
    poss=[(a,b) for a in range(n) for b in range(n) if pos[a]<pos[b]]
    rng.shuffle(poss)
    return set(poss[:min(m,len(poss))])


def evaluate_holdout(graphs, holdout, k=5, controls=200):
    train=[g for name,g in graphs.items() if name!=holdout]
    train_maps=[graphlets(n,e,k) for n,e in train]
    common=set.intersection(*(set(x) for x in train_maps)) if train_maps else set()
    hn,he=graphs[holdout]; hm=graphlets(hn,he,k)
    matched=common & set(hm)
    bridges,loss=reachability_score(hn,he)
    bridge_hits=sum(1 for motif in matched for occ in hm[motif] if occ & bridges)
    rng=random.Random(20260829 + sum(map(ord,holdout)))
    ctrl=[]
    for _ in range(controls):
        re=random_order_graph(hn,len(he),rng)
        rm=graphlets(hn,re,k)
        ctrl.append(len(common & set(rm)))
    ctrl.sort(); p95=ctrl[int(.95*(len(ctrl)-1))] if ctrl else 0
    return {
        'train_common':len(common), 'heldout_matches':len(matched),
        'bridge_nodes':len(bridges), 'bridge_loss':loss, 'bridge_hits':bridge_hits,
        'random_p95':p95, 'pass': bool(matched) and bridge_hits>0 and len(matched)>p95,
    }


def main():
    graphs={name:local_call_graph(path) for name,path in SOURCES.items()}
    for name,(n,e) in graphs.items():
        print(f'GRAPH {name} nodes={n} edges={len(e)}')
        assert n>=5 and len(e)>=4, (name,n,len(e))
    results={h:evaluate_holdout(graphs,h) for h in graphs}
    for h,r in results.items(): print(f'HOLDOUT {h} {r}')
    passed=sum(r['pass'] for r in results.values())
    print(f'LEAVE_ONE_OUT passes={passed}/{len(results)}')
    # Strong gate: recurrence must generalize to every sealed family, not one lucky holdout.
    assert passed==len(results), results
    print('IDENTIFIERS_ERASED_BEFORE_MOTIF_MINING=PASS')
    print('HELDOUT_MOTIF_BEATS_RANDOM_TOPOLOGY=PASS')
    print('HELDOUT_MOTIF_OVERLAPS_CAUSAL_BRIDGE=PASS')
    print('CROSS_DOMAIN_UNIVERSAL_MOTIFS_V2=PASS')

if __name__=='__main__':main()
