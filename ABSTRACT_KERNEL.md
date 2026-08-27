# Abstract kernel

The extensional interface-state laws do not require an explicit situation set `X` or equivalence relations on `X`.

They require only a meet-semilattice with top:

\[
(L,\wedge,\top).
\]

An interface state is an element `E ∈ L`. A verified distinction contributes an element `K ∈ L`. The update law is

\[
\boxed{E' = E\wedge K.}
\]

The semilattice axioms are:

\[
a\wedge a=a,\qquad a\wedge b=b\wedge a,\qquad
(a\wedge b)\wedge c=a\wedge(b\wedge c),\qquad a\wedge\top=a.
\]

Define the refinement order by

\[
a\preceq b \iff a\wedge b=a.
\]

Then every update is monotone descent:

\[
E\wedge K\preceq E.
\]

For a finite protected generator family `C={K_1,...,K_n}`, define the protected target

\[
T=\bigwedge_{i=1}^n K_i.
\]

For a retained subfamily `B`, let

\[
E_B=\bigwedge_{K\in B}K,
\]

with the empty meet equal to `top`.

Then:

1. **Order independence** follows from commutativity and associativity.
2. **Duplicate insensitivity** follows from idempotence.
3. **Monotone refinement** is `E_{B∪{K}} = E_B∧K \preceq E_B`.
4. **Strict progress** occurs exactly when `E_B∧K != E_B`.
5. **Exact stopping for a finite protected family** is

   \[
   E_B=T
   \iff
   \forall K\in C\setminus B,\;E_B\wedge K=E_B.
   \]

6. **Finite convergence** follows by repeatedly adjoining any remaining `K` that strictly refines the current state. At most `|C\setminus B|` such additions are possible before reaching `T`.

Thus the state-identification dynamics compress to

\[
\boxed{E_{t+1}=E_t\wedge K_t.}
\]

## What this abstraction removes

The abstract kernel does not retain what `E` or `K` *mean*. In the relational realization, elements are equivalence relations on a situation set and meet is intersection. In other realizations they may be entirely different objects.

The abstraction therefore preserves the algebra of verified refinement but not automatically:

- pairwise separator witnesses `(x,y)`;
- quotient classes or quotient maps;
- observational semantics;
- transformation congruence on situations;
- provenance, cost, or verifier authority of a generator;
- mechanisms that generate new admissible `K` values.

Those require a representation/realization of the semilattice or additional structure above it.

So `(L,∧,top)` is sufficient for the **extensional refinement state machine**. The equivalence-relation model remains the smallest concrete semantics currently established for interpreting that machine as a minimal sufficient interface.
