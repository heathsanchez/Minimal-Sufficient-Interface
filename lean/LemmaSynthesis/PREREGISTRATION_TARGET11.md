# Target 11 — multi-diff boundary (prospective)

## Frozen architecture
One-hole ResidualView = (Ctx, Filling) frozen at `18657d2` (Target 10 externally green: it survived the
single-diff adequacy test).  No multi-hole/composed context is added beforehand.

## The boundary probe (nearest boundary, not a richer repair)
    single-diff residual  →  multi-diff residual
    Can one-hole (Ctx, Filling) still determine continuation when TWO positions must change together?

## Pre-registered prediction (frozen before the witness is sought)
A collapse EXISTS at the multi-diff boundary.  The one-hole view marks ONE distinguished position; a
residual whose diff spans two positions loses "which OTHER position is also a diff".  Prediction: two
residuals share the SAME one-hole decomposition (same (Ctx, Filling) at the shared first diff) yet require
different futures because one has a second diff position and the other does not.

## Explicit falsifiers (any one ⇒ retain one-hole, no compose promotion)
  F1  no two residuals with equal one-hole (Ctx, Filling) but different required continuation;
  F2  the one-hole view already distinguishes every multi-diff pair in the tested class
      (then the representation survives the harder boundary and compose stays merely available).

## If the collapse lands
  - Record the collapse FIRST (same one-hole view, different futures).  Do not repair before recording.
  - THEN promote composition: the residual is a COMPOSITION of one-hole contexts (multiple holes), not a
    larger flat feature set.
  - At that point `fill_compose` becomes scientifically load-bearing (not inherited-by-correspondence):
    RE-PROVE the generic signature-generic `fill (compose c d) x = fill c (fill d x` law as part of the
    repair.

## No-change rule
One-hole (Ctx, Filling) stays frozen through this probe.  Multi-hole/composed structure is added ONLY if
this witness forces it, and only as the minimal joint-hole representation the witness requires.
