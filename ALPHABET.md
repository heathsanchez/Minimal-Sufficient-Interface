# Minimal alphabet

This file tests how far the kernel can be compressed without changing its mathematics.

## Primitive ontology

The state-identification layer needs only:

- a set `X` of situations;
- a family `C` of protected continuations/observations;
- for each `c ∈ C`, a map `c : X → O_c` into any outcome set for that continuation;
- equality in each `O_c`.

A single shared outcome type `O` is convenient notation, not part of the essential ontology. Outcome *names* are irrelevant; only the equality fibers of each continuation matter.

## Master equation

For `B ⊆ C`, define

\[
\boxed{E_B = \bigcap_{c\in B}\ker c.}
\]

Equivalently,

\[
x\,E_B\,y \iff \forall c\in B,\;c(x)=c(y).
\]

This is the compressed semantic kernel.

## What is derived

From the master equation alone:

1. `E_B` is an equivalence relation.
2. `B ⊆ B'` implies `E_{B'} ⊆ E_B`.
3. `E_{B∪{c}} = E_B ∩ ker c`.
4. A residual is a pair in `E_B \ E_C`.
5. Any continuation separating a residual pair produces strict refinement.
6. `E_B = E_C` iff no continuation in `C\B` separates any pair still merged by `E_B`.
7. If `C` is finite, repeated lawful strict refinement terminates at `E_C`.

Capability descent is the next layer rather than an additional state-identification primitive: a transformation `f:X→X` acts on `X/E_B` exactly when it preserves `E_B`.

## Alphabet

At the state-identification level, the irreducible typed alphabet can therefore be written as

\[
\boxed{x:X,\qquad c:X\to O_c,\qquad =}
\]

with quantification/set formation supplied by the ambient mathematics.

The apparent notions `separator`, `equivalence`, `quotient`, `residual`, `refinement`, `sufficiency`, and `convergence` are derived vocabulary, not primitives.

## Falsification boundary

The claim here is *definitional sufficiency*, not metaphysical minimality. To falsify the proposed compression within this kernel, exhibit a current kernel law whose truth cannot be reconstructed from the family of equality kernels `ker c`, or two systems with identical equality kernels for every continuation but different state-identification behavior under the spec.

`tests/test_alphabet_kernel.py` exhaustively checks the reconstruction against all 512 binary `3×3` worlds, all retained bases, finite repair, and independent outcome relabelings. It also includes a heterogeneous-codomain witness showing that a common global outcome set is unnecessary.
