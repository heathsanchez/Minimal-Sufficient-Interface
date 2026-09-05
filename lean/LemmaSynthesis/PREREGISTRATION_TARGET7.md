# Target 7 — adequacy of the refined quotient {depth, arity, sort} (prospective)

## Frozen architecture
Frozen at the quotient-refinement commit.  F' = {requiredDepth, safeArity, invSort}; SearchPolicy
= {depthBound, arityCap, budget, focusSort}; selector `SelectPolicy'` focuses on the invariant's
sort.  Calibrated on Target 6: `refined_F_separates`, `focusA_reaches_invA`, `focusB_reaches_invB`.

## The adequacy test (the recursive question, now built in)
    ∃ ρ_a, ρ_b :  F'(ρ_a) = F'(ρ_b)  ∧  Future(ρ_a) ≠ Future(ρ_b) ?
If YES, sort is still too coarse and the next discriminator is forced.  If NO, sort survives.

## Predicted next discriminator (if sort proves too coarse)
The natural candidate is OPERATOR (which operator within the target sort must be expanded), not
position/dependency-path: two residuals can share {depth, arity, sort} yet differ in WHICH operator
of that sort their invariant's RHS is built from, so a sort-focus search still has to decide among
multiple operators.  This prediction is provisional — Target 7 decides it, not assertion.

## What would falsify "sort survives" (i.e. confirm F' is still too coarse)
  F1  two residuals with equal {depth, arity, sort} but invariants built from different operators
      of that sort, so a sort-focus policy reaches one but not the other;
  F2  two residuals with equal {depth, arity, sort} but different required depth/arity per-sort,
      so even the per-sort depth/arity is conflated.

## What would CONFIRM "sort survives"
  No such pair is found for the declared signature class — every pair with equal
  {depth, arity, sort} has the same required control.  Then the refinement is sufficient and the
  quotient is adequate for that class.

## No-change rule
The refined F' and SearchPolicy are frozen.  Do not add operator/depth/position features unless a
verifier-certified residual (this Target 7) forces exactly that discriminator.
