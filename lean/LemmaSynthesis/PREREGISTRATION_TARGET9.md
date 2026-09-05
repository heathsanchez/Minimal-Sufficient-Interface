# Target 9 — adequacy of {depth, arity, sort, operator, position} (prospective)

## Frozen architecture
Frozen at the position-refinement commit.  Q''' = {requiredDepth, safeArity, invSort, invOp, diffPos};
SearchPolicy = {depthBound, arityCap, budget, focusSort, focusOp, focusPos}; selector `SelectPolicy'''`.
Calibrated: `position_refinement_separates`, `refined_policies_differ`, left/right position reach/miss.

## The adequacy test (recursive, now the fifth iteration)
    ∃ ρ_a, ρ_b :  Q'''(ρ_a) = Q'''(ρ_b)  ∧  Future(ρ_a) ≠ Future(ρ_b) ?
If YES, {depth, arity, sort, operator, position} is still too coarse and the next discriminator is forced.
If NO, position survives.

## Predicted next discriminator (PROVISIONAL, promoted only if a witness forces it)
The refinement sequence has moved scalar → typed → operator-level → positional.  The next candidate
is RELATIONAL — dependency structure / the CONTEXT around the diff path (not just the path index):
two residuals can share depth, arity, sort, operator, and position, yet differ in the surrounding
context the diff position sits in, so a focus-pos search still cannot decide which surrounding
subterm to expand.  Explicitly provisional: do not add context/relational structure unless Target 9
exhibits a witness that specifically requires it.

## Explicit falsifiers (any one ⇒ "position survives" for the tested class)
  F1  no two residuals with equal {depth, arity, sort, operator, position} but different futures;
  F2  the position distinction is sufficient — every position-equal pair has the same required
      control (then the refinement is adequate and the chain stops at position).

## No-change rule
Q''' and the SearchPolicy are frozen.  Add relational/context structure only if a verifier-
certified witness (Target 9) forces exactly that discriminator.
