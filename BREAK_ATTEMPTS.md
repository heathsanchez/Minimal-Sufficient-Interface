# Break Attempts

The frozen MSI refinement kernel survived the adversarial checks performed here, but the strongest recent **constructor-genesis** interpretation did not survive unchanged.

## What broke

The grammar used in `tests/test_constructor_genesis.py`

\[
t ::= x \mid F(t) \mid G(t)
\]

can generate only unary action words. It can therefore discover sequential composition because the target `F(G(x))` is already expressible in that grammar.

That does **not** imply arbitrary composition-like structure can be generated from counterexamples alone.

A fixed three-state falsifier is:

- `f = (0,0,2)`;
- `g = (1,0,1)`;
- hidden binary constructor: pointwise minimum,

\[
H(f,g)(x)=\min(f(x),g(x)),
\]

which gives

\[
H(f,g)=(0,0,1).
\]

No term in the depth-3 constructor grammar realizes this map. More strongly, the repository checks the grammar out to depth 12 and still finds no realization. Counterexample elimination therefore eventually removes **every** candidate.

So the safe statement is not

> counterexamples generate the correct constructor structure in general.

It is

\[
\boxed{
\textbf{counterexamples identify the correct constructor only when the developmental grammar can express it.}
}
\]

## What did not break

This falsifier does not touch the canonical MSI equations

\[
E_{t+1}=E_t\wedge K_t,
\qquad
E_B=\bigcap_{c\in B}K_c,
\]

nor the Lean behavioural-congruence theorems. Those results already quantify over supplied protected continuations / actions and do not claim universal synthesis of missing constructors.

It also does not invalidate the finite constructor-genesis census. That census remains correct for its stated grammar and sequential-composition verifier. What fails is the stronger extrapolation from grammar-relative synthesis to open-ended constructor invention.

## New sharp boundary

The remaining problem is now explicit:

\[
\boxed{
\text{residual}
\to
\text{recognize grammar insufficiency}
\to
\text{expand the constructor language}
\to
\text{resume verified synthesis}.
}
\]

A genuinely developmental system must be able to treat **empty version space** as a representation-level residual rather than as terminal failure.

This is a stronger and cleaner target than merely searching a deeper fixed grammar.

See `tests/test_break_attempts.py` for the machine-checked falsifier.
