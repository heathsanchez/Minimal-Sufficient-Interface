# QCK Core v1 — Finite Context-Stable Certified Substitution

## Scope

QCK-Core formalizes finite-dimensional linear certified substitution under a fixed action alphabet. The canonical object is the quotient by differences no admitted future can expose. Matrix presentations, ranks, PSD/Gram structure, cost models, general context translations, approximate equivalence, and developmental policy are outside the semantic core.

## Source model

Fix a field `𝕜`, vector spaces `V` and `Y`, an action alphabet `A`, generator maps `S a : V →ₗ[𝕜] V`, and an observation map `C : V →ₗ[𝕜] Y`.

For a finite word `w : List A`, `wordMap S w` is the corresponding composite action.

## Canonical nullspace and quotient

Define

`N_C = ⋂ w, ker (C ∘ wordMap S w)`.

Two source states are contextually equivalent exactly when their difference lies in `N_C`. The canonical replacement is `V ⧸ N_C` with quotient map `q_C = N_C.mkQ`.

## Core theorem stack

1. `wordMap` identity and append/composition laws.
2. Membership in `N_C` iff every admitted finite continuation observes zero.
3. `N_C` is invariant under every generator.
4. Contextual equivalence iff equality after the canonical quotient map.
5. Every generator descends to a unique reduced linear map on the canonical quotient.
6. The observation descends to the quotient.
7. Generator intertwining implies all-word intertwining and all-word observation substitution.
8. If a linear representation `q : V →ₗ[𝕜] R` is sufficient for every protected continuation, then `ker q ≤ N_C`.
9. Hence `q_C` factors uniquely through `q.range`, and the canonical quotient is the coarsest sufficient linear quotient.
10. Certified substitutions compose when their alphabets and generator interfaces agree.

## Operation-extension theorem

For a surjective presentation `q : V →ₗ[𝕜] R` and proposed source operation `Aop : V →ₗ[𝕜] V`, kernel stability

`Aop (ker q) ⊆ ker q`

is the primary obstruction. Prove it is equivalent to existence of a unique reduced operation `R →ₗ[𝕜] R` intertwining `q`. Failure yields a source difference erased by `q` but exposed after `Aop`.

## Optionality module after the core is green

For active kernel `N₀` and future interfaces with kernels `Nᵢ`, define snapshot-safe forgetting by intersection. Maintained-safe forgetting is the intersection of all preimages of the snapshot-safe space under waiting words; prove it is the greatest waiting-action-invariant subspace contained in the snapshot-safe space. Dimension/rank and submodularity results belong in `QCK.FiniteLinear`, not `QCK.Core`.

## Claim boundary

The core proves a universal property among linear representations under the declared action/observation contract. It does not prove universal operational minimization, nonlinear minimality, optimal cost, autonomous contract selection, noisy equivalence, or physical/quantum structure.
