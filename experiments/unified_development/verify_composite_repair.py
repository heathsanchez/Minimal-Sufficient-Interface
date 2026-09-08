"""Independent replay of finite constructor certificates; no hidden-world oracle."""
import hashlib
import itertools
import json
import sys

SOURCE_BLOB="294fc3a43c4d155290430777695add4d5de56cb7"

def enc(x):
    return json.dumps(x,sort_keys=True,separators=(",", ":")).encode()

def sha(x):
    return hashlib.sha256(enc(x)).hexdigest()

def words():
    return sorted((w for d in (1,2) for w in itertools.product((0,1),repeat=d)),
                  key=lambda w:(len(w),w))

def grammar():
    ws=words()
    out=[{"kind":"word","words":[list(w)]} for w in ws]
    out += [{"kind":"local","words":[]},{"kind":"state","words":[]}]
    pairs=[{"kind":"pair","words":[list(a),list(b)]}
           for a,b in itertools.combinations(ws,2)
           if (a,b)!=((0,),(1,))]
    pairs.sort(key=lambda s:(sum(map(len,s["words"])),s["words"]))
    return out+pairs

def cost(s):
    k=s["kind"]
    return (0,len(s["words"][0])) if k=="word" else (1,0) if k=="local" else (2,0) if k=="state" else (3,sum(map(len,s["words"])))

def arity(s):
    return 3 if s["kind"]=="state" else 2 if s["kind"] in ("local","pair") else 1

def observe(s,row):
    f,g,x,_=row
    if s["kind"]=="local": return (f[x],g[x])
    if s["kind"]=="state": return (x,f[x],g[x])
    values=[]
    for word in s["words"]:
        y=x
        for symbol in reversed(word):
            y=(f if symbol==0 else g)[y]
        values.append(y)
    return tuple(values)

def domain(n):
    maps=list(itertools.product(range(n),repeat=n))
    return [(f,g,x,None) for f in maps for g in maps for x in range(n)]

def replay_fit(data,s,n):
    seen={}
    first={}
    for i,row in enumerate(data):
        k=observe(s,row)
        if k in seen and seen[k]!=row[3]:
            return ("contradicted",[first[k],i])
        seen[k]=row[3]
        first.setdefault(k,i)
    if len(seen)!=n**arity(s):
        return ("incomplete",len(seen))
    return ("complete",[[list(k),seen[k]] for k in itertools.product(range(n),repeat=arity(s))])

def verify(cert,data):
    assert data and all(len(r)==4 for r in data)
    p=cert["payload"]
    n=p["n"]
    assert n==3 and p["kind"]=="finite_constructor"
    for f,g,x,y in data:
        assert len(f)==n and len(g)==n and type(x)==int and 0<=x<n
        assert all(type(v)==int and 0<=v<n for v in list(f)+list(g))
        assert type(y)==int and 0<=y<n
    assert cert["source_bound"]==3
    assert cert["source_blob"]==SOURCE_BLOB
    assert cert["identity"]==sha(p)
    assert cert["source"]==["call",cert["identity"]]
    assert cert["evidence_sha256"]==sha(data)
    failures=[]
    selected=None
    for tier in sorted(set(map(cost,grammar()))):
        survivors=[]
        for s in (s for s in grammar() if cost(s)==tier):
            status,value=replay_fit(data,s,n)
            if status=="contradicted":
                failures.append({"spec":s,"witness":value})
            else:
                assert status=="complete", "Unresolved extension"
                survivors.append({"spec":s,"table":value})
        if not survivors: continue
        signatures=set()
        for c in survivors:
            table={tuple(k):v for k,v in c["table"]}
            signatures.add(tuple(table[observe(c["spec"],r)] for r in domain(n)))
        assert len(signatures)==1, "Ambiguous extension"
        selected=min(survivors,key=lambda c:enc(c["spec"]))
        assert cert["equivalent_survivors"]==len(survivors)
        assert cert["cost"]==list(tier)
        break
    assert selected is not None
    assert p["spec"]==selected["spec"]
    assert p["table"]==selected["table"]
    assert cert["obstructions"]==failures
    return {"status":"FINITE_CERTIFICATE_PASS","cost":cert["cost"],
            "equivalent_survivors":cert["equivalent_survivors"],
            "obstructions":len(failures),"domain":n**(2*n+1)}

if __name__=="__main__":
    with open(sys.argv[1]) as f: cert=json.load(f)
    with open(sys.argv[2]) as f: evidence=json.load(f)
    print(json.dumps(verify(cert,evidence),sort_keys=True))
