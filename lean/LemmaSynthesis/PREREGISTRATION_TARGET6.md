# Target 6 — feature-extractor collapse (control-level analogue of extensional/context)

## Frozen architecture
Frozen at `2047b358`.  The feature extractor `F(ρ) = {requiredDepth, safeArity}` and the selector
`SelectPolicy` are NOT modified.

## The test (kernel-check the collapse)
∃ ρ_a, ρ_b :  F(ρ_a) = F(ρ_b)  but  required control action differs,
with F(ρ) = {requiredDepth, safeArity}.

This is the control-level analogue of the object-level extensional/context result: the same coarse
(scalar) observation does not determine the consequential structure.  At the object level,
`neg(neg hole)` and `hole` collapse extensionally but differ structurally; here, two residuals
collapse under the scalar summary {depth, arity} but differ in the SORT their invariant lives at,
hence in which operator set the search must expand.

## What would falsify it
  F1  no two residuals with equal {depth, arity} but different required control exist for the
      tested signature (F is injective on consequential structure);
  F2  the sort difference is not consequential (reaching the two invariants requires the same
      expansion, so the collapse is vacuous);
  F3  the invariants do not both have size 2 and arity 2 (so F genuinely differs).

## Sealed expected result
The collapse holds: two residuals in one two-sort signature, both with {requiredDepth 2, safeArity 2},
whose invariants live at different sorts and are reachable only by expanding different operator
sets.  F erases exactly that distinction.

## No-change rule
The feature extractor is NOT repaired in this run.  A clean failure (or confirmation) is recorded;
the forced repair — scalar residual summary → structured residual representation (sort, operator,
diff position) — is only proposed AFTER the result is formal.
