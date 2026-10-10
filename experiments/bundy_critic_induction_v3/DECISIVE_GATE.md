# V3 decisive implementation gate — evidence and falsifiers

Status: EXPERIMENT DESIGN; no V3 generator or Lean CI result claimed.

## Critical distinction
The training example's missing induction invariant is a relation over the free accumulator, not merely a lemma about the original goal. A valid constructor must derive an invariant schema from the recursor equations and the exact stuck proof state; it must not inspect protected task solutions or choose from a target-labelled menu.

## Scientific validity guards
1. Freeze the existing development_cases.json, protected_cases.json, FrozenSource.lean and preregistration commits. Record their source SHA-256 digests before generator construction.
2. Implement one target-neutral extraction of a recursive-step equation, the free accumulator variable, and the protected output relation. Keep candidate invariant construction separate from the Lean verifier.
3. Exhaust the declared old proof-plan language or return UNKNOWN_SEARCH. A tactic timeout is not a proof of inexpressibility.
4. Admit a generated critic only after Lean checks concrete generated proofs without sorry/admit, source-specific axiom additions or theorem-as-oracle lookups.
5. Run the frozen four positive protected families and the bad-accumulator negative. Never reinterpret a negative failure as a new positive.
6. Compare against strong stateless induction/generalization search under matched wall-time, candidate-check and Lean-check budgets. Also compare exact executable-memory replay, which should tie reach by construction.
7. Ablate the learned critic, a load-bearing training distinction, the induction hypothesis and irrelevant hypotheses separately.
8. Count development, synthesis, failed candidates, proof checking, persistence and future use. A reduction in runtime alone without all acquisition costs is not a lifecycle gain.
9. If the generator only instantiates a pre-written accumulator-generalization template, classify as bounded schema selection, not constructor genesis.
10. Require a second independently structured failure to induce a *new repair-constructor family*, not just another instance of the first, before claiming meta-level growth.

## Decision table
- WARRANTED: independently checked proof products and causally necessary generated operation, under the declared source and verifier boundary.
- REUSABLE: the exact frozen critic transfers to untouched protected tasks with no new target-specific engineering.
- REJECTED_ON_BOUNDARY: strong comparator ties protected reach and cost, or candidate is merely an existing repair template.
- UNKNOWN: incomplete old-language coverage, missing proof checks, untested future transfer or missing cost accounting.

## Strongest possible paper claim after success
A source-bound, independently replayable critic-development procedure constructs a typed induction-repair plan from a certified residual and transfers it across independent proof families under a fixed verifier and budget. This is not general theorem-prover completeness, nor primitive-free invention.
