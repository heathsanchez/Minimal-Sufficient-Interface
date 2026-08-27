# Grammar-Driven Constructor Genesis

This experiment removes the last hand-written finite list of candidate composition laws.

The learner is no longer given candidates such as `seq`, `rev`, `left`, `right`, `min`, or `max`. Instead it receives only a tiny constructor grammar over two executable transformations `F`, `G` and a state `x`:

\[
\boxed{t ::= x \mid F(t) \mid G(t).}
\]

Terms are generated mechanically up to depth 3. The true sequential constructor

\[
F(G(x))
\]

is therefore generated as one term among 15 syntax trees; it is not named as the target.

## Verifier-driven synthesis

For a reachable transformation algebra `A`, the hidden verifier knows the actual sequential execution semantics

\[
(f\circ g)(x)=f(g(x)).
\]

The learner maintains the generated term version space. Whenever a candidate term disagrees with execution on some reachable triple `(f,g,x)`, the verifier returns only that concrete counterexample. All generated terms inconsistent with it are removed. The process continues until no reachable counterexample exists.

Thus:

\[
\boxed{
\text{generated constructor grammar}
\to
\text{execution counterexample}
\to
\text{version-space refinement}
\to
\text{retained constructor}.
}
\]

## Exhaustive result

The census exhausts all ordered pairs of deterministic primitive transformations on a three-state space:

\[
27^2=729
\]

reachable-action worlds.

Results:

- total worlds: **729**;
- worlds with a unique surviving syntax: **558**;
- worlds with multiple surviving syntaxes: **171**;
- harmful ambiguity: **0**;
- verifier counterexamples used in total: **3,626**;
- maximum counterexamples required in any world: **7**;
- identity-law failures for the retained constructor: **0**;
- associativity failures for the retained constructor: **0**.

The deterministic retained term was `F(G(x))` in **728/729** worlds. In the single degenerate world, the reachable algebra is trivial, so even the identity term is operationally indistinguishable from composition.

Most importantly, every syntactic ambiguity is operationally harmless: every survivor agrees extensionally with true composition on the entire reachable action algebra. Therefore a shortest retained survivor always inherits the correct identity and associativity laws on that reachable algebra.

The strongest safe conclusion is:

\[
\boxed{
\textbf{Counterexamples can synthesize the operative composition constructor from a grammar rather than a hand-listed law set.}
}
\]

and, in MSI terms:

\[
\boxed{
\textbf{the learner retains only the compositional structure that reachable behaviour can distinguish.}
}
\]

## What this does and does not establish

This crosses the previous boundary: the composition candidate itself is now generated rather than supplied as one item in a finite law menu.

It still assumes a minimal meta-language capable of applying primitive transformations to states and nesting those applications. No finite experiment can literally infer a syntax from no representational substrate at all. The meaningful developmental claim is instead that, given a weak generative language, verifier counterexamples can select the smallest operationally adequate compositional program from it.

Taken together with the Lean behavioural-congruence and typed-category theorems, the repo now has the following closed finite/theorem-level chain:

\[
\boxed{
\text{counterexample}
\to
\text{generated continuation/constructor}
\to
\text{new distinction}
\to
\text{behavioural congruence}
\to
\text{quotient dynamics}
\to
\text{composition preservation}.
}
\]

See `tests/test_constructor_genesis.py` for the exhaustive executable census.
