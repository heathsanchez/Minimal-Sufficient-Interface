# Residual-driven new node type genesis

This branch tests whether a verified expressivity obstruction can force creation of a new value-producing node type rather than deeper search inside the existing selector-tree schema.

The old schema may branch arbitrarily over the current observables `x`, `F(x)`, and `G(x)`, but every leaf must return one of those existing values. Therefore any verified row whose target is outside `{x,F(x),G(x)}` is a depth-independent impossibility witness for the entire old schema language.

After that obstruction is certified, the developmental rule infers the minimum subset of current coordinates needed to make verifier outcomes functional and synthesizes a finite `Combine` node extensionally over those coordinates. No arithmetic/operator family is supplied to the learner.

The primary hidden world is verifier-only `(F(x)+G(x)) mod 4`. The expected inferred inputs are `(F,G)`. The learned node is frozen and evaluated on all held-out non-permutation map pairs; ablation returns to the old selector language and its impossibility witnesses.

Boundary: the new node is still a generic finite lookup over existing observables. The next step after this is to require a new observable/state variable or to transfer the developmental mechanism into Lean proof search.
