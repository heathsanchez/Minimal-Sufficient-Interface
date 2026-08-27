# Counterexample-Driven Composition Discovery

This experiment asks a stricter question than the earlier compositional-closure census:

> Can the system recover the right compositional behavioural equivalence from verifier counterexamples **without being given the generated monoid, the target quotient, or the identity of the separating composite**?

The answer is yes in the exhaustive four-state setting tested here.

## What the learner is given

The learner receives only:

1. a finite state space `X`;
2. a protected observation `v : X -> O`;
3. primitive executable actions `g_i : X -> X`;
4. a generic sequential-execution constructor for finite words over those primitives;
5. verifier residuals in the form of a pair `(x,y)` that the current interface merges but some reachable future distinguishes.

It is **not** given:

- the generated transformation monoid `G*`;
- an enumeration of reachable composites;
- the final behavioural equivalence relation;
- the separating continuation responsible for a residual;
- category/monoid tables or quotient maps.

The complete closure is computed only on the verifier/judge side so that the experiment can certify whether the learner has really recovered the all-futures quotient.

## Development rule

The learner starts from the identity and primitive actions only.

When the verifier exposes a residual pair `(x,y)`, the learner enumerates primitive-action words by increasing length, executes each word, deduplicates extensionally, and keeps the first genuinely new composite `w` satisfying

\[
v(w(x)) \neq v(w(y)).
\]

That new continuation is retained and the interface is refined. The process repeats until the verifier can expose no residual.

Thus the loop is

\[
\boxed{
\text{counterexample pair}
\to
\text{blind word search}
\to
\text{synthesized composite separator}
\to
\text{interface refinement}.
}
\]

No separator identity is supplied by the verifier.

## Exhaustive result

The census covers all

- 16 binary observations on four states;
- 256 deterministic primitive maps;
- **4,096 total worlds**.

Results:

- worlds requiring a nonprimitive composite separator: **576**;
- synthesized composite separators: **576**;
- recovery failures: **0**;
- final behavioural-congruence failures: **0**;
- exact last-composite ablation witnesses: **576**.

In every world, the learned relation equals the hidden all-reachable-futures relation

\[
\boxed{
E_{\mathrm{learned}}
=
\bigcap_{f\in G^*}\ker(v\circ f).
}
\]

In every one of the 576 nontrivial worlds, removing the final synthesized composite restores an erroneous merge.

A representative witness has

- `v = (0,0,0,1)`;
- primitive `g = (0,2,3,0)`;
- verifier residual pair `(0,1)`;
- learner-synthesized word `(g,g)`;
- synthesized map `g^2 = (0,3,0,0)`.

The learner is never told that `g^2` is the needed separator. It constructs it because the counterexample makes the current representation falsifiable and the generic word search finds the shortest reachable intervention that resolves that falsification.

## Interpretation

This crosses an important boundary.

The earlier theorem says that **if all reachable continuations are available**, verifier-driven refinement recovers the maximal behavioural congruence.

This experiment shows that the separating continuations themselves need not be pre-enumerated. They can be **synthesized from primitive actions in response to counterexamples**, while the final compositional equivalence still emerges correctly.

The strongest safe statement is therefore:

\[
\boxed{
\textbf{Counterexamples can drive discovery of the composite continuations needed to recover behavioural congruence.}
}
\]

or more compactly:

\[
\boxed{
\textbf{The right compositional equivalence can be learned without supplying the composite separators.}
}
\]

## Important boundary

This does **not** yet mean the system discovered composition from nothing.

Sequential execution of primitive actions is still an available constructor. What is not supplied is the category/monoid closure, the useful composites, or the target congruence.

The next stronger target is therefore to make the **constructor family itself** developmental: begin with multiple possible ways of combining/interpreting primitive interventions, let verifier residuals select which composition law or typed constructor earns retention, and test whether the correct compositional structure itself is identified by counterexamples.

See `tests/test_counterexample_composition_discovery.py` for the executable exhaustive census.
