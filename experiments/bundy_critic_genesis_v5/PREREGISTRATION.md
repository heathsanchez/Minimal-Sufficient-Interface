# V5 — constructive escape from a certified proof-plan obstruction

Parent: V4 commit 9b033e803a30d6922b3ff72e35dd4f2a1cc7f609, qualified CI 38103506151.
Status: PREREGISTERED, not yet a demonstrated breakthrough.

## Objective
Test development of a *new proof-plan constructor* rather than instance-level proof generation. Freeze V4's full generic planner and a separately defined typed operation language before seeing the V5 protected source. A new task must exhibit a formally checked old-language obstruction, not a timeout.

## Source and problem
Use indexed inductive syntax with dependent transport, or mutual recursion, requiring a repair operation outside V4's structural-tree property grammar. Freeze two distinct families, a calibration source and an independent protected source, including negative cases. Keep theorem solutions and target-specific tactics out of the frozen task source.

## Warrant and controls
1. Formalise the exact old-language grammar and prove its closure invariant in Lean. Source-string inspection alone is insufficient.
2. Construct a typed new operation from a certified failed residual. Do not add target-labelled templates or interpreter cases after inspecting protected tasks.
3. Check generated proof terms in pinned Lean without sorry/admit, axioms as shortcuts, or imports of the reference proof module.
4. Demonstrate a causally necessary protected proof, source mutation rejection, removal ablation, previous-proof preservation, and independent replay.
5. Compare a full stateless planner given the same semantics, evidence and budget, and exact executable memory. Count discovery, verification, integration and reuse cost.
6. A strong stateless planner with the same expressive substrate and unlimited time can reconstruct the same operation. Do not claim strict semantic reach against that comparator.

## Epistemic decision
WARRANTED_BOUNDED only after source-exact CI. REUSABLE after frozen independent transfer. BREAKTHROUGH only if the new operation's semantics were not supplied in advance, its generation is source-driven, and a meaningful budgeted advantage or new scoped expressivity is established. Otherwise UNKNOWN or REJECTED.

## Existing results not to inflate
V3 4/4 generated accumulator proofs; V4 4/4 generated branching proofs. Both depend on supplied induction and simplification semantics. No autonomous meta-language invention established.
