#!/usr/bin/env python3
"""Source-derived, finite discriminator for the V3 induction calibration.

This is NOT a verified induction-critic constructor. It reads the frozen
development function equations and uses their extracted operations to
falsify candidate accumulator orientations before protected tasks are read.
"""
import hashlib, itertools, json, pathlib, re
ROOT=pathlib.Path(__file__).parent
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def definition(source,name):
    pattern=r"(?m)^def "+re.escape(name)+r"\\b[\\s\\S]*?(?=^def |^-- Protected|^-- Development|^end |\\Z)"
    m=re.search(pattern,source,re.M)
    if not m: raise ValueError("missing frozen definition "+name)
    return m.group(0)
def interpret_pair(source,plain,accum):
    p=definition(source,plain);a=definition(source,accum)
    # Exact, frozen-source-extracted structural interpreter for list cons,
    # singleton append, and accumulator cons. Reject unknown syntax.
    if not re.search(r"\\| \\[\\] => \\[\\]",p): raise ValueError("unsupported plain base")
    if not re.search(r"\\| \\[\\] => acc",a): raise ValueError("unsupported accumulator base")
    if not re.search(r"\\| x :: xs => "+re.escape(plain)+r" xs \\+\\+ \\[x\\]",p):
        raise ValueError("unsupported plain recursion")
    if not re.search(r"\\| x :: xs => "+re.escape(accum)+r" \\(x :: acc\\) xs",a):
        raise ValueError("unsupported accumulator recursion")
    def ordinary(xs):
        if not xs:return ()
        return ordinary(xs[1:])+(xs[0],)
    def helper(acc,xs):
        if not xs:return acc
        return helper((xs[0],)+acc,xs[1:])
    return ordinary,helper
def run():
    source=(ROOT/"FrozenSource.lean").read_text()
    dev=json.loads((ROOT/"development_cases.json").read_text())
    assert len(dev["development"])==1
    case=dev["development"][0]
    ordinary,helper=interpret_pair(source,case["plain"],case["accumulator"])
    # The calibration includes noncommutative, nonempty accumulator values.
    samples=tuple(itertools.product((1,2),repeat=2))
    accs=((1,),(2,),(1,2))
    scores={}
    counterexamples={}
    for side in ("left","right"):
        mismatches=[]
        for xs in samples:
            for acc in accs:
                expected=acc+ordinary(xs) if side=="left" else ordinary(xs)+acc
                if helper(acc,xs)!=expected:
                    mismatches.append({"xs":xs,"acc":acc,"actual":helper(acc,xs),"candidate":expected})
        scores[side]=len(mismatches)
        counterexamples[side]=mismatches[:1]
    winners=[side for side,miss in scores.items() if miss==0]
    selection={"status":"CANDIDATE_FINITE_DISCRIMINATOR" if len(winners)==1 else "UNKNOWN_CHOICE",
      "orientation":winners[0] if len(winners)==1 else None,
      "sample_counts":len(samples)*len(accs),
      "mismatches":scores,"counterexamples":counterexamples,
      "scope":"exact parsed development recursion, finite lists and nonempty accumulators"}
    receipt={"source_sha256":hashlib.sha256((ROOT/"FrozenSource.lean").read_bytes()).hexdigest(),
      "development_sha256":hashlib.sha256((ROOT/"development_cases.json").read_bytes()).hexdigest(),
      "selection":selection}
    receipt["digest"]=digest(receipt)
    out=ROOT/"results";out.mkdir(exist_ok=True)
    (out/"pre_holdout_freeze.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\\n")
    held=json.loads((ROOT/"protected_cases.json").read_text())
    evidence={"status":selection["status"],"orientation":selection["orientation"],
      "frozen_receipt":receipt["digest"],
      "protected_positive_count":len(held["heldout"]),
      "protected_negative_count":len(held["negative"]),
      "protected_proofs_attempted":0,"lean_proofs_generated":0,
      "claims":{"finite_source_derived_orientation":"CANDIDATE",
                "universal_lean_calibration":"WARRANTED_IN_SEPARATE_PINNED_RUN",
                "automatic_induction_critic":"UNKNOWN",
                "protected_transfer":"UNKNOWN"},
      "next_required":"Source-derived general invariant AST and Lean proof-producing compiler"}
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\\n")
    print(json.dumps(evidence,sort_keys=True))
if __name__=="__main__":run()
