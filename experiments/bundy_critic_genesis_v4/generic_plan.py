#!/usr/bin/env python3
"""V4 generic tree-proof plan emitter: no theorem-name to proof-script table.

Uses a frozen list of goals and generic source-structure-derived induction.
The lower induction/simplification/omega semantics remain supplied by Lean.
This is a bounded compiler experiment, NOT autonomous meta-semantics invention.
"""
import hashlib,json,pathlib,re
from .construct_plan import construct
ROOT=pathlib.Path(__file__).parent
def main():
    source=(ROOT/"FrozenSource.lean").read_text()
    plan=construct(source)
    assert plan.recursor=="Tree"
    assert ("leaf",0) in plan.recursive_fields and ("node",2) in plan.recursive_fields
    task=json.loads((ROOT/"frozen_tasks.json").read_text())
    # Derive the candidate goal text from source-extracted function signatures
    # and pre-frozen property descriptors. No theorem-name to proof-script table.
    # The goal grammar is intentionally finite, explicit and inspectable.
    defs=set(re.findall(r"(?m)^def\s+(\w+)\s*:",source))
    goals=[]
    for case in task["development"]+task["protected"]:
        fs=case["functions"]
        if any(f not in defs for f in fs):raise ValueError("unknown source function")
        if case["consequence"]=="count preservation under mirror":
            goal=f"{fs[1]} ({fs[0]} t) = {fs[1]} t"
        elif case["consequence"]=="mirror twice returns tree":
            goal=f"{fs[0]} ({fs[0]} t) = t"
        elif case["consequence"]=="mirror reverses leaves":
            goal=f"{fs[1]} ({fs[0]} t) = ({fs[1]} t).reverse"
        elif case["consequence"]=="height preservation":
            goal=f"{fs[1]} ({fs[0]} t) = {fs[1]} t"
        else:raise ValueError("unsupported frozen property grammar")
        goals.append((case["name"],goal,fs))
    out=["import Std","import FrozenSource","namespace BundyCriticV4"]
    for name,goal,fs in goals:
        # A single goal-independent plan: induction; constructor base by simp;
        # recursive branch uses source definitions and IHs, with omega for
        # arithmetic residuals. No target-specific tactic body.
        unfolding=", ".join(dict.fromkeys(fs))
        body=(f"theorem generated_{name} (t : Tree Nat) : {goal} := by\n"
              "  induction t with\n"
              f"  | leaf x => simp [{unfolding}]\n"
              f"  | node l r ihl ihr => simp [{unfolding}, ihl, ihr, List.reverse_append, Nat.max_comm]; all_goals omega\n")
        out.append(body)
    out.append("end BundyCriticV4")
    result=ROOT/"results";result.mkdir(exist_ok=True)
    (result/"GenericTreeProofs.lean").write_text("\n".join(out)+"\n")
    evidence={"status":"CANDIDATE_GENERIC_PROOF_PLAN_UNTIL_LEAN_CI",
      "generated":len(goals),"target_named_tactic_templates":False,
      "property_grammar_fixed":True,"supplied_semantics":["induction","simp","omega"],
      "new_semantics_invented":False,"strong_stateless_baseline":"same Lean tactic machinery available",
      "source_sha256":hashlib.sha256((ROOT/"FrozenSource.lean").read_bytes()).hexdigest()}
    (result/"generic_evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print(json.dumps(evidence,sort_keys=True))
if __name__=="__main__":main()
