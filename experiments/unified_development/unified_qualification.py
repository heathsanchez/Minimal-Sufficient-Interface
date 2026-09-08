"""Small integration of pinned MSI acquisition, replay, and capability reuse.

The world supplies only observations through step(). The constructor grammar,
independent certificate verifier, and feedback archive are imported unchanged.
This is a finite functional-world qualification, not an ARC3 environment.
"""
from __future__ import annotations
import copy
import hashlib
import itertools
import json
import sys
from pathlib import Path
import frozen_constructor as C
import composite_residual_repair as R
import verify_composite_repair as V
import closed_feedback_v2 as F

SOURCE_BLOBS = {
    "frozen_constructor.py": "294fc3a43c4d155290430777695add4d5de56cb7",
    "composite_residual_repair.py": "031ab9ead59e5fb9d5d91c3f8b7a2346464a0be1",
    "verify_composite_repair.py": "19a41f7adda6132fc107b8c77fcfc5e46021927a",
    "closed_feedback_v2.py": "32dd8a45394b7441e7f08be7c128f1691ff941c0",
}

def verify_sources(directory=None):
    for name, expected in SOURCE_BLOBS.items():
        module = {
            "frozen_constructor.py": C,
            "composite_residual_repair.py": R,
            "verify_composite_repair.py": V,
            "closed_feedback_v2.py": F,
        }[name]
        data = Path(module.__file__).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            raise ValueError("Source mismatch: " + name)

class QueryWorld:
    """The target function is accessible only through the external step."""
    def __init__(self, oracle):
        self._oracle = oracle
        self.last = None
        self.observation_space = self.frame()
    def frame(self):
        return {"frame": self.last, "levels_completed": 0,
                "state": "NOT_FINISHED", "available_actions": ["query"]}
    def reset(self):
        self.last = None
        return self.frame()
    def step(self, action):
        f,g,x = action
        self.last = [list(f),list(g),x,self._oracle(f,g,x)]
        return self.frame()
    def close(self):
        return None

def acquire_label(factory, query, archive):
    """Two fresh actual replays; a stored claim cannot supply an oracle label."""
    trial = F.replay(factory, (query,), None, 1)
    proof = F.replay(factory, (query,), trial["final_sha256"], 1)
    if (trial["status"] != "OBSERVED" or proof["status"] != "OBSERVED"
            or proof["initial_sha256"] != trial["initial_sha256"]
            or proof["executed"] != (query,)
            or proof["observations"] != trial["observations"]):
        raise ValueError("Replay mismatch")
    before, after = trial["observations"]
    row = after["frame"]
    if row is None or len(row) != 4 or row[3] is None:
        raise ValueError("Missing acquisition label")
    archive.retain((), before, query, after)
    archive.install(trial["initial_sha256"], (query,), trial["final_sha256"], proof)
    return (tuple(row[0]),tuple(row[1]),row[2],row[3])

def candidate_models(data):
    """Keep partial candidate models as hypotheses, not certified capabilities."""
    if not data: return []
    models=[]
    for spec in R.GRAMMAR:
        result=R.fit(data,spec)
        if result["status"] == "contradicted": continue
        table={R.key(spec,row):row[3] for row in data}
        models.append((spec,table))
    return models

def choose_probe(remaining, models):
    """Prefer a deciding disagreement; unknown predictions remain unknown."""
    if not models: return remaining[0]
    def priority(query):
        row=query+(None,)
        known={table[R.key(spec,row)] for spec,table in models
               if R.key(spec,row) in table}
        return (len(known)>1,len(known),-sum(R.key(spec,row) not in table
                                             for spec,table in models))
    return max(remaining,key=priority)

