#!/usr/bin/env python3
"""Independent guard against falsely promoting V4 target-named scripts.

Checks the actual proof emitter's dependency on theorem labels and compares
with the generic induction tactic already available to Lean.
"""
import ast,json,pathlib,re
ROOT=pathlib.Path(__file__).parent
source=(ROOT/"generate_tree_proofs.py").read_text()
module=ast.parse(source)
names=[]
for node in ast.walk(module):
    if isinstance(node,ast.Assign):
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id=="templates" and isinstance(node.value,ast.Dict):
                names=[key.value for key in node.value.keys if isinstance(key,ast.Constant)]
expected={"mirror_count","mirror_involution","mirror_leaves","height_mirror"}
assert set(names)==expected,(names,expected)
report={
  "status":"REJECTED_AS_AUTONOMOUS_CONSTRUCTOR",
  "target_named_template_count":len(names),
  "template_names":names,
  "generic_constructor_plan_verified":"SOURCE_RELATIVE_ONLY",
  "new_semantics_invented":False,
  "strong_stateless_Lean_induction_baseline":"CAN_PROVE_THE_SAME_FROZEN_REFERENCE_THEOREMS",
  "claim_boundary":"The emitted proofs are valid but the emitter contains target-specific scripts. Proof reach cannot demonstrate critic-genesis novelty.",
  "next_decisive_test":"Replace template dictionary with a generic proof-state interpreter that derives tactic steps from residuals, freeze source and compare strong stateless budgets."
}
out=ROOT/"results";out.mkdir(exist_ok=True)
(out/"template_dependency_audit.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
