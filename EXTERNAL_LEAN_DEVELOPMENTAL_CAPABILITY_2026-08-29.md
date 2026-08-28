# External Lean developmental capability — 2026-08-29

This note records the first MSI result in this repo where the developmental structure is learned from an **independent real formal verifier** and then shown to cause a new capability under a frozen verifier budget.

## 1. External task-only interface genesis

Experiment: `experiments/lean_external_task_only_genesis.py`

Deciding workflow run: **33212554003**

The learner interacts with the real `lean` executable. For every probe, stdout and stderr are suppressed. The learner receives only the process success/failure bit.

It is not supplied:

- Lean type names;
- source or destination types of operations;
- compiler diagnostics;
- a composition table;
- a cross-token translation;
- the held-back operator's attachment point.

From task outcomes alone it reconstructs an anonymous operational interface and is then tested on unseen compositions and a structural intervention.

Result:

- anonymous presentations: **4**;
- exact recovered structures: **4/4**;
- acquisition/compiler queries: **352**;
- unseen length-3 programs: **16,000/16,000** predicted correctly;
- post-intervention predictions after attaching a held-back operation: **336/336**;
- flat/untyped ablation errors: **15,696**;
- Lean diagnostics exposed to learner: **0**;
- final independently compiled/rejected witness gate: **12/12**.

Thus, in this fixed finite Lean operator corpus,

\[
\boxed{
\text{Lean accept/reject residuals}
\to
\text{latent operational interface}
\to
\text{exact unseen compositional prediction}
}
\]

with a causal ablation showing that the flat representation is insufficient.

## 2. Budgeted capability synthesis

Experiment: `experiments/lean_external_capability_synthesis.py`

Deciding workflow run: **33212842416**

This is the causal follow-up. COLD and WARM receive the same primitive vocabulary, starting object, frozen depth-5 candidate enumeration, hidden terminal context, external Lean verifier and synthesis budget.

The only difference is that WARM may locally reject a candidate when the operational interface learned from prior accept/reject experience proves that the candidate cannot compose.

Frozen synthesis budget:

\[
B=32\text{ Lean verifier calls}.
\]

Result:

- interface acquisition: **80** prior binary Lean queries;
- COLD / flat search: **FAIL after 32/32 verifier calls**;
- WARM / learned-interface search: **PASS in 4 verifier calls**;
- candidates rejected locally from learned structure before wasting verifier calls: **40,004**;
- accepted depth-5 witness: `q4-q0-q0-q0-q7`;
- diagnostics exposed: **0**;
- final verifier: real `lean` executable.

Therefore the learned representation is not merely descriptive. Under the frozen bounded protocol it changes the reachable capability frontier:

\[
\boxed{
\text{verified experience}
\to
\text{learned latent interface}
\to
\text{search-space contraction}
\to
\text{new Lean-verified capability within budget}.
}
\]

Ablating the learned interface returns exactly to COLD and removes the capability under the same budget.

## 3. Joined MSI chain

Together with the existing formal and exhaustive results in this repository, the current strongest chain is

\[
\boxed{
\rho
\to
[f]_{\mathrm{beh}}^{\min}
\to
\operatorname{Adjoin}(\mathcal C_t,f)
\to
Q_{t+1}
\to
\text{learned external operational structure}
\to
\text{strictly changed verified capability frontier}.
}
\]

The important new fact is that the final two arrows are now decided by **Lean itself**, not by a synthetic Python oracle.

## 4. Scientific boundary

This does **not** prove unrestricted autonomous mathematical discovery.

The finite operator corpus and syntactic term grammar are still supplied by the experimenter. The latent structure recovered here corresponds to operational typing/compatibility already enforced by Lean. The system reconstructs that structure from behavioural evidence; it does not invent Lean's type theory or discover a previously unknown theorem of mathematics.

What is now supported is narrower and stronger than the previous synthetic claim:

> In a fixed finite external formal domain, binary verifier experience can recover a latent operational representation that is causally necessary for efficient generalization and can enable a new verifier-certified construction under a resource bound where the unstructured representation fails.

The next genuinely stronger boundary is source-distinct theorem discovery: transfer this mechanism to an independently authored Lean theorem corpus, with no hand-designed operator graph, and require a previously unseen proof/construction that becomes reachable only after residual-driven representation acquisition.
