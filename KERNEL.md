# Minimal Sufficient Interface — canonical kernel

This file is the frozen mathematical snapshot of the foundational core.

## 1. Universal refinement law

Let `(L, ∧)` be a meet-semilattice (equivalently, an idempotent commutative semigroup). Given current interface state `E_t` and a verified constraint `K_t`, update by

\[
\boxed{E_{t+1}=E_t\wedge K_t.}
\]

The operation satisfies

\[
a\wedge a=a,
\qquad
a\wedge b=b\wedge a,
\qquad
(a\wedge b)\wedge c=a\wedge(b\wedge c).
\]

Thus accumulated verified refinement is duplicate-insensitive, order-independent, and grouping-independent. The induced refinement order is

\[
a\le b\iff a\wedge b=a,
\]

so every update satisfies `E_{t+1} ≤ E_t`.

A top element `⊤` is required only when a canonical empty-evidence initial state is desired.

## 2. Minimal-sufficient-interface realization

Let `X` be situations and let each protected continuation `c` induce an equivalence relation `K_c` on `X`, where

\[
x\,K_c\,y
\]

means that continuation `c` does not distinguish `x` from `y` at the protected outcome boundary.

For a retained continuation family `B`, the current interface is

\[
\boxed{E_B=\bigcap_{c\in B}K_c.}
\]

Equivalently, for outcome maps `c:X\to O_c`,

\[
x\,E_B\,y
\iff
\forall c\in B,\;c(x)=c(y).
\]

This realizes the abstract meet as intersection of equivalence relations.

## 3. Derived notions

Nothing below is primitive.

- **separator:** a `K_c` whose meet with `E_B` is strict;
- **residual:** a distinction present in the protected target but absent from the current interface;
- **refinement:** `E' = E ∧ K`;
- **sufficiency:** current and protected target interfaces are equal;
- **finite convergence:** repeated strict descent terminates in a finite refinement poset;
- **quotient:** the state space modulo the current equivalence relation;
- **capability descent:** a transformation acts on the quotient exactly when it preserves the current equivalence.

## 4. Claim boundary

The abstract law describes extensional accumulation of verified refinements. It does not by itself specify what a constraint means, how it is discovered, whether the available constraints cover reality, what tests cost, or how capabilities create new tests.

The semantic interpretation supplied by Minimal Sufficient Interface is therefore the pair of equations

\[
\boxed{E_{t+1}=E_t\wedge K_t}
\qquad\text{and}\qquad
\boxed{E_B=\bigcap_{c\in B}K_c.}
\]

The first is the universal refinement dynamics. The second says what those dynamics mean here: retain exactly the sameness that survives every protected distinction currently in force.
