# Endogenous Capability Genesis

This experiment removes the remaining supplied-`O1` assumption from the finite developmental bridge.

## Setup

The current interface exposes a binary protected observation `v`. A second protected binary observation `t` is available only to the verifier.

If the current interface merges a pair that the verifier distinguishes, the verifier returns a residual witness:

\[
v(x)=v(y),\qquad t(x)\neq t(y).
\]

The constructor is not given an `O1` or an `O2`.

Its candidate language is frozen in advance as all deterministic transformations `X -> X` on a three-state universe, in lexicographic order.

## O1 synthesis rule

A candidate `h` is eligible only if:

1. it is genuinely outside the old executable closure;
2. it repairs the live residual using the already-available observation:

\[
v(h(x))\neq v(h(y));
\]

3. after retaining `h` and exposing `v∘h`, it creates at least one newly reachable transformation that is quotient-inadmissible before refinement and quotient-admissible after refinement.

Among eligible candidates, the search maximizes the **count** of such newly enabled capabilities and breaks ties lexicographically. This is a generic future-capability-value criterion: no desired `O1` or `O2` identity is supplied.

The selected transformation is retained as `O1`.

## O2 discovery

After the interface is refined by the induced continuation `v∘O1`, a separate blind search returns the lexicographically first newly enabled nonprimitive transformation. That result is called `O2` only after discovery.

The full tested chain is therefore:

\[
\boxed{
\text{verifier residual}
\to
\text{endogenous }O_1\text{ genesis}
\to
\text{new separator}
\to
Q_1
\to
\text{expanded closure}
\to
\text{autonomous }O_2\text{ discovery}
}
\]

## Exhaustive result

On the three-state binary-observation universe:

- 36 `(v,t)` worlds contain a live verifier residual;
- across those worlds and all 27 primitive generators, 648 residual-driven `O1` geneses satisfy the frozen search rule;
- all 648 produce the full residual-to-`O2` causal witness under the preregistered criterion.

One witness is:

- `v = (0,0,1)`
- protected verifier target `t = (0,1,0)`
- primitive `g = (0,0,0)`
- residual pair `(0,1)`
- synthesized `O1 = (1,2,0)`
- autonomously discovered `O2 = (2,0,1)`

Ablating `O1` removes `O2` from the old executable closure and restores the coarse relation on the residual pair.

## Claim boundary

This is a bounded finite existence-and-causality result. It does **not** show that arbitrary real-world verifier residuals induce useful operators, nor that the chosen future-capability-value criterion is uniquely correct or computationally cheap in large spaces.

What it does show is that the complete developmental chain can arise without supplying either `O1` or `O2` by identity: a verifier residual can drive generic capability search, the retained capability can refine the interface, and that refinement can change what an unchanged downstream search can discover.

Reproduction: `tests/test_endogenous_genesis.py`.
