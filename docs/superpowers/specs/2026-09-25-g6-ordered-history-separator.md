# G6 Ordered-History Separator Specification

## Scientific question

After a shared final selector click, does the earlier click leave any legally
observable residue in the present state or in the response to one common next
click?

The qualified G6 selector response collapses under the coarse source-bit
observer to the last click.  Therefore `UL` versus `LU` is not a valid history
separator: the final selector states differ.  The controlled comparisons are:

- `UL` versus `LL`, both ending in `L`;
- `LU` versus `UU`, both ending in `U`.

## Exact boundary

- Exact public game: `tn36-ef4dde99`.
- Enter G6 only through the already-qualified G1→G5 replay.
- Execute the common route prefix `RRRRUULLUU` before every trial.
- For each controlled history comparison, use the common suffix bank
  `("", "U", "D", "L", "R")`.
- Restart and replay the common prefix for every history/suffix trial.
- Observe only legal public frames and public frame metadata.
- Perform zero target-panel writes, zero submit clicks, zero model calls, and
  zero game-source inspection.
- Bound every trial by 13 clicks: ten prefix clicks, two history clicks, and at
  most one suffix click.

## Protected observation

For the common-prefix frame and every resulting frame, retain:

- canonical full-visible-matrix digest;
- exact visible changes relative to the common-prefix frame, including
  coordinate, before value, and after value;
- six source bits;
- level and public game state;
- action trace and action count.

The empty-suffix comparison tests present-state residue after the shared
endpoint.  Non-empty suffixes test one-step protected future response.  A
difference visible only between the two histories' first intermediate frames is
diagnostic and cannot promote the separator.

## Classification

- `RESPONSE_SEPARATOR_ONLY`: at least one controlled pair differs after the
  shared endpoint under the empty suffix or after the same one-click suffix.
- `WARRANTED_NEGATIVE`: every controlled pair is equal across the complete
  declared suffix bank.  This rejects only this bounded public-observation and
  one-step-suffix family.
- `NON_EVIDENCE`: restart drift, missing controls, inconsistent common-prefix
  identity, incomplete census, malformed observation, budget overrun, or any
  harness exception.

This experiment cannot claim a target projection, G6 progress, or a reusable
solver capability.  A positive result earns only the ordered-history separator
needed for the next G2–G5 supervised projection experiment.
