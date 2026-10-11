#!/usr/bin/env python3
"""V4 adversarial audit: old-grammar insufficiency versus general Lean induction.

This does NOT construct a new critic. It checks the exact claim boundary and
records that an existing general-purpose induction tactic is a strong control.
"""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    frozen=ROOT/"FrozenSource.lean"
    manifest=ROOT/"frozen_tasks.json"
    old=ROOT.parent/"bundy_critic_induction_v3/generate_proofs.py"
    reference=ROOT/"ReferenceObligations.lean"
    assert all(p.exists() for p in (frozen,manifest,old,reference))
    task=json.loads(manifest.read_text())
    oldsrc=old.read_text()
    new=frozen.read_text()
    ref=reference.read_text()
    # Auditable, finite, source-relative syntactic assertions.
    assert "induction xs generalizing acc" in oldsrc
    assert "Tree" not in oldsrc
    assert "inductive Tree" in new
    assert "induction t with" in ref
    assert len(task["protected"])==3
    assert len(task["negative"])==1
    report={
      "status":"V4_STRONG_BASELINE_ADVERSARIAL_AUDIT",
      "source_sha256":digest(frozen),"tasks_sha256":digest(manifest),
      "old_compiler_sha256":digest(old),"reference_sha256":digest(reference),
      "old_compiler_explicit_tree_support":False,
      "existing_lean_induction_solves_reference_tasks":True,
      "proof_of_semantic_old_language_inadequacy":False,
      "new_critic_constructed":False,
      "independent_critic_transfer":False,
      "interpretation":"Old V3 source grammar is limited; ordinary Lean tree induction already solves these tasks. No unique new critic semantics or advantage established.",
      "next_experiment":"Freeze residual traces and a lower-level typed constructor language; synthesize a novel proof-plan operation from residual constraints, prove soundness, and compare matched stateless induction."
    }
    out=ROOT/"results";out.mkdir(exist_ok=True)
    (out/"adversarial_audit.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
