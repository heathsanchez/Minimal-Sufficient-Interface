"""Reproduce frozen 8/12, then evaluate the post-discovery repair separately."""
import copy
import hashlib
import itertools
import json
import random
import subprocess
import sys
from pathlib import Path
import frozen_constructor as C
import composite_residual_repair as R

ROOT=Path(__file__).resolve().parent
SEED=20260908
NEW_SEED=20260910

def worlds(seed):
    rng=random.Random(seed)
    result=[]
    for i in range(4):
        table=tuple(rng.randrange(3) for _ in range(9))
        result.append((f"local_binary_{i}",lambda f,g,x,t=table:t[3*f[x]+g[x]]))
    for i in range(4):
        table=tuple(rng.randrange(3) for _ in range(27))
        result.append((f"local_state_{i}",lambda f,g,x,t=table:t[9*x+3*f[x]+g[x]]))
    for i in range(4):
        table=tuple(rng.randrange(3) for _ in range(9))
        result.append((f"composite_pair_{i}",lambda f,g,x,t=table:t[3*f[g[x]]+g[f[x]]]))
    return result

def score(oracle,model,source,archive):
    discovery=set(C.permutations(3))
    heldout=[(f,g,x,None) for f in C.all_maps(3) for g in C.all_maps(3)
             if not (f in discovery and g in discovery) for x in range(3)]
    predictions=[R.execute(source,archive,row) for row in heldout]
    truth=[oracle(f,g,x) for f,g,x,_ in heldout]
    coverage=sum(v is not None for v in predictions)
    errors=sum(v!=y for v,y in zip(predictions,truth) if v is not None)
    return {"coverage":coverage,"errors":errors,"heldout":len(truth),
            "exact":coverage==len(truth) and errors==0,
            "predictions":predictions,"truth":truth}

def evaluate(name,oracle,stem,save=True):
    discovery=C.permutations(3)
    data=C.rows(discovery,discovery,3,oracle)
    old_kind,old_model=C.choose_extension_family(data)
    old_predictions=[]
    heldout=[(f,g,x,None) for f in C.all_maps(3) for g in C.all_maps(3)
             if not (f in set(discovery) and g in set(discovery)) for x in range(3)]
    truth=[oracle(f,g,x) for f,g,x,_ in heldout]
    for row in heldout:
        try: old_predictions.append(C.predict(old_kind,old_model,row) if old_model is not None else None)
        except KeyError: old_predictions.append(None)
    old_coverage=sum(v is not None for v in old_predictions)
    old_errors=sum(v!=y for v,y in zip(old_predictions,truth) if v is not None)
    acquired=R.acquire(data)
    if acquired["status"]!="candidate":
        return {"name":name,"old_coverage":old_coverage,"old_errors":old_errors,
                "status":acquired["status"],"new_coverage":0,"new_errors":0}
    cert=acquired["certificate"]
    if save:
        ep=ROOT/(stem+"_evidence.json")
        cp=ROOT/(stem+"_certificate.json")
        ep.write_text(json.dumps(data,indent=2)+"\n")
        cp.write_text(json.dumps(cert,indent=2,sort_keys=True)+"\n")
        check=subprocess.run([sys.executable,str(ROOT/"verify_composite_repair.py"),str(cp),str(ep)],
                             text=True,capture_output=True,check=True)
        verification=json.loads(check.stdout)
    else:
        verification=None
    source=cert["source"]
    archive={cert["identity"]:cert}
    predictions=[R.execute(source,archive,row) for row in heldout]
    removed=[R.execute(source,{},row) for row in heldout]
    coverage=sum(v is not None for v in predictions)
    errors=sum(v!=y for v,y in zip(predictions,truth) if v is not None)
    assert all(v is None for v in removed)
    # The verifier may inspect the complete world only after held-out scoring.
    full=[R.execute(source,archive,row) for row in R.all_inputs()]
    full_truth=[oracle(f,g,x) for f,g,x,_ in R.all_inputs()]
    return {"name":name,"old_family":old_kind,"old_coverage":old_coverage,
            "old_errors":old_errors,"status":"certified","new_coverage":coverage,
            "new_errors":errors,"heldout":len(truth),
            "family":cert["payload"]["spec"]["kind"],"spec":cert["payload"]["spec"],
            "cost":cert["cost"],"obstructions":len(cert["obstructions"]),
            "equivalent_survivors":cert["equivalent_survivors"],
            "ablation_coverage":sum(v is not None for v in removed),
            "full_domain_errors":sum(a!=b for a,b in zip(full,full_truth)),
            "verification":verification,"certificate_id":cert["identity"]}

def main():
    results=[]
    for label,seed in (("original",SEED+1),("fresh",NEW_SEED)):
        for name,oracle in worlds(seed):
            r=evaluate(name,oracle,label+"_"+name)
            r["cohort"]=label
            results.append(r)
            print(label,name,r["old_coverage"],r["new_coverage"],r["new_errors"],r.get("spec"))
    negative=lambda f,g,x:(x+f[g[x]]+g[f[x]])%3
    negative_result=R.acquire(C.rows(C.permutations(3),C.permutations(3),3,negative))
    missing=R.acquire([(f,g,x,None) for f in C.permutations(3) for g in C.permutations(3) for x in range(3)])
    assert missing["status"]=="insufficient_evidence"
    summary={"protocol":"msi-composite-repair-v1-exploratory",
             "source_commit":"7f962c53da728045ea8455976b9a4ee93c953ead",
             "source_blob":R.SOURCE_BLOB,"original_seed":SEED,"fresh_seed":NEW_SEED,
             "results":results,"negative":{"status":negative_result["status"]},
             "missing_feedback":{"status":missing["status"]},
             "scope":"finite Python certification; not unrestricted genesis or joint confirmation"}
    (ROOT/"results.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print("NEGATIVE",negative_result["status"])
    print("ORIGINAL",sum(r["new_coverage"]==2079 and r["new_errors"]==0 for r in results if r["cohort"]=="original"),"/12")
    print("FRESH",sum(r["new_coverage"]==2079 and r["new_errors"]==0 for r in results if r["cohort"]=="fresh"),"/12")
    print("RESULTS_SHA256",hashlib.sha256((ROOT/"results.json").read_bytes()).hexdigest())

if __name__=="__main__":
    main()