def acquire_world(factory, feedback=True):
    archive=F.FeedbackArchive()
    remaining=[(f,g,x) for f in C.permutations(3)
               for g in C.permutations(3) for x in range(3)]
    data=[]; order=[]; residuals=[]
    while remaining:
        models=candidate_models(data) if feedback else []
        query=choose_probe(remaining,models)
        remaining.remove(query)
        order.append(query)
        data.append(acquire_label(factory,query,archive))
        if feedback:
            result=R.search(data)
            if result["status"]=="grammar_insufficiency":
                residuals.append({"rows":len(data),"status":result["status"]})
    proposal=R.acquire(data)
    if proposal["status"]!="candidate":
        return {"status":proposal["status"],"evidence":data,"archive":{},
                "order":order,"residuals":residuals}
    cert=proposal["certificate"]
    verdict=V.verify(cert,data)
    if verdict["status"]!="FINITE_CERTIFICATE_PASS":
        raise ValueError("Independent verification failed")
    if V.verify(cert,data)["status"]!="FINITE_CERTIFICATE_PASS":
        raise ValueError("Promotion replay failed")
    installed={cert["identity"]:copy.deepcopy(cert)}
    return {"status":"FINITE_CERTIFICATE_PASS","evidence":data,
            "archive":installed,"source":cert["source"],"certificate":cert,
            "order":order,"residuals":residuals,"verdict":verdict,
            "acquisition_actions":len(data)*2,
            "verified_operations":archive.snapshot()["options"]}

def plan(source,archive,choices,goal):
    """A prediction is only a planning hypothesis; the environment decides."""
    for query in choices:
        value=R.execute(source,archive,query+(None,))
        if value==goal:
            return query
    return None

def evaluate_planning(oracle, acquired):
    """One action per task, with actual hidden-world feedback after selection."""
    maps=C.all_maps(3); discovery=set(C.permutations(3))
    baseline=developed=available=0
    for f in maps:
        for g in maps:
            if f in discovery and g in discovery: continue
            choices=[(f,g,x) for x in range(3)]
            goal=2
            baseline+=oracle(*choices[0])==goal
            selected=plan(acquired.get("source"),acquired["archive"],choices,goal)
            if selected is not None:
                available+=1
                developed+=oracle(*selected)==goal
    return {"tasks":len(maps)**2-len(discovery)**2,
            "baseline_wins":baseline,"planned_wins":developed,
            "planned_coverage":available}

def worlds(seed):
    import random
    rng=random.Random(seed)
    out=[]
    for i in range(4):
        table=tuple(rng.randrange(3) for _ in range(9))
        out.append(("local_binary_"+str(i),lambda f,g,x,t=table:t[3*f[x]+g[x]]))
    for i in range(4):
        table=tuple(rng.randrange(3) for _ in range(27))
        out.append(("local_state_"+str(i),lambda f,g,x,t=table:t[9*x+3*f[x]+g[x]]))
    for i in range(4):
        table=tuple(rng.randrange(3) for _ in range(9))
        out.append(("composite_pair_"+str(i),lambda f,g,x,t=table:t[3*f[g[x]]+g[f[x]]]))
    return out

def evaluate_world(name,oracle):
    result=acquire_world(lambda:QueryWorld(oracle))
    cert=result["certificate"]
    old_kind,old_model=C.choose_extension_family(result["evidence"])
    heldout=[r for r in R.all_inputs()
             if not (r[0] in C.permutations(3) and r[1] in C.permutations(3))]
    def old_prediction(row):
        if old_model is None:return None
        try:return C.predict(old_kind,old_model,row)
        except KeyError:return None
    old=[old_prediction(r) for r in heldout]
    new=[R.execute(result["source"],result["archive"],r) for r in heldout]
    truth=[oracle(f,g,x) for f,g,x,_ in heldout]
    return {"name":name,"old_exact":old==truth,"new_exact":new==truth,
            "old_coverage":sum(v is not None for v in old),
            "new_coverage":sum(v is not None for v in new),
            "errors":sum(v!=t for v,t in zip(new,truth) if v is not None),
            "family":cert["payload"]["spec"]["kind"],"spec":cert["payload"]["spec"],
            "obstructions":len(cert["obstructions"]),
            "planning":evaluate_planning(oracle,result),
            "acquisition_actions":result["acquisition_actions"],
            "verified_operations":result["verified_operations"],
            "result":result}
