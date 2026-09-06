# Target 13 — adequacy of the directed residual (Ctx ⊢ Source → Target)

## Frozen architecture
Source-axis repair `69cfacd` (externally green): Diff = (Ctx, Source, Target), Residual = List (Diff).
Each diff is a directed contextual change: Ctx ⊢ Source → Target.

## The adequacy test (broad, no axis pre-committed)
    Q_dir(ρ_a) = Q_dir(ρ_b)  ∧  Future(ρ_a) ≠ Future(ρ_b) ?
Seek two residuals with the SAME list of directed diffs but DIFFERENT required continuation because a
RELATION among multiple directed changes is lost.  Candidate seams (explicit, none preferred):
  · relation/dependency between directed diffs
  · ordering
  · shared-variable interaction
  · causal / enabling structure

## Discipline (post-Target-12)
Predict the BOUNDARY, not the answer.  Do NOT pre-commit to which axis wins: the verifier names the
missing distinction.  This restraint matters because Target 12 falsified our axis guess and the
mechanism proved more reliable than the guess.

## Explicit falsifiers (any one ⇒ retain (Ctx, Source, Target); no refinement)
  F1  no two residuals with equal directed list but different future;
  F2  the directed (Ctx, Source, Target) already separates every candidate-seam pair — because it
      records the FULL source and target terms, from which any relation (dependency, shared-variable,
      causal) is derivable.  If the representation is injective, it determines the residual and hence
      the continuation, and the chain reaches a genuine fixed point.

## If a collapse DOES land
Record it first; then let the WITNESS name the missing relation (not our prior), and refine minimally
to represent exactly that relation.
