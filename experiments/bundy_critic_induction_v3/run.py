#!/usr/bin/env python3
"""V3 scoped critic experiment. Uses only frozen development metadata before freeze."""
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).parent
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def candidates():
    # Generic expression shapes; none contains task or operator names.
    return [{"kind":"fold_accumulator","orientation":side,"abstract":True} for side in ("left","right")]
def run():
    dev=json.loads((ROOT/"development_cases.json").read_text())
    assert len(dev["development"])==1
    # Only the development instance is observed before selection.
    # No synthetic oracle: a single example cannot distinguish every monoid
    # orientation without a checked noncommutative observation.
    pool=candidates()
    selection={"status":"UNKNOWN_CHOICE","candidate_count":len(pool),
      "candidates":pool,"reason":"No source-extracted certified invariant-discriminator or proof-producing compiler exists yet."}
    receipt={"source_sha256":hashlib.sha256((ROOT/"FrozenSource.lean").read_bytes()).hexdigest(),
      "development_sha256":hashlib.sha256((ROOT/"development_cases.json").read_bytes()).hexdigest(),
      "selection":selection}
    receipt["digest"]=digest(receipt)
    out=ROOT/"results";out.mkdir(exist_ok=True)
    (out/"pre_holdout_freeze.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    # Protected tasks are loaded only after the receipt is written.
    held=json.loads((ROOT/"protected_cases.json").read_text())
    evidence={"status":"UNKNOWN_CHOICE","frozen_receipt":receipt["digest"],
      "protected_positive_count":len(held["heldout"]),"protected_negative_count":len(held["negative"]),
      "protected_proofs_attempted":0,"lean_proofs_generated":0,
      "claim":"No induction critic has been autonomously constructed or independently qualified.",
      "next_required":"Extract a genuine source-bound residual discriminator, construct invariant AST, generate proof terms and run pinned Lean."}
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print(json.dumps(evidence,sort_keys=True))
if __name__=="__main__":run()
