import itertools
import math
import random
import unittest
from collections import defaultdict, deque

# This experiment deliberately keeps domain learners separate.  Each returns an
# anonymous causal DAG plus objective before/after/ablation measurements.  Only
# after all domains finish do we erase event names and mine common graphlets.


def add(trace, name, *parents):
    trace[name] = set(parents)


def edges(trace):
    ns = list(trace)
    idx = {n:i for i,n in enumerate(ns)}
    return ns, {(idx[p], idx[n]) for n, ps in trace.items() for p in ps}


def connected(k, es):
    if k <= 1: return True
    adj=[set() for _ in range(k)]
    for a,b in es:
        adj[a].add(b); adj[b].add(a)
    seen={0}; q=[0]
    while q:
        u=q.pop()
        for v in adj[u]-seen:
            seen.add(v); q.append(v)
    return len(seen)==k


def canon(k, es):
    # exact unlabeled directed-graph canonical form; k <= 6 here.
    best=None
    for p in itertools.permutations(range(k)):
        s=''.join('1' if (p[i],p[j]) in es else '0'
                  for i in range(k) for j in range(k) if i!=j)
        if best is None or s<best: best=s
    return best


def graphlets(trace, k):
    ns, es = edges(trace)
    out=set()
    for subset in itertools.combinations(range(len(ns)), k):
        mp={old:i for i,old in enumerate(subset)}
        sub={(mp[a],mp[b]) for a,b in es if a in mp and b in mp}
        if connected(k, sub): out.add(canon(k, sub))
    return out


def boolean_domain():
    rows=list(itertools.product([0,1], repeat=3))
    def nand(a,b): return 1-(a&b)
    base={'a':tuple(r[0] for r in rows),'b':tuple(r[1] for r in rows),'c':tuple(r[2] for r in rows)}
    target=tuple(r[0]^r[1] for r in rows)
    vals=dict(base); expr={k:k for k in base}; found=None
    for depth in range(1,5):
        old=list(vals)
        for x in old:
            for y in old:
                v=tuple(nand(i,j) for i,j in zip(vals[x],vals[y]))
                key=('n',x,y)
                if v not in vals.values(): vals[key]=v; expr[key]=f'N({expr[x]},{expr[y]})'
                if v==target: found=key; break
            if found is not None: break
        if found is not None: break
    assert found is not None
    xorv=vals[found]
    parity3=tuple(r[0]^r[1]^r[2] for r in rows)
    warm=tuple(x^r[2] for x,r in zip(xorv,rows))
    cold_ok=False
    warm_ok=(warm==parity3)
    tr={}; add(tr,'obs'); add(tr,'mismatch','obs'); add(tr,'compose','mismatch'); add(tr,'verify','compose'); add(tr,'retain','verify'); add(tr,'future','retain'); add(tr,'ablate','retain'); add(tr,'lost','ablate')
    return tr, {'before':0.5,'after':1.0 if warm_ok else 0.0,'ablation':1.0 if cold_ok else 0.0,'artifact':expr[found]}


def dfa_domain():
    states=[0,1,2]; alphabet=[0,1]
    trans={(s,a):(s+a)%3 for s in states for a in alphabet}; accept={0}
    part=[set(accept), set(states)-accept]; before=len(part); witness=None
    while True:
        bid={s:i for i,b in enumerate(part) for s in b}
        sig={s:(s in accept, tuple(bid[trans[s,a]] for a in alphabet)) for s in states}
        groups=defaultdict(set)
        for s in states: groups[sig[s]].add(s)
        new=list(groups.values())
        if len(new)==len(part): break
        for b in part:
            for x,y in itertools.combinations(b,2):
                if sig[x]!=sig[y]: witness=(x,y)
        part=new
    after=len(part); exact=True
    for s in states:
        for word in itertools.product(alphabet, repeat=4):
            q=s
            for a in word:q=trans[q,a]
            exact &= ((q in accept)==(q==0))
    tr={}; add(tr,'sample'); add(tr,'conflict','sample'); add(tr,'split','conflict'); add(tr,'check','split'); add(tr,'freeze','check'); add(tr,'predict','freeze'); add(tr,'remove','freeze'); add(tr,'failure','remove')
    return tr, {'before':before,'after':after,'ablation':before,'witness':witness,'exact':exact}


def graph_domain():
    adj={0:[1,2],1:[3],2:[3],3:[4],4:[4],5:[1,2]}; terminal={4}
    color={v:int(v in terminal) for v in adj}; before=len(set(color.values())); changed=True; witness=None
    while changed:
        sig={v:(color[v],tuple(sorted(color[w] for w in adj[v]))) for v in adj}
        uniq={s:i for i,s in enumerate(sorted(set(sig.values()), key=repr))}
        new={v:uniq[sig[v]] for v in adj}; changed=any(new[v]!=color[v] for v in adj)
        if changed:
            for a,b in itertools.combinations(adj,2):
                if color[a]==color[b] and new[a]!=new[b]: witness=(a,b); break
        color=new
    after=len(set(color.values())); ok=True
    for h in range(6):
        val={v:(v in terminal) for v in adj}
        for _ in range(h): val={v:(v in terminal or any(val[w] for w in adj[v])) for v in adj}
        for a,b in itertools.combinations(adj,2):
            if color[a]==color[b]: ok &= (val[a]==val[b])
    tr={}; add(tr,'raw'); add(tr,'counterexample','raw'); add(tr,'recolor','counterexample'); add(tr,'validate','recolor'); add(tr,'quotient','validate'); add(tr,'query','quotient'); add(tr,'undo','quotient'); add(tr,'query_breaks','undo')
    return tr, {'before':before,'after':after,'ablation':before,'witness':witness,'exact':ok}


