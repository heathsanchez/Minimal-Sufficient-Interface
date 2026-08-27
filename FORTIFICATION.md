# Adversarial Fortification

This note records attempts to break the strongest developmental claims above the frozen MSI kernel.

The core equations

\[
E_{t+1}=E_t\wedge K_t
\qquad\text{and}\qquad
E_B=\bigcap_{c\in B}K_c
\]

survived. Several stronger claims did not. The failures sharpen the architecture.

## 1. Constructor genesis is representation-relative

The grammar-driven constructor experiment uses

\[
t ::= x\mid F(t)\mid G(t).
\]

That grammar can generate sequential composition, but it cannot represent every binary constructor. A concrete three-state counterexample uses

- `f = (0,0,2)`;
- `g = (1,0,1)`;
- hidden constructor `H(f,g)(x)=min(f(x),g(x))`.

The target map is `(0,0,1)`, and no unary action word realizes it, even when the grammar is extended well beyond the original depth bound.

Therefore:

\[
\boxed{
\text{counterexamples identify the right constructor only relative to an expressive hypothesis language.}
}
\]

An empty version space is evidence that the current constructor representation is inadequate **or** that some other assumption has failed; it is not by itself proof that the task is impossible.

See `tests/test_break_attempts.py`.

## 2. Representation repair can itself use MSI

The same failed min example admits a generic repair without naming `min` as a candidate law.

First enlarge the representation to all pointwise binary lookup tables

\[
\phi:X\times X\to X.
\]

Verifier constraints recover exactly the table entries needed on the reachable input support. Any remaining table ambiguity lies only on argument pairs that the current reachable algebra never presents, so every survivor is operationally equivalent there.

A second experiment diagnoses the missing representation more economically. Generate primitive trace features

\[
x,\ F(x),\ G(x),\ F(F(x)),\ F(G(x)),\ G(F(x)),\ G(G(x)).
\]

For true sequential composition, the minimum sufficient feature interface is the singleton

\[
\boxed{F(G(x))}.
\]

For the hidden pointwise-min constructor, **no singleton trace feature is sufficient**. Exhaustive residual analysis finds the minimum sufficient feature interface

\[
\boxed{(F(x),G(x))}.
\]

Once that pair is retained, the constructor is synthesized as a lookup table over the refined interface.

Thus representation failure and representation repair instantiate the same pattern:

\[
\boxed{
\text{merged examples with different verified outcomes}
\to
\text{separator feature}
\to
\text{refined interface}
\to
\text{sufficient constructor representation}.
}
\]

See `tests/test_fortification.py` and `tests/test_meta_interface_synthesis.py`.

## 3. Local observation is too weak; all-futures observation is enough in the finite census

The original constructor-learning experiments used exact state-valued execution feedback. That is stronger than MSI's intended protected observational boundary.

A direct attack replaces raw state equality by a single local binary observation. This breaks the safe-constructor claim: there are candidate constructors that agree with the true constructor under the immediate observation but differ under a later reachable context.

One explicit witness found automatically is

- `obs = (0,0,1)`;
- `a = (0,0,1)`;
- `b = (0,2,2)`;
- locally surviving bad constructor term `(0,0,1)`.

So:

\[
\boxed{
\text{one-step observational agreement does not certify constructor correctness.}
}
\]

The repair is exactly the behavioural principle already proved elsewhere in the repo. Give the verifier only the **all-reachable-futures observation signature** of the produced state, not its raw identity.

Across all 4,374 worlds formed by

- all 6 nonconstant binary observations on three states; and
- all 729 ordered primitive-map pairs,

the contextual verifier census found:

- `harmful_survivors = 0`;
- `raw_distinct_but_behaviourally_safe = 5,166`;
- at most 7 counterexamples in any world.

This is stronger than the raw-state version in the direction MSI actually wants: the verifier forgets state identity and retains only differences visible under protected reachable futures.

Hence:

\[
\boxed{
\text{constructor identity should itself be quotiented by behavioural equivalence.}
}
\]

See `tests/test_contextual_constructor_verification.py`.

## 4. Verifier soundness is a real trust assumption

A single false verifier label can eliminate the true constructor from the version space.

Worse, a richer hypothesis language can fit corrupted evidence perfectly. In the pointwise-table repair above, changing one verifier entry produces a different lookup table that exactly satisfies every corrupted constraint while disagreeing with the true hidden law.

So a failed version space does **not** uniquely diagnose representation failure, and a successful richer fit does **not** prove that language expansion was the correct diagnosis.

The same meta-level symptom can arise from at least three causes:

\[
\boxed{
\text{no consistent current hypothesis}
\Leftarrow
\begin{cases}
\text{language inadequate},\\
\text{verifier unsound},\\
\text{target/protected authority changed}.
\end{cases}
}
\]

Disambiguating those causes requires information outside bare version-space exhaustion: trusted verifier authority, provenance, replay, redundancy, or an explicit model of nonstationarity.

See `tests/test_fortification.py` and `tests/test_diagnostic_ambiguity.py`.

## 5. Meet refinement cannot retract stale evidence

The refinement law is intentionally monotone:

\[
E' = E\wedge K \le E.
\]

If a once-protected constraint is later withdrawn, another meet update cannot restore distinctions that were previously erased from the equivalence relation. The only way a meet update can also be a genuine coarsening is for it to have made no change.

