"""Evidence-triggered extension of the frozen MSI constructor learner.

The frozen source is imported, not modified. The only new constructor syntax is
a pair of independently generated unary observations. No target pair is named.
A full training-table fit is not sufficient for installation: all least-cost
survivors must have the same extension over the declared finite input domain.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import frozen_constructor as C

SOURCE_BLOB = "294fc3a43c4d155290430777695add4d5de56cb7"
N = 3
WORDS = tuple(sorted(C.generated_words(2), key=lambda w: (len(w), w)))

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def specs():
    single = [{"kind": "word", "words": [list(w)]} for w in WORDS]
    local = [{"kind": "local", "words": []}]
    state = [{"kind": "state", "words": []}]
    pairs = [{"kind": "pair", "words": [list(a), list(b)]}
             for a,b in itertools.combinations(WORDS,2)
             if (a,b) != ((0,), (1,))]
    pairs.sort(key=lambda s:(sum(map(len,s["words"])), s["words"]))
    return single + local + state + pairs

GRAMMAR = specs()

def cost(spec):
    k = spec["kind"]
    if k == "word": return (0, len(spec["words"][0]))
    if k == "local": return (1,0)
    if k == "state": return (2,0)
    return (3,sum(map(len,spec["words"])))

def key(spec, row):
    f,g,x,_ = row
    kind = spec["kind"]
    if kind == "local": return (f[x],g[x])
    if kind == "state": return (x,f[x],g[x])
    return tuple(C.apply_word(tuple(w),f,g,x) for w in spec["words"])

def arity(spec):
    return 3 if spec["kind"]=="state" else 2 if spec["kind"] in ("local","pair") else 1

def validate(data, n=N):
    if not data: return "insufficient_evidence"
    for row in data:
        if len(row)!=4: return "malformed_evidence"
        f,g,x,y=row
        if len(f)!=n or len(g)!=n or not isinstance(x,int) or isinstance(x,bool) or not 0<=x<n:
            return "malformed_evidence"
        if any(not isinstance(v,int) or isinstance(v,bool) or not 0<=v<n for v in tuple(f)+tuple(g)):
            return "malformed_evidence"
        if y is None: return "insufficient_evidence"
        if not isinstance(y,int) or isinstance(y,bool) or not 0<=y<n:
            return "malformed_evidence"
    return None

def fit(data, spec, n=N):
    """Return a fit or a concrete collision; never treat missing keys as proof."""
    table={}
    first={}
    for i,row in enumerate(data):
        k=key(spec,row)
        if k in table and table[k]!=row[3]:
            return {"status":"contradicted","witness":[first[k],i]}
        table[k]=row[3]
        first.setdefault(k,i)
    if len(table)!=n**arity(spec):
        return {"status":"incomplete","observed":len(table)}
    return {"status":"complete","table":[[list(k),table[k]] for k in itertools.product(range(n),repeat=arity(spec))]}

def value(spec,table,row):
    return table[key(spec,row)]

def all_inputs(n=N):
    maps=C.all_maps(n)
    return [(f,g,x,None) for f in maps for g in maps for x in range(n)]

def search(data, n=N):
    bad=validate(data,n)
    if bad: return {"status":bad}
    failures=[]
    for tier in sorted(set(map(cost,GRAMMAR))):
        survivors=[]
        for spec in (s for s in GRAMMAR if cost(s)==tier):
            result=fit(data,spec,n)
            if result["status"]=="contradicted":
                failures.append({"spec":spec,"witness":result["witness"]})
            elif result["status"]=="incomplete":
                return {"status":"insufficient_evidence","candidate":spec,
                        "observed":result["observed"]}
            else:
                survivors.append({"spec":spec,"table":result["table"]})
        if not survivors: continue
        signatures=set()
        domain=all_inputs(n) if len(survivors)>1 else ()
        for candidate in survivors:
            table={tuple(k):v for k,v in candidate["table"]}
            signatures.add(tuple(value(candidate["spec"],table,r) for r in domain))
        if len(signatures)!=1:
            return {"status":"ambiguous_extension","cost":list(tier),
                    "survivors":len(survivors)}
        chosen=min(survivors,key=lambda c:canonical(c["spec"]))
        return {"status":"candidate","chosen":chosen,"obstructions":failures,
                "equivalent_survivors":len(survivors),"cost":list(tier)}
    return {"status":"grammar_insufficiency","obstructions":failures}

def acquire(data,n=N):
    result=search(data,n)
    if result["status"]!="candidate": return result
    payload={"kind":"finite_constructor","n":n,"spec":result["chosen"]["spec"],
             "table":result["chosen"]["table"]}
    identity=digest(payload)
    cert={"payload":payload,"identity":identity,"source":["call",identity],
          "source_bound":3,"source_blob":SOURCE_BLOB,
          "evidence_sha256":digest(data),"obstructions":result["obstructions"],
          "equivalent_survivors":result["equivalent_survivors"],
          "cost":result["cost"]}
    return {"status":"candidate","certificate":cert}

def execute(source,archive,row):
    if source is None or source[0]!="call" or len(source)!=2:
        return None
    cert=archive.get(source[1])
    if cert is None: return None
    if cert["identity"]!=digest(cert["payload"]) or cert["source"]!=source:
        raise ValueError("invalid retained capability")
    payload=cert["payload"]
    table={tuple(k):v for k,v in payload["table"]}
    return value(payload["spec"],table,row)