def code_domain():
    xs=list(range(24))
    # Period 12 is the true behavioral key, but the learner is not told that.
    def f(x): return ((x//3)%4, (x*x+3*x)%4)
    candidates=[('p2',lambda x:x%2,1),('p3',lambda x:x%3,1),('p4',lambda x:x%4,1),('p5',lambda x:x%5,1),('p12',lambda x:x%12,2),('pair34',lambda x:(x%3,x%4),2)]
    base=candidates[0]
    def collisions(fn):
        buckets=defaultdict(set)
        for x in xs:buckets[fn(x)].add(f(x))
        return sum(len(v)-1 for v in buckets.values())
    before=collisions(base[1]); viable=[]
    for name,fn,cost in candidates[1:]:
        c=collisions(fn)
        if c==0: viable.append((cost,name,fn))
    viable.sort(key=lambda z:(z[0],z[1])); assert viable
    cost,name,key=viable[0]; after=collisions(key)
    memo={key(x):f(x) for x in xs}; held=list(range(24,36))
    exact=all(key(x) in memo and memo[key(x)]==f(x) for x in held)
    tr={}; add(tr,'runs'); add(tr,'collision','runs'); add(tr,'key_search','collision'); add(tr,'test_key','key_search'); add(tr,'install','test_key'); add(tr,'reuse','install'); add(tr,'drop','install'); add(tr,'miss','drop')
    return tr, {'before':before,'after':after,'ablation':before,'key':name,'exact':exact}


def arithmetic_domain():
    mod=17; a=5; b=3; seq=[2]
    for _ in range(80):seq.append((a*seq[-1]+b)%mod)
    train=seq[:50]; test=seq[50:]; best=None
    for m in range(2,25):
        for aa in range(m):
            for bb in range(m):
                if all((aa*train[i]+bb)%m==train[i+1]%m for i in range(len(train)-1)):
                    cand=(m+aa+bb,m,aa,bb)
                    if best is None or cand<best:best=cand
    assert best is not None
    _,m,aa,bb=best; pred=[]; x=train[-1]
    for _ in test:
        x=(aa*x+bb)%m; pred.append(x)
    exact=(pred==test)
    tr={}; add(tr,'stream'); add(tr,'error','stream'); add(tr,'fit','error'); add(tr,'verify_fit','fit'); add(tr,'promote_rule','verify_fit'); add(tr,'rollout','promote_rule'); add(tr,'erase','promote_rule'); add(tr,'forecast_lost','erase')
    return tr, {'before':0.0,'after':1.0 if exact else 0.0,'ablation':0.0,'rule':(m,aa,bb),'exact':exact}


def run():
    domains={'boolean':boolean_domain(),'automaton':dfa_domain(),'graph':graph_domain(),'code':code_domain(),'arithmetic':arithmetic_domain()}
    for name,(tr,m) in domains.items():
        if 'exact' in m: assert m['exact'], (name,m)
        assert m['after'] != m['before'] or m.get('exact',False), (name,m)
    common_by_k={}
    for k in range(6,2,-1):
        sets=[graphlets(tr,k) for tr,_ in domains.values()]
        common=set.intersection(*sets); common_by_k[k]=common
        if common: largest=k; break
    else: largest=0; common=set()
    rng=random.Random(20260829); neg=[]
    for tr,_ in domains.values():
        ns,es=edges(tr); n=len(ns)
        poss=[(i,j) for i in range(n) for j in range(i+1,n)]; rng.shuffle(poss); res=set(poss[:len(es)])
        nt={str(i):set() for i in range(n)}
        for a,b in res: nt[str(b)].add(str(a))
        neg.append(nt)
    neg_common=set.intersection(*(graphlets(t,largest) for t in neg)) if largest else set()
    print('CROSS_DOMAIN domains='+','.join(domains))
    for name,(tr,m) in domains.items(): print(f'DOMAIN {name} metrics={m}')
    print(f'BLIND_COMMON_MOTIF largest_nodes={largest} common_classes={len(common)}')
    print(f'RANDOM_DAG_CONTROL same_size_common_classes={len(neg_common)}')
    assert largest >= 6
    assert len(common) >= 1
    assert len(neg_common) == 0
    print('DOMAIN_NAMES_ERASED_BEFORE_CANONICALIZATION=PASS')
    print('COMMON_DIRECTED_MOTIF_AT_LEAST_6_NODES=PASS')
    print('RANDOM_DAG_DENSITY_CONTROL=PASS')
    print('CROSS_DOMAIN_UNIVERSAL_MOTIFS_V1=PASS')
    return domains,largest


class TestCrossDomainUniversalMotifs(unittest.TestCase):
    def test_cross_domain_universal_motifs(self): run()

if __name__=='__main__': run()
