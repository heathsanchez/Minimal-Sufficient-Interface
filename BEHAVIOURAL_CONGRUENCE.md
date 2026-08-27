# Behavioural Congruence Theorem

This file records the general theorem counterpart of the finite compositional census.

Let a monoid `M` act on a state space `X`, and let

\[
v:X\to O
\]

be the protected observation. Define all-futures behavioural equivalence by

\[
\boxed{
x\sim_*y
\iff
\forall m\in M,\;v(m\cdot x)=v(m\cdot y).
}
\]

In the generated-action interpretation, `M = G*` is the monoid of all reachable compositions.

The theorem package is machine-checked in [`lean/BehaviouralCongruence.lean`](lean/BehaviouralCongruence.lean) under the pinned Lean 4.24.0 toolchain.

## 1. Greatest invariant observation-compatible relation

The Lean development proves that `~*` is an equivalence relation, is contained in the observation kernel, and is invariant under every reachable action.

More strongly, for any relation `R`, if

\[
R(x,y)\Longrightarrow v(x)=v(y)
\]

and

\[
R(x,y)\Longrightarrow R(m\cdot x,m\cdot y)
\qquad\forall m\in M,
\]

then

\[
R\subseteq\sim_*.
\]

Therefore

\[
\boxed{
\sim_*
=
\max\{E\subseteq\ker(v):E\text{ is an }M\text{-invariant equivalence relation}\}.
}
\]

The Lean maximality theorem is slightly stronger than this formulation because `R` itself need not be assumed to be an equivalence relation.

## 2. Quotient action

Because `~*` is invariant, every reachable action `m` induces a well-defined map

\[
\bar m:X/{\sim_*}\to X/{\sim_*}
\]

with

\[
\bar m([x])=[m\cdot x].
\]

The file constructs this map with `Quotient.lift` and proves its uniqueness among maps agreeing with the action on representatives.

## 3. Identity and composition survive compression

The quotient action preserves the monoid laws:

\[
\boxed{\bar 1=\mathrm{id}}
\]

and

\[
\boxed{\overline{gf}=\bar g\circ\bar f.}
\]

So the behavioural quotient does not merely retain observational distinctions. It retains the compositional dynamics of every reachable action.

## 4. Finite verifier-driven recovery

For the finite case, let `all` be any finite list covering every reachable action. Let `B_n` be the retained continuation list at stage `n`. A genuine refinement step may choose **any** reachable continuation that separates a pair still merged by the current interface and retain it.

The Lean theorem proves that, starting from no retained continuations, if such a genuine separator is added whenever the current interface is nonterminal, then there is some

\[
n\le |\texttt{all}|
\]

such that

\[
\boxed{
E_{B_n}=\sim_*.
}
\]

No greedy policy, fixed separator ordering, or knowledge of the final quotient is assumed.

The proof uses two facts:

1. a genuine separator cannot already be in the retained basis, so every nonterminal step adds a fresh continuation;
2. a finite complete continuation family cannot contain more distinct retained continuations than its own size.

The exact stopping theorem inside the same file is

\[
\boxed{
\text{no reachable separator remains}
\iff
E_B=\sim_*.
}
\]

Thus the finite developmental process is not merely convergent: it converges to the uniquely characterized maximal observation-compatible behavioural congruence.

## Relation to the census

The earlier exhaustive census found the first nontrivial finite witnesses at four states:

- 4,096 total worlds;
- 576 one-step quotients too coarse;
- 576 compositional refinements;
- 0 convergence failures;
- 0 congruence failures;
- 0 quotient-composition failures;
- 576 exact ablation witnesses.

Those data remain useful as executable witnesses and falsifier cases. The Lean theorem now explains why the successful endpoint is forced in general for monoid actions under the stated assumptions.

## What is not proved yet

This theorem is about a single state type with a monoid of endomorphisms. It does **not** yet formalize:

- typed morphisms between different state spaces;
- a family of observational congruences indexed by objects of a category;
- quotienting a category by such a congruence family;
- verifier-driven growth of the morphism/category itself.

Those are the next categorical layer above the monoid theorem.

The strongest current statement is therefore:

\[
\boxed{
\textbf{MSI refinement computes the maximal observation-compatible behavioural congruence,}
}
\]

with quotient dynamics that preserve identity and composition.
