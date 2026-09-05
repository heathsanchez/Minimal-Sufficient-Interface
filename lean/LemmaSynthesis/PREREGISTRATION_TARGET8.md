# Target 8 — adequacy of {depth, arity, sort, operator} (prospective)

## Frozen architecture
Frozen at the operator-refinement commit.  Q'' = {requiredDepth, safeArity, invSort, invOp};
SearchPolicy = {depthBound, arityCap, budget, focusSort, focusOp}; selector `SelectPolicy''`.
Calibrated: `operator_refinement_separates`, `refined_policies_differ`, focus-fa/ga reach/miss.

## The adequacy test (recursive, now the third iteration)
    ∃ ρ_a, ρ_b :  Q''(ρ_a) = Q''(ρ_b)  ∧  Future(ρ_a) ≠ Future(ρ_b) ?
If YES, {depth, arity, sort, operator} is still too coarse and the next discriminator is forced.
If NO, operator survives.

## Predicted next discriminator (PROVISIONAL, promoted only if a witness forces it)
POSITION / diff-path — two residuals can share {depth, arity, sort, operator} yet differ in WHERE
within the term the operator is applied (the residual's diff position / dependency path), so a
focus-op search still cannot decide which subterm to expand.  Explicitly provisional: do not add
position unless Target 8 exhibits a witness that specifically requires it.

## Explicit falsifiers (any one ⇒ "operator survives" holds for the tested class)
  F1  no two residuals with equal {depth, arity, sort, operator} but different futures;
  F2  the operator distinction is already sufficient — every operator-equal pair has the same
      required control (then the refinement is adequate and the chain stops at operator).

## No-change rule
Q'' and the SearchPolicy are frozen.  Add position/diff-path only if a verifier-certified witness
(Target 8) forces exactly that discriminator.
