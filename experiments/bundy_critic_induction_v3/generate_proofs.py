#!/usr/bin/env python3
"""Bounded generic proof-plan compiler, separate from calibration selector.

The generator reads frozen source definitions and protected metadata only after
the pre-holdout freeze receipt exists. It emits proof obligations and a single
typed induction-plan schema. This is schema instantiation, NOT invention of the
schema or of Lean's induction/rewrite tactics.
"""
import hashlib,json,pathlib,re
from . import run
ROOT=pathlib.Path(__file__).parent
def definition(source,name):
    m=re.search(r"(?m)^def "+re.escape(name)+r"\b[\s\S]*?(?=^def |^-- |^end |\Z)",source)
    if not m:raise ValueError("missing source definition "+name)
    return m.group(0)
def main():
    receipt=ROOT/"results/pre_holdout_freeze.json"
    if not receipt.exists():run.run()
    frozen=json.loads(receipt.read_text())
    assert frozen["source_sha256"]==hashlib.sha256((ROOT/"FrozenSource.lean").read_bytes()).hexdigest()
    assert frozen["selection"]["orientation"]=="right"
    source=(ROOT/"FrozenSource.lean").read_text()
    protected=json.loads((ROOT/"protected_cases.json").read_text())
    out=["import Std","import FrozenSource","namespace BundyInductionV3", 
         "/- Generated from frozen function definitions and a pre-selected generic",
         "   induction-plan schema. The compiler is not itself kernel verified. -/"]
    manifest=[]
    for case in protected["heldout"]:
        plain,acc=case["plain"],case["accumulator"]
        p,a=definition(source,plain),definition(source,acc)
        op=case["operation"]
        # Validate actual source syntax before using the declared operator.
        if op=="append":
            assert "++" in p and ("++" in a or "::" in a)
            sym="++";algebra="List.append_assoc"
        elif op=="add":
            assert " + " in p and " + " in a
            sym="+";algebra="Nat.add_assoc, Nat.add_comm, Nat.add_left_comm"
        elif op=="mul":
            assert " * " in p and " * " in a
            sym="*";algebra="Nat.mul_assoc, Nat.mul_comm, Nat.mul_left_comm"
        else:raise ValueError("unsupported frozen operator")
        carrier=case["carrier"]
        element=case["element"]
        extra=case.get("parameters",[])
        if extra:
            assert len(extra)==1 and extra[0]=="f : Nat → Nat"
            assert "(f : Nat → Nat)" in p and "(f : Nat → Nat)" in a
        extra_binder="(f : Nat → Nat) " if extra else ""
        extra_arg="f " if extra else ""
        theorem="generated_"+case["name"]
        body=(f"theorem {theorem} {extra_binder}(acc : {carrier}) (xs : List {element}) :\n"
              f"    {acc} {extra_arg}acc xs = {plain} {extra_arg}xs {sym} acc := by\n"
              "  induction xs generalizing acc with\n"
              f"  | nil => simp [{acc}, {plain}]\n"
              "  | cons x xs ih =>\n"
              f"    simp only [{acc}, {plain}]\n"
              "    rw [ih]\n"
              f"    simp [{algebra}]\n")
        out.append(body)
        manifest.append({"name":case["name"],"theorem":theorem,"operation":op,"source_names":[plain,acc]})
    out.append("end BundyInductionV3")
    output=ROOT/"results/GeneratedProtected.lean"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(out)+"\n")
    evidence={"status":"CANDIDATE_GENERATED_PROOFS_UNTIL_LEAN_CI",
      "generated_count":len(manifest),"manifest":manifest,
      "source_sha256":frozen["source_sha256"],
      "freeze_digest":frozen["digest"],
      "negative_case_generated":False,
      "claims":{"autonomous_meta_constructor":"UNKNOWN",
                "strong_stateless_advantage":"UNKNOWN",
                "source_derived_generic_schema_instantiation":"CANDIDATE"}}
    (ROOT/"results/generated_evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print(json.dumps(evidence,sort_keys=True))
if __name__=="__main__":main()
