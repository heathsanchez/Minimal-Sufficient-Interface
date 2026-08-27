# Typed Behavioural Congruence

The monoid theorem has now been lifted to typed continuations over a small category.

Let `C` be a small category. Each object `X` carries a state type `A(X)`, each morphism

\[
f:X\to Y
\]

acts as a typed state transformation

\[
A(f):A(X)\to A(Y),
\]

and each object has a protected observation

\[
v_X:A(X)\to O_X.
\]

Define contextual behavioural equivalence at object `X` by

\[
\boxed{
x\sim_X y
\iff
\forall Y\;\forall f:X\to Y,
\quad
v_Y(A(f)(x))=v_Y(A(f)(y)).
}
\]

The theorem package is machine-checked in [`lean/TypedBehaviouralCongruence.lean`](lean/TypedBehaviouralCongruence.lean) under the pinned Lean 4.24.0 toolchain.

## Greatest typed congruence

For a family of relations `R_X` on the typed state spaces, call `R` observation-compatible when

\[
R_X(x,y)\Longrightarrow v_X(x)=v_X(y),
\]

and categorical-congruent when every morphism preserves it:

\[
R_X(x,y)
\Longrightarrow
R_Y(A(f)(x),A(f)(y))
\qquad(f:X\to Y).
\]

Lean proves that the contextual family `~_X` is an equivalence relation at every object, is observation-compatible, is preserved by every morphism, and is greatest among all observation-compatible congruence families:

\[
\boxed{
R\text{ observation-compatible and congruent}
\Longrightarrow
R_X\subseteq\sim_X
\quad\forall X.
}
\]

As with the monoid result, the maximality theorem is slightly stronger than the usual statement because the competing family `R` itself need not be assumed to consist of equivalence relations.

## Objectwise minimal sufficient interfaces

Each object therefore has a behavioural quotient

\[
Q(X)=A(X)/{\sim_X}.
\]

Every morphism `f : X -> Y` descends uniquely to

\[
Q(f):Q(X)\to Q(Y),
\qquad
Q(f)([x])=[A(f)(x)].
\]

Lean proves

\[
\boxed{Q(1_X)=1_{Q(X)}}
\]

and

\[
\boxed{Q(g\circ f)=Q(g)\circ Q(f)}.
\]

Thus the minimal sufficient interfaces are not merely compatible objectwise. They assemble into a functorial quotient action of the whole continuation category.

## What changed conceptually

The monoid theorem said that, for one state type, MSI computes the maximal observation-compatible behavioural congruence under all reachable endomorphisms.

The typed theorem now says:

\[
\boxed{
\textbf{MSI computes the maximal observation-compatible congruence family across typed continuation contexts.}
}
\]

The quotient preserves the entire typed composition structure that acts on states.

This is the categorical bridge that the finite and monoid results pointed toward.

## Important boundary

The theorem does **not** yet quotient morphisms of `C` by an equivalence relation or construct a new quotient category `C/~` in the strongest category-theoretic sense. What is proved is the directly relevant behavioural statement: the category action on typed state spaces factors through objectwise behavioural quotients, and those quotient maps preserve identities and composition.

That distinction matters. The current theorem establishes a quotient **functorial action**. A quotient of the morphism category itself would require an additional morphism-equivalence notion and compatibility proof.

## Next developmental layer

The continuation category is still fixed. The next question is to let the accessible morphism family itself change under verified development:

\[
\boxed{\mathcal C_t\longrightarrow\mathcal C_{t+1}.}
\]

The desired causal law is

\[
\text{verified residual}
\to
\text{new justified morphism}
\to
\text{new continuation contexts}
\to
\text{finer behavioural quotient}
\to
\text{new executable/discoverable morphisms}.
\]

That is the next layer above the typed behavioural congruence theorem.
