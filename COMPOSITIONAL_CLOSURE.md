# Compositional Closure Result

This experiment tests whether repeated verifier-driven refinement recovers exactly the behavioural equivalence induced by all reachable composite futures.

Let `G` be a finite generator set of deterministic transformations on a finite state space `X`, let `G*` be its transformation monoid under composition, and let `v : X -> O` be the protected observation. Define

\[
x \sim_* y
\iff
\forall f\in G^*,\; v(f(x))=v(f(y)).
\]

Development begins from only the one-step continuations and repeatedly adds a reachable composite continuation whenever it separates a pair still merged by the current interface.

## Three-state boundary

The first proposed universe was `|X|=3`, binary `v`, and two deterministic generators. Exhaustive search covered

- 8 observations,
- 27 x 27 ordered generator pairs,
- 5,832 total worlds.

Unexpectedly, there were **0** worlds where the one-step family `{id,g0,g1}` was too coarse relative to the full generated monoid. On this tiny universe, the one-step quotient already equals the full behavioural quotient in every case.

This falsifies the expectation that three states would exhibit a necessary composite separator.

## Four-state result

The smallest tested setting where the intended phenomenon appears cleanly is `|X|=4` with one deterministic generator. Exhaustive search covered

- 16 binary observations,
- 256 deterministic generators,
- 4,096 total worlds.

Results:

- one-step quotient too coarse: **576** worlds;
- composite separators added by residual-driven refinement: **576**;
- convergence failures: **0**;
- congruence failures at the final behavioural quotient: **0**;
- quotient composition-law failures: **0**;
- exact ablation witnesses: **576**.

Thus every world converged to

\[
E_\infty
=
\bigcap_{f\in G^*}\ker(v\circ f),
\]

and the resulting relation was stable under every reachable action:

\[
x\sim_* y
\Longrightarrow
g(x)\sim_*g(y)
\qquad \forall g\in G^*.
\]

Therefore each reachable transformation induces a well-defined map on the quotient, and composition is preserved:

\[
[g\circ f]=[g]\circ[f].
\]

The ablation arm removes the last required composite separator and verifies that an erroneous merge returns in every one of the 576 worlds that required compositional refinement.

## Interpretation

Within this exhaustive finite setting, repeated verified refinement does not merely recover an observation-preserving equivalence. It recovers the behavioural congruence induced by all reachable futures, and the compressed quotient retains the composition law of the executable dynamics.

The strongest safe statement is:

\[
\boxed{\text{Developmental refinement recovered the behavioural congruence from compositional residuals.}}
\]

This is a finite result, not yet a general theorem for arbitrary state spaces, action categories, or verifier families.

See `tests/test_compositional_closure.py` for the executable census.
