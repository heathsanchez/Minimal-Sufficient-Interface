import ast
import itertools
import random
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'orbit': ROOT / 'experiments/natural_orbit_recursive_genesis_v3b.py',
    'boolean': ROOT / 'tests/test_blind_recursive_cross_grammar_genesis.py',
    'category': ROOT / 'tests/test_final_boss_task_only_category_genesis.py',
    'group': ROOT / 'tests/test_final_leap_cross_lens_rank2_world.py',
    'lean': ROOT / 'experiments/lean_external_capability_synthesis.py',
}


def names_load(node):
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}


def names_store(node):
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Param))}


def statement_graph(path):
    tree=ast.parse(path.read_text())
    stmts=[x for x in ast.walk(tree) if isinstance(x, ast.stmt)]
    stmts.sort(key=lambda x:(getattr(x,'lineno',0),getattr(x,'col_offset',0),type(x).__name__))
    idx={id(x):i for i,x in enumerate(stmts)}
    edges=set()

    def add_block(body, inherited=None):
        body=[x for x in body if isinstance(x, ast.stmt)]
        for a,b in zip(body,body[1:]): edges.add((idx[id(a)],idx[id(b)]))
        if inherited is not None and body: edges.add((inherited,idx[id(body[0])]))
        last={}
        for s in body:
            si=idx[id(s)]
            # def-use is computed before identifiers are erased; identifiers never enter motifs.
            for name in names_load(s):
                if name in last: edges.add((last[name],si))
            for name in names_store(s): last[name]=si
            child_blocks=[]
            if isinstance(s,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.For,ast.AsyncFor,ast.While,ast.If,ast.With,ast.AsyncWith)):
                child_blocks += [getattr(s,'body',[]),getattr(s,'orelse',[])]
            elif isinstance(s,ast.Try):
                child_blocks += [s.body,s.orelse,s.finalbody] + [h.body for h in s.handlers]
            elif isinstance(s,ast.Match): child_blocks += [c.body for c in s.cases]
            for block in child_blocks:
                if block: add_block(block,si)
    add_block(tree.body)
    live={u for e in edges for u in e}
    remap={old:i for i,old in enumerate(sorted(live))}
    return len(live), {(remap[a],remap[b]) for a,b in edges if a in live and b in live}


def canon(k, es):
    best=None
    for p in itertools.permutations(range(k)):
        s=''.join('1' if (p[i],p[j]) in es else '0' for i in range(k) for j in range(k) if i!=j)
        if best is None or s<best:best=s
    return best


def graphlets(n, es, k, cap=12000):
    und=[set() for _ in range(n)]
    for a,b in es: und[a].add(b);und[b].add(a)
    subsets=set()
    # Deterministic connected-set expansion; capped before canonicalization.
    for root in range(n):
        stack=[frozenset((root,))]
        seen={stack[0]}
        while stack and len(subsets)<cap:
            cur=stack.pop()
            if len(cur)==k:
                subsets.add(tuple(sorted(cur)));continue
            frontier=set()
            for u in cur: frontier |= und[u]
            for v in sorted(frontier-cur, reverse=True):
                nxt=frozenset(set(cur)|{v})
                if nxt not in seen:
                    seen.add(nxt);stack.append(nxt)
        if len(subsets)>=cap:break
    out=defaultdict(list)
    for subset in subsets:
        mp={old:i for i,old in enumerate(subset)}
        sub={(mp[a],mp[b]) for a,b in es if a in mp and b in mp}
        out[canon(k,sub)].append(set(subset))
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
    base=total(); losses=[base-total(v) for v in range(n)]
    m=max(losses) if losses else 0
    return {i for i,x in enumerate(losses) if x==m and x>0},m


def random_order_graph(n,m,rng):
    order=list(range(n));rng.shuffle(order);pos={v:i for i,v in enumerate(order)}
    poss=[(a,b) for a in range(n) for b in range(n) if pos[a]<pos[b]]
    rng.shuffle(poss);return set(poss[:min(m,len(poss))])


def evaluate_holdout(graphs,holdout,k=5,controls=80):
    train_maps=[graphlets(n,e,k) for name,(n,e) in graphs.items() if name!=holdout]
    common=set.intersection(*(set(x) for x in train_maps)) if train_maps else set()
    hn,he=graphs[holdout];hm=graphlets(hn,he,k);matched=common & set(hm)
    bridges,loss=reachability_score(hn,he)
    bridge_hits=sum(1 for motif in matched for occ in hm[motif] if occ & bridges)
    rng=random.Random(20260829+sum(map(ord,holdout)));ctrl=[]
    for _ in range(controls):
        rm=graphlets(hn,random_order_graph(hn,len(he),rng),k)
        ctrl.append(len(common & set(rm)))
    ctrl.sort();p95=ctrl[int(.95*(len(ctrl)-1))] if ctrl else 0
    return {'train_common':len(common),'heldout_matches':len(matched),'bridge_nodes':len(bridges),'bridge_loss':loss,'bridge_hits':bridge_hits,'random_p95':p95,'pass':bool(matched) and bridge_hits>0 and len(matched)>p95}


def main():
    graphs={name:statement_graph(path) for name,path in SOURCES.items()}
    for name,(n,e) in graphs.items():
        print(f'GRAPH {name} nodes={n} edges={len(e)}');assert n>=5 and len(e)>=4,(name,n,len(e))
    results={h:evaluate_holdout(graphs,h) for h in graphs}
    for h,r in results.items():print(f'HOLDOUT {h} {r}')
    passed=sum(r['pass'] for r in results.values());print(f'LEAVE_ONE_OUT passes={passed}/{len(results)}')
    assert passed==len(results),results
    print('IDENTIFIERS_ERASED_BEFORE_MOTIF_MINING=PASS')
    print('HELDOUT_MOTIF_BEATS_RANDOM_TOPOLOGY=PASS')
    print('HELDOUT_MOTIF_OVERLAPS_CAUSAL_BRIDGE=PASS')
    print('CROSS_DOMAIN_UNIVERSAL_MOTIFS_V2=PASS')

if __name__=='__main__':main()
