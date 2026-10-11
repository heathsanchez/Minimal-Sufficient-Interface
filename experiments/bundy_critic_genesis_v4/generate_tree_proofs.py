#!/usr/bin/env python3
"""V4 proof emitter driven by a previously frozen branching-plan receipt.

Supplied generic Lean structural induction and simplification are used.
No new induction semantics or theorem discovery claimed.
"""
import hashlib,json,pathlib
from .construct_plan import construct
ROOT=pathlib.Path(__file__).parent
def run():
    source=(ROOT/"FrozenSource.lean").read_text()
    plan=construct(source)
    assert plan.recursor=="Tree" and ("node",2) in plan.recursive_fields
    frozen=json.loads((ROOT/"frozen_tasks.json").read_text())
    assert len(frozen["protected"])==3
    # These proof-plan *strategies* are fixed and source-independent, but the
    # goal specifications below are derived from the pre-frozen manifest.
    templates={
      "mirror_count":("leafCount (mirror t) = leafCount t",
          "  | leaf x => rfl\n  | node l r ihl ihr => simp only [mirror, leafCount]; omega"),
      "mirror_involution":("mirror (mirror t) = t",
          "  | leaf x => rfl\n  | node l r ihl ihr => simp [mirror, ihl, ihr]"),
      "mirror_leaves":("leaves (mirror t) = (leaves t).reverse",
          "  | leaf x => rfl\n  | node l r ihl ihr => simp [mirror, leaves, ihl, ihr, List.reverse_append]"),
      "height_mirror":("height (mirror t) = height t",
          "  | leaf x => rfl\n  | node l r ihl ihr => simp [mirror, height, ihl, ihr, Nat.max_comm]"),
    }
    names=["mirror_count"]+[x["name"] for x in frozen["protected"]]
    # Explicit disclosure: these are target-named scripts, a strong negative
    # control against claims of genuine constructor genesis.
    out=["import Std","import FrozenSource","namespace BundyCriticV4"]
    for name in names:
        goal,body=templates[name]
        out.append(f"theorem emitted_{name} (t : Tree Nat) : {goal} := by\n  induction t with\n{body}")
    out.append("end BundyCriticV4")
    result=ROOT/"results";result.mkdir(exist_ok=True)
    (result/"GeneratedTreeProofs.lean").write_text("\n\n".join(out)+"\n")
    evidence={"status":"CANDIDATE_TARGET_NAMED_PLAN_EMISSION",
      "generated_count":len(names),"plan":plan.data(),
      "target_named_proof_templates":True,
      "source_derived_constructor_semantics":False,
      "autonomous_critic_invention":"REJECTED_ON_THIS_IMPLEMENTATION",
      "strong_stateless_baseline":"STANDARD_LEAN_INDUCTION_SOLVES_REFERENCE"}
    (result/"generated_evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print(json.dumps(evidence,sort_keys=True))
if __name__=="__main__":run()
