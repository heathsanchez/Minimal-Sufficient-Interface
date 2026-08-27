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

For width `n`, [`tests/test_arithmetic_order_genesis.py`](tests/test_arithmetic_order_genesis.py) mechanically generates every permutation of the `n` positional indices. A candidate order is rejected whenever it tries to emit a position before some lower-significance position capable of changing it through a carry chain.

The exhaustive census covers widths two through seven. For each width, all incorrect orders admit a constructive verifier counterexample; the unique survivor is

\[
\boxed{0,1,2,\ldots,n-1}
\]

where position `0` is least significant.

The factorial census is only the judge. A stronger developmental test removes factorial search entirely.

[`tests/test_arithmetic_dependency_graph_learning.py`](tests/test_arithmetic_dependency_graph_learning.py) starts with **no causal precedence relation**. It proposes a topological order under the constraints learned so far. Whenever the proposal exposes a position before an unseen lower-significance cause, the verifier returns a concrete conflicting pair and justifies one new precedence edge

\[
 i\longrightarrow i+1.
\]

The learner retains that edge and proposes again. For widths 2, 3, 10, 32, and 128, exactly `n-1` structural counterexamples recover the full chain

\[
\boxed{0\to1\to2\to\cdots\to n-1}
\]

and therefore the unique causal processing order.

This matters because the representation is no longer selected by brute-force enumeration. The causal structure itself is accumulated from residuals:

\[
\boxed{
\text{bad structural proposal}
\to
\text{verified counterexample}
\to
\text{new precedence relation}
\to
\text{new compositional world}.
}
\]

The system is not rewarded for choosing the human phrase "right to left". It develops the dependency relation under which the local computation can actually be compositional.

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

## 5. The discovered hidden-state structure is not decimal-specific

[`tests/test_arithmetic_base_invariance.py`](tests/test_arithmetic_base_invariance.py) repeats the interface-discovery procedure independently in every positional base from 2 through 16.

For each base, the learner starts from an indiscriminate history interface and uses only equality of verified future output digits. In every base the minimum behavioural partition has exactly two states, and a single retained future context is enough to expose them.

The external judge can identify those two classes after the fact as carry-out `0` and carry-out `1`, but that semantic interpretation is not supplied to the learner.

So the structural object being recovered is invariant across a family of coordinate systems:

\[
\boxed{
\text{base changes}
\quad\text{but}\quad
\text{minimal behavioural memory for two-addend local addition remains two-state}.
}
\]

This does not mean the digit-specific transition tables themselves transfer unchanged across bases. The invariant is the minimal latent interface structure required by the compositional dependency.

## 6. Verification does not uniquely determine granularity

The attack also exposes an important non-uniqueness result.

[`tests/test_arithmetic_granularity_ambiguity.py`](tests/test_arithmetic_granularity_ambiguity.py) compares least-significant-first decompositions using one decimal digit per local symbol and two decimal digits per local symbol. Both admit exact two-state quotient dynamics and both compute held-out forty-digit additions exactly.

So compositional correctness alone does **not** tell the system whether the basic block should be a digit, a two-digit chunk, or some other lawful grouping.

That means the strongest possible claim is not that verifier pressure discovers one uniquely privileged representation. It discovers an equivalence class of representations that preserve the required futures. Choosing among equally lawful granularities requires another criterion such as cost, locality, description length, search complexity, or transfer value.

This reconnects the domain experiment to the repo's selection layer:

\[
\boxed{
\text{verification determines admissibility; a value/cost principle selects among admissible representations.}
}
\]

This is a useful fortification rather than a defect. MSI should erase distinctions that protected futures cannot justify, including distinctions between representational choices that are operationally equivalent at the protected boundary.

## Interpretation

The arithmetic sequence now demonstrates three distinct developmental moves in one natural domain:

\[
\boxed{
\begin{array}{c}
\textbf{structural development:}\\
\text{counterexamples build the causal dependency relation}\\[4pt]
\downarrow\\[4pt]
\textbf{state/interface development:}\\
\text{retain exactly the hidden history distinction needed for future behaviour}\\[4pt]
\downarrow\\[4pt]
\textbf{selection above correctness:}\\
\text{choose among multiple lawful interfaces by explicit resource/value criteria.}
\end{array}
}
\]

In ordinary terminology the resulting hidden distinction functions as carry. But the learner never needs that semantic label. What it discovers is the minimal behavioural state required by verified future consequences.

The stronger lesson is:

\[
\boxed{
\textbf{verified failures can alter both the dependency structure of composition
and the state distinctions carried across its interfaces.}
}
\]

That is closer to structural development than merely fitting parameters inside a fixed architecture.

## Boundary

The experiment still supplies substantial structure:

- positional notation and significance-indexed digit positions;
- exact trusted addition outcomes;
- the causal/local transducer objective;
- a grammar of candidate orderings or precedence relations;
- finite candidate chunkings when granularity is studied.

It does not discover positional notation, invent digits, infer the task of addition from raw sensory data, or derive a unique granularity from correctness alone.

So the result should not be described as open-ended invention. It is a controlled domain-level demonstration that verified counterexamples can move the system outward through multiple levels of representation:

1. grow a causal dependency structure from structural residuals;
2. discover the minimal latent state inside the resulting lawful decomposition;
3. expose the remaining operational equivalence class of lawful representations for a separate value/cost selector.

That is the current strongest arithmetic realization of the MSI developmental thesis.
