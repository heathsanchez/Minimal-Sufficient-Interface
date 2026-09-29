# TaskSAT PVS CAD residual V1

## Residual

The observable-validity CAD run closed 7 of 8 formulas. The only unresolved
formula was the strict-interior R-subset-B equivalence with five quantified
variables, including an auxiliary clamp-output variable y. That formula timed
out / remained OPEN; this is a verifier-performance residual, not a known
counterexample.

## Cheapest decisive experiment

Eliminate y and expand clamp validity into its three regions directly. Then
split the equivalence into two one-way four-variable theorems:

1. reference-validity implies raw Python validity;
2. raw Python validity implies reference-validity.

If both are CAD-QED, they jointly discharge the exact strict-interior
equivalence and close the final algebraic residual without asking CAD to solve
the harder presentation.

## Promotion

A green 2/2 run promotes the strict-interior validity-equivalence claim from
UNKNOWN-at-verifier-boundary to WARRANTED, while preserving the failed
five-variable theorem as a performance negative result.