This is now machine-checked in Lean as `MeetKernel.update_cannot_coarsen`.

At the concrete continuation level, `EquivalentOn.antitone_basis` proves the dual provenance law: removing active continuations can only coarsen observational identity.

Therefore dynamic authority requires a layer above the frozen kernel:

\[
\boxed{
\text{active provenance set}
\to
\text{recompute current meet}
}
\]

rather than pretending retraction is another refinement step.

See `lean/Kernel.lean` and `tests/test_fortification.py`.

## 6. There is no uniform finite lookahead bound

The all-futures theorem is exact, but a tempting practical shortcut is to replace “all reachable futures” with a fixed context-depth cutoff.

That shortcut is false in general.

For every tested horizon `H = 0,...,20`, `tests/test_horizon_boundary.py` constructs a deterministic finite world with two states whose protected observations agree after every continuation of length at most `H`, but differ after exactly `H+1` steps.

So there is no world-independent finite depth `H` such that

\[
\text{agreement through depth }H
\Rightarrow
\text{full behavioural equivalence}
\]

for arbitrary finite systems.

The correct operational principle is therefore adaptive:

\[
\boxed{
\text{search deeper while a residual can still be exposed; do not promote a fixed horizon to completeness.}
}
\]

This is consistent with the finite-recovery theorem, which assumes coverage of the relevant continuation family rather than a universal depth bound.

See `tests/test_horizon_boundary.py`.

## 7. Hidden-state refinement cannot repair a causally wrong decomposition

The arithmetic transfer gives a qualitatively different failure mode.

For exact positional addition processed most-significant-digit first, two complete inputs can expose the same currently visible prefix and current digit pair but require different current output digits because a carry is generated in an unseen lower-order suffix.

That means no amount of hidden state computed solely from the already processed prefix can make the local output well-defined. The deciding information has not arrived yet.

The width-two obstruction is machine-checked in Lean as `no_exact_msd_local_emitter` in `lean/ArithmeticDirection.lean`.

The finite representation selector therefore rejects most-significant-first processing and retains least-significant-first processing before performing ordinary MSI hidden-state refinement. `tests/test_arithmetic_order_genesis.py` strengthens this by generating every positional order for widths two through seven: every incorrect order is eliminated by a constructive verifier counterexample, leaving only increasing significance order.

So:

\[
\boxed{
\text{some residuals require changing the decomposition, not refining state inside it.}
}
\]

This is a concrete domain-level separation between search/state failure and representation/decomposition failure.

## 8. Fixed delay does not rescue the wrong arithmetic direction

A possible repair is to retain most-significant-first processing but delay output by some fixed number of positions.

`tests/test_arithmetic_delay_boundary.py` falsifies that shortcut. For every tested delay `D = 0,...,32`, it constructs a longer addition whose first `D+1` visible positions are identical across two examples while an unseen suffix changes the required first output digit through an arbitrarily long carry-propagation chain.

Thus no world-independent fixed delay is sufficient for arbitrary-length exact addition under that decomposition.

The structural message matches the general no-lookahead result:

\[
\boxed{
\text{bounded patience cannot compensate for information flowing opposite the chosen causal factorization.}
}
\]

## 9. Correctness does not uniquely identify representation granularity

The arithmetic transfer also breaks a stronger uniqueness claim.

Least-significant-first addition can be made exactly compositional with one decimal digit per local symbol, but also with two decimal digits per local symbol (equivalently base 100 chunks). Both decompositions admit a two-state hidden interface and exact held-out forty-digit computation.

So verifier correctness alone cannot tell the learner whether the “right” block is a digit, a two-digit chunk, or another operationally adequate grouping.

`tests/test_arithmetic_granularity_ambiguity.py` records this explicitly.

Therefore:

\[
\boxed{
\text{verification determines admissibility, not a unique representation among equally lawful ones.}
}
\]

A cost/value principle is needed above the verifier boundary to choose among operationally equivalent granularities. This is exactly the role of the repo's selection layer.

## What survived

The adversarial programme did **not** falsify:

- the meet-semilattice refinement law;
- the equality-kernel realization;
- exact stopping under stated coverage assumptions;
- the behavioural-congruence theorem;
- quotient descent and composition preservation;
- the typed behavioural quotient construction;
- monotone refinement under growth of an accessible continuation category;
- residual-driven recovery of the two-state arithmetic hidden interface once a lawful causal decomposition is used.

What broke were stronger developmental interpretations that omitted necessary assumptions about representation coverage, verifier authority, contextual coverage, retraction, search horizon, causal decomposition, or representation-selection criteria.

The fortified architecture is therefore:

\[
\boxed{
\begin{array}{c}
\text{trusted protected evidence + provenance}\\
\downarrow\\
\text{candidate decomposition / representation}\\
\downarrow\\
\text{verify causal and behavioural adequacy}\\
\downarrow\\
\text{MSI refinement / behavioural quotient}\\
\downarrow\\
\text{residual diagnosis}\\
\downarrow\\
\text{adaptive search inside current representation}\\
\downarrow\\
\text{if exhausted: distinguish state/search failure from representation/verifier/drift failure}\\
\downarrow\\
\text{justified representation expansion or decomposition change}\\
\downarrow\\
\text{select among lawful alternatives by explicit cost/value}\\
\downarrow\\
\text{replay + contextual verification + retention}
\end{array}
}
\]

The core stays frozen. The attack surface is now explicitly above it.
