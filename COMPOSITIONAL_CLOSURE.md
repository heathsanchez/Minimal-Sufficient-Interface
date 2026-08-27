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

The first proposed universe was `|X|=3`, binary `v`, and two deterministic generators. Exhaustive search covered 5,832 total worlds. Unexpectedly, there were **0** worlds where the one-step family `{id,g0,g1}` was too coarse relative to the full generated monoid. On this tiny universe, the one-step quotient already equals the full behavioural quotient in every case.

## Four-state result

At `|X|=4` with one deterministic generator, exhaustive search covered 4,096 worlds. Results:

- one-step quotient too coarse: **576** worlds;
- composite separators added by residual-driven refinement: **576**;
- convergence failures: **0**;
- congruence failures: **0**;
- quotient composition-law failures: **0**;
- exact ablation witnesses: **576**.

Thus every world converged to

\[
E_\infty=\bigcap_{f\in G^*}\ker(v\circ f),
\]

and the resulting relation was stable under every reachable action. Therefore each reachable transformation induces a well-defined quotient map and composition is preserved:

\[
[g\circ f]=[g]\circ[f].
\]

## General Lean theorem

The experimental endpoint now has a general monoid-action theorem counterpart in [`lean/BehaviouralCongruence.lean`](lean/BehaviouralCongruence.lean).

The Lean development proves that all-futures behavioural equivalence is an equivalence relation, is observation-compatible, is invariant under every reachable action, and contains every other reachable-action-invariant observation-compatible relation.

It also constructs the unique descended quotient action and proves identity and composition preservation. In the finite case, given any finite list covering every reachable action, any refinement process that adds a genuine reachable separator whenever one remains reaches the exact behavioural quotient within the size of that list. No greedy selection rule and no prior knowledge of the final quotient are assumed.

See [`BEHAVIOURAL_CONGRUENCE.md`](BEHAVIOURAL_CONGRUENCE.md) for the theorem package.

The strongest current statement is:

\[
\boxed{\text{MSI refinement computes the maximal observation-compatible behavioural congruence.}}
\]

The remaining open generalization is categorical rather than monoidal: typed morphisms, object-indexed observational congruences, quotient functoriality across objects, and eventually verifier-driven growth of the continuation category itself.

See `tests/test_compositional_closure.py` for the executable census.
