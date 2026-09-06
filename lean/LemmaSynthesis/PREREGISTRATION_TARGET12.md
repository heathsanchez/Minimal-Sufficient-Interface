# Target 12 — nested-diff boundary: does List(Diff) conflate parallel vs sequential?

## Frozen architecture
Composition repair `78c18ef` (externally green): Residual = List (Diff), Diff = Σ s t, (Ctx s t × Term t),
numDiffs load-bearing, generic fill_compose re-proved via Ctx.rec.

## The boundary probe
    parallel multiplicity  vs  sequential/compositional dependency
    Does the flat list preserve that one diff occurs INSIDE the filling of another?

## Pre-registered prediction (frozen before the witness is sought)
A collapse exists: two residuals with the SAME flat list of one-hole diffs but DIFFERENT nesting
(parallel vs nested/sequential) require different futures, because a list does not record the
compose-relationship between its entries.  If so, compose becomes part of the residual datatype itself
(tree/free-category/path), a further phase change: List(Diff) → compositional residual structure.

## Explicit falsifiers (any one ⇒ no nesting collapse; flat list survives)
  F1  the flat list already distinguishes every nested pair from its parallel pair — the one-hole Ctx
      records the hole's DEPTH/POSITION, so nesting is derivable and no information is lost;
  F2  two residuals with equal flat list have equal futures (the mapping is injective on the diff set).

## Honest fallback if the prediction is falsified
Record it, and separately probe the axis the flat list DOES lose: the SOURCE (IH value) at each diff
position is not recorded — only the target (goal value).  If two residuals share goal+target but differ
in IH, the flat list conflates them: that is the genuine next collapse (source-axis), to be reported if
the nesting-axis survives.
