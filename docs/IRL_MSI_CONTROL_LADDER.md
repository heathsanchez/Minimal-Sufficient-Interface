# IRL-shaped control ladder for MSI constitutional identifiability

Status: executable finite control, not a claim that IRL lacks quotient or invariance theory.

## Purpose

This control asks a deliberately adversarial question: does the MSI constitutional package merely rediscover standard partial-identifiability structure already known in inverse reinforcement learning, or does the quotient-to-realization layer add a distinct obligation?

The control must first reproduce known IRL ambiguity faithfully. Only after that is any MSI-specific comparison admissible.

## Literature anchor

The experiment is aligned with established IRL results rather than positioned against a strawman.

- Cao, Cohen & Szpruch (NeurIPS 2021), *Identifiability in inverse reinforcement learning*: reward reconstruction is generally non-identifiable; under entropy regularization they characterize reward functions producing a given policy and conditions under which additional environments/discount factors restore identifiability up to a constant. https://proceedings.neurips.cc/paper/2021/hash/671f0311e2754fcdd37f70a8550379bc-Abstract.html
- Kim, Garg, Shiragur & Ermon (ICML 2021), *Reward Identification in Inverse Reinforcement Learning*: formalizes reward identifiability modulo an equivalence relation and gives identifiability conditions for deterministic MDPs under MaxEntRL. https://proceedings.mlr.press/v139/kim21c.html
- Skalse, Farrugia-Roberts, Russell, Abate & Gleave (ICML 2023), *Invariance in Policy Optimisation and Partial Identifiability in Reward Learning*: characterizes ambiguities of reward-learning data sources and compares them with invariances tolerated by downstream tasks. https://proceedings.mlr.press/v202/skalse23a.html

These sources already establish the legitimacy of reward equivalence classes / fibres / invariances. MSI does not claim invention of that layer.

## Frozen finite model

Reward universe:

\[
R=\{-3,-2,-1,0,1,2,3\}^2,
\qquad |R|=49.
\]

There is one state and two actions. For an entropy-regularized policy at any fixed nonzero inverse temperature \(\beta\), the action probability is an injective function of

\[
d=r_1-r_0.
\]

We therefore use \(d\) as an exact symbolic soft-policy signature, avoiding floating-point tolerance.

Two rewards induce the same soft policy exactly when

\[
r_1-r_0=s_1-s_0,
\]

which on this two-action model is exactly additive-shift equivalence:

\[
s=r+c(1,1).
\]

## Twelve control gates

1. **Known equivalence recovery.** Exhaust all \(49^2=2401\) reward pairs and prove policy-kernel equality iff additive-shift equivalence.
2. **Partial-identifiability census.** Recover 13 soft-policy classes and 91 ambiguous unordered reward pairs.
3. **Downstream factorization.** Optimal action must factor through the soft-policy quotient.
4. **Gauge fixing.** The canonical representative \((0,d)\) represents every quotient class without pretending the true reward was identified.
5. **Temperature control.** Multiple fixed nonzero temperatures preserve the same additive-shift kernel in this model.
6. **Postprocessing control.** A function of the policy signature cannot split a policy fibre.
7. **Prior control.** Different priors can select different representatives while adding no policy information.
8. **External-anchor control.** Adding absolute reward coordinate \(r_0\) removes the ambiguity; exact ablation restores it.
9. **Data-source coarsening.** Observing only optimal action yields a strictly coarser three-class quotient and additional residuals.
10. **MSI repair control.** Meeting the coarse optimal-action kernel with the protected soft-policy signature yields exactly the soft-policy quotient.
11. **Misspecification residual.** A sign-only behavioural model merges rewards separated by the true soft-policy signature, producing explicit residual pairs.
12. **Stopping control.** Reward representative identity is not needed when the protected downstream query is already invariant across the policy fibre.

## Comparison with the constitutional experiment

The IRL control establishes the familiar layer

\[
\text{latent reward}
\to
\text{behavioural observation}
\to
\text{equivalence class / quotient}
\to
\text{downstream invariance test}.
\]

MSI should agree with that. In this finite control it does: when optimal action is the protected downstream question, the soft-policy quotient is sufficient and the system should stop. Choosing a gauge-fixed reward representative does not create new evidence and is not required for the protected task.

The constitutional finite witness asks a different second-layer question. There the abstract repaired quotient \(E^+\) is fixed, yet within a declared implementation language there are multiple concrete interface realizations with different operational cost profiles for later protected questions. The distinction is therefore:

\[
\underbrace{\text{which latent points are observationally equivalent}}_{\text{standard partial identifiability}}
\qquad\text{vs}\qquad
\underbrace{\text{how the required quotient is concretely realized}}_{\text{MSI realization layer}}.
\]

The current finite evidence supports the existence of that second layer in the constitutional model. It does **not** establish that IRL theory globally lacks analogous structured realization questions, nor that this layer is universally nontrivial.

## Falsifiers

The control fails if any of the following occurs under the frozen universe:

- the soft-policy kernel differs from additive-shift equivalence;
- class count is not 13 or ambiguity count is not 91;
- optimal action varies inside a soft-policy class;
- an evidence-only postprocessor splits a policy class;
- absolute-coordinate ablation fails to restore the original ambiguity;
- the MSI meet repair differs from the protected soft-policy quotient;
- the misspecified sign model has no residual pair.

## Scientific interpretation

If all gates pass, the warranted conclusion is modest but useful:

> MSI reproduces a known partial-identifiability/invariance pattern in a finite IRL-shaped control, correctly stops when the quotient is sufficient for the protected downstream task, and separately exposes a quotient-realization distinction in the constitutional finite model.

That is a calibration result, not a global novelty theorem.
