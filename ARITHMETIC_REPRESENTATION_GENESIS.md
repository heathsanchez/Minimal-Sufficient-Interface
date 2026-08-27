# Arithmetic Representation Genesis

The first arithmetic experiment fixed least-significant-digit-first processing and asked whether verifier-driven refinement could recover the hidden compositional state needed for addition. It did: the initially coarse history interface refined to exactly two behavioural classes and the learned quotient dynamics extrapolated exactly far beyond the discovery length.

This extension moves the developmental boundary outward again.

The learner is no longer told which direction positional digits should be processed.

## 1. Representation failure appears before hidden-state refinement

Consider a causal local decomposition that must emit the output digit corresponding to the current input position as that position is processed.

For most-significant-digit-first processing, even width two already gives a verifier counterexample. Two complete additions can present the same currently visible leading digit pair `(0,0)` but require different current output digits because an unseen lower-order suffix may later generate a carry.

Concretely:

- leading pair `(0,0)`, lower pair `(0,0)` requires tens output `0`;
- the same leading pair `(0,0)`, lower pair `(9,1)` requires tens output `1`.

No hidden state computed only from the already processed prefix can repair this, because the deciding information has not arrived yet.

This obstruction is formalized in Lean as `no_exact_msd_local_emitter` in [`lean/ArithmeticDirection.lean`](lean/ArithmeticDirection.lean).

So this is not search failure inside the current state representation. It is a failure of the decomposition itself.

## 2. Let verified counterexamples select the traversal

[`tests/test_arithmetic_representation_selection.py`](tests/test_arithmetic_representation_selection.py) offers two traversal hypotheses, most-significant-first and least-significant-first, and asks only whether verified local outputs are causally well-defined from the exposed prefix.

The verifier rejects the most-significant-first representation by a concrete conflicting pair and retains the least-significant-first representation.

Only after that representation choice is made does MSI residual refinement operate on history state.

From histories of length at most two, it again discovers exactly two behavioural interface states, with no supplied `carry` variable or transition table, freezes the learned transducer, and evaluates it on sixty-digit additions outside the discovery regime.

Thus the developmental chain has become

\[
\boxed{
\text{candidate decomposition}
\to
\text{verified causal failure}
\to
\text{representation selection}
\to
\text{behavioural residual}
\to
\text{latent interface refinement}
\to
\text{quotient dynamics}
\to
\text{length extrapolation}.
}
\]

## 3. Remove even the named direction hypotheses

The next test does not present labels such as `left-to-right` and `right-to-left`.

For width `n`, it mechanically generates every permutation of the `n` positional indices. A candidate order is rejected whenever it tries to emit a position before some lower-significance position capable of changing it through a carry chain.

[`tests/test_arithmetic_order_genesis.py`](tests/test_arithmetic_order_genesis.py) exhausts every order for widths two through seven. For each width, all incorrect orders admit a constructive verifier counterexample; the unique survivor is

\[
\boxed{0,1,2,\ldots,n-1}
\]

where position `0` is least significant.

This is important conceptually. The system is not rewarded for choosing the human phrase "right to left". It retains the unique processing order under which the local computation can actually be compositional.

The dependency structure is discovered negatively: every order that exposes an effect before its possible causes is eliminated by a verified future conflict.

## 4. Fixed output delay does not rescue the wrong decomposition

A natural objection is that most-significant-first processing might become compositional if the system simply waits a fixed number of positions before emitting an output.

[`tests/test_arithmetic_delay_boundary.py`](tests/test_arithmetic_delay_boundary.py) attacks that possibility directly. For every tested delay `D = 0,...,32`, it constructs two additions that are identical through the first `D+1` visible most-significant positions but require different first output digits. The distinguishing carry is generated one position farther into the unseen suffix and propagated backward through a chain of sum-nine positions.

Therefore no world-independent fixed delay can repair the most-significant-first causal decomposition for arbitrary-length exact addition:

\[
\boxed{
\forall D\;\exists\text{ a longer addition whose deciding carry lies beyond delay }D.
}
\]

This is the arithmetic analogue of the repo's no-uniform-lookahead falsifier. The issue is not insufficient search depth inside a good interface. The information flow points the wrong way.

## Interpretation

The arithmetic sequence now demonstrates two distinct developmental moves in one natural domain:

\[
\boxed{
\begin{array}{c}
\textbf{representation development:}\\
\text{choose an order in which local composition is causally possible}\\[4pt]
\downarrow\\[4pt]
\textbf{state/interface development:}\\
\text{retain exactly the hidden history distinction needed for future behaviour.}
\end{array}
}
\]

In ordinary terminology the resulting hidden distinction functions as carry. But the learner never needs that semantic label. What it discovers is the minimal behavioural state required by verified future consequences.

The stronger lesson is:

\[
\boxed{
\textbf{verified failures can select not only what state must be remembered,
but the decomposition in which a finite compositional state exists.}
}
\]

That is closer to structural development than merely fitting parameters inside a fixed architecture.

## Boundary

The experiment still supplies substantial structure:

- positional decimal notation;
- the decomposition into digit positions;
- exact trusted addition outcomes;
- the causal/local transducer objective;
- finite candidate orders or traversal hypotheses.

It does not discover positional notation, invent digits, or infer the task of addition from raw sensory data.

So the result should not be described as open-ended invention. It is a controlled domain-level demonstration that verified counterexamples can move the system outward through two levels of representation:

1. select the lawful compositional decomposition;
2. discover the minimal latent state inside that decomposition.

That is the current strongest arithmetic realization of the MSI developmental thesis.
