# IRL-shaped control ladder for MSI constitutional identifiability

Status: executable finite control, not a claim that IRL lacks quotient, invariance, or realization structure.

## Purpose

This control asks a deliberately adversarial question: does the MSI constitutional package merely rediscover standard partial-identifiability structure already known in inverse reinforcement learning, and if a quotient-to-realization layer appears, is that layer actually specific to the constitutional example?

The control must first reproduce known IRL ambiguity faithfully. Only after that is any MSI-specific comparison admissible.

## Literature anchor

The experiment is aligned with established IRL results rather than positioned against a strawman.

- Cao, Cohen & Szpruch (NeurIPS 2021), *Identifiability in inverse reinforcement learning*: reward reconstruction is generally non-identifiable; under entropy regularization they characterize reward functions producing a given policy and conditions under which additional environments/discount factors restore identifiability up to a constant. https://proceedings.neurips.cc/paper/2021/hash/671f0311e2754fcdd37f70a8550379bc-Abstract.html
- Kim, Garg, Shiragur & Ermon (ICML 2021), *Reward Identification in Inverse Reinforcement Learning*: formalizes reward identifiability modulo an equivalence relation and gives identifiability conditions for deterministic MDPs under MaxEntRL. https://proceedings.mlr.press/v139/kim21c.html
- Skalse, Farrugia-Roberts, Russell, Abate & Gleave (ICML 2023), *Invariance in Policy Optimisation and Partial Identifiability in Reward Learning*: characterizes ambiguities of reward-learning data sources and compares them with invariances tolerated by downstream tasks. https://proceedings.mlr.press/v202/skalse23a.html

These sources already establish the legitimacy of reward equivalence classes / fibres / invariances. MSI does not claim invention of that layer.

## Frozen finite soft-policy model

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

## Independent exact-gap realization control

A separate finite control over \(\{-2,-1,0,1,2\}^2\) protects exact reward identity after observing only the gap \(d=r_1-r_0\). Adding either primitive coordinate \(r_0\) or \(r_1\) produces the same discrete repaired kernel:

\[
\ker(d,r_0)=\ker(d,r_1)=\ker(\mathrm{id}_R).
\]

Under the frozen operational language where a retained primitive costs 1 and reconstructing the other reward coordinate with one add/subtract operation costs 2, the two lawful realizations have opposite future-query profiles:

\[
(r_0\text{-realizer})=(1,2),\qquad
(r_1\text{-realizer})=(2,1).
\]

Thus an IRL-shaped control itself exhibits:

\[
\text{same required quotient} + \text{multiple operational realizations}.
\]

This directly falsifies any claim that the quotient-to-realization distinction is unique to the constitutional example.

## Potential-shaping control

A second control uses a deterministic two-path, two-step reward family with \(\gamma=1/2\), 81 base reward vectors, and all 27 potentials in \(\{-1,0,1\}^3\). Across all 2,187 shaping interventions,

\[
r'(s,a,s')=r(s,a,s')+\gamma\Phi(s')-\Phi(s)
\]

preserves return difference and therefore optimal choice, while changing the concrete reward vector in 2,106 interventions. The finite search generates 1,297 distinct shaped reward vectors from 81 base rewards while the protected quotient remains unchanged.

The same control also recovers a strict interface-refinement lattice:

\[
\ker(\mathrm{full\ reward})
\subsetneq
\ker(\mathrm{return\ difference})
\subsetneq
\ker(\mathrm{optimal\ choice}),
\]

with class counts \(81>13>3\) and ambiguity counts \(0<310<1200\). Protecting a literal transition reward, which is not shaping-invariant, generates 202 residual pairs and forces refinement beyond the return-difference quotient.

## Corrected comparison with the constitutional experiment

The IRL controls establish that both of the following are already meaningful in a standard partial-identifiability setting:

\[
\underbrace{\text{which latent points are observationally equivalent}}_{\text{quotient / partial identifiability}}
\]

and

\[
\underbrace{\text{how a sufficient quotient is concretely represented or transformed}}_{\text{realization / gauge / shaping structure}}.
\]

Therefore MSI should **not** claim novelty from the bare existence of a quotient-realization distinction.

The stronger MSI object is the developmental composition:

\[
I
\to
\text{failed factorization}
\to
E^+
\to
\mathcal V(E^+;\mathcal H)
\to
\text{later protected consequence}
\to
\text{certified residual}
\to
\text{minimal refinement or fixed point},
\]

with explicit attachment, replay, provenance, ablation, and stopping conditions. The constitutional and IRL controls are now calibration domains for that same machine rather than evidence that one domain contains a uniquely new mathematical layer.

## Falsifiers

The soft-policy control fails if any of the following occurs under the frozen universe:

- the soft-policy kernel differs from additive-shift equivalence;
- class count is not 13 or ambiguity count is not 91;
- optimal action varies inside a soft-policy class;
- an evidence-only postprocessor splits a policy class;
- absolute-coordinate ablation fails to restore the original ambiguity;
- the MSI meet repair differs from the protected soft-policy quotient;
- the misspecified sign model has no residual pair.

The realization control fails if \(\ker(d,r_0)\neq\ker(d,r_1)\), if either differs from exact reward identity, or if the frozen operational profiles cease to differ.

The shaping control fails if any enumerated potential-shaping intervention changes return difference or optimal choice, if the refinement lattice ceases to be strict, or if the reported census counts change under the frozen universe.

## Scientific interpretation

The warranted conclusion is now stronger and more conservative at the same time:

> MSI reproduces known partial-identifiability and invariance structure in finite IRL-shaped controls, correctly stops when the current quotient is sufficient for protected downstream tasks, detects when non-invariant protected questions require refinement, and tracks multiple concrete realizations without claiming that realization structure is unique to MSI or to constitutional reasoning.

The remaining candidate contribution is the **verifier-governed developmental calculus linking these layers**, not any one layer in isolation.
