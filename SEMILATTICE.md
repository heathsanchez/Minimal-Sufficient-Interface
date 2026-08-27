# Semilattice compression

The state-identification kernel admits a stricter compression than the continuation/outcome presentation.

Let `Eq(X)` be the set of equivalence relations on `X`, ordered by inclusion. Finer observational interfaces contain fewer pairs.

For a protected continuation `c`, keep only its kernel equivalence relation `K_c`.

For a retained family `B`, the interface state is

\[
E_B = \bigcap_{c\in B} K_c.
\]

Thus the update caused by new verified distinction evidence is simply

\[
\boxed{E' = E \wedge K}
\]

where the meet is set intersection.

## What is forced

`Eq(X)` with meet `\wedge = \cap` is a meet-semilattice:

- `E \wedge E = E` (idempotence),
- `E \wedge F = F \wedge E` (commutativity),
- `(E \wedge F) \wedge G = E \wedge (F \wedge G)` (associativity),
- the indiscrete relation `X x X` is the top element,
- `E \le F` iff `E \wedge F = E`, exactly corresponding to `E \subseteq F`.

Therefore, if we care only about the current observational interface and its lawful refinement trajectory, named continuations are not primitive. Their only state-changing content is the equivalence relation they contribute to the meet.

The compressed state dynamics are:

\[
\boxed{E_{t+1}=E_t\wedge K_t.}
\]

A step is informative exactly when `E_{t+1} < E_t`.

## What this compression does not retain

Eliminating continuation names loses information that higher layers may need:

- which experiment produced `K`,
- the cost of obtaining it,
- whether two distinct experiments have the same kernel,
- provenance and verifier authority,
- how a capability generates a new continuation,
- which continuation to choose next.

So there are two different minimalities:

1. **Interface-state ontology:** a point `E` in the meet-semilattice `Eq(X)`.
2. **Development/search ontology:** generators/tests plus provenance/cost are needed to decide which meet operand can or should be acquired next.

The continuation object is therefore eliminable from the extensional state kernel, but not from an active theory of experiment selection or capability growth.

## Exhaustive finite check

`tests/test_semilattice_core.py` exhausts all 15 equivalence relations on four states and verifies closure under meet, associativity, commutativity, idempotence, the top identity, refinement/inclusion correspondence, strict progress, order independence, and duplicate-kernel redundancy. It also exhausts all `5^3=125` three-test families over the five equivalence relations on three states and all eight retained subsets, confirming that the induced interface is completely determined by their meet.

## Compressed equation

For the extensional kernel, the smallest current candidate is therefore

\[
\boxed{E' = E \wedge K.}
\]

The static form is

\[
\boxed{E_B=\bigwedge_{c\in B}K_c.}
\]

This is a compression of the kernel, not a claim that all developmental intelligence is a semilattice process.
