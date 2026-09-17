# QCK.FiniteLinear v1 — Executable Finite-Dimensional Consequences of QCK.Core

## Status

Design approved in chat on 2026-09-18. This document freezes the intended scope before implementation.

## Purpose

QCK.Core v1 is the frozen semantic kernel for finite context-stable certified substitution. It defines the canonical quotient

    N_C = ⋂ w, ker (C ∘ S_w)
    R_C = V / N_C

and proves induced dynamics/observation, all-word substitution, the universal/coarsest sufficient-linear-representation property, composable substitution certificates, and kernel-stability operation descent.

QCK.FiniteLinear v1 does not redefine that semantics. It derives executable finite-dimensional presentations, rank diagnostics, and optionality/reserve theorems from the frozen quotient.

Dependency direction is fixed:

    QCK.Core → QCK.FiniteLinear → QCK.API

`qcklean/QCKCore.lean` must remain byte-for-byte unchanged on this branch.

## 1. Mathematical setting

Work over a field `𝕜`. Assume finite-dimensional source and observation spaces where required. The action alphabet remains shared and finite for the executable closure theorems.

Authoritative imported semantic objects include `contextNullspace`, `Canonical`, `canonicalMap`, `Sufficient`, `KernelStable`, reduced dynamics, and substitution theorems from QCK.Core.

No PSD, inner product, probability, Choi/Kraus, approximation, cost model, or developmental policy belongs in this module.

## 2. Dual observation closure

Let `L₀ = range(C*)` inside the algebraic dual. For each generator `S a`, use the dual action `φ ↦ φ ∘ S a` and define

    L_{n+1} = L_n + Σ_a S_a*(L_n).

Because the source is finite-dimensional, the ascending chain stabilizes. Let `Lstar` be the stabilized space.

Prove the basis-free semantic characterization:

    Lstar = span { φ ∘ C ∘ S_w | φ ∈ Y*, w ∈ A* }

and the central duality theorem:

    Lstar = Ann(contextNullspace S C).

This theorem is the bridge from the frozen semantic quotient to finite executable coordinates.

## 3. Finite executable presentation

Choose a finite basis of `Lstar` and construct a linear presentation map `O : V → F^d` (or an equivalent finite function-space codomain natural to Mathlib).

Prove:

    ker O = contextNullspace S C.

Therefore `range O` is linearly equivalent to the canonical quotient `V / contextNullspace S C`.

`O` is explicitly non-canonical: basis choices may change coordinates without changing the semantic quotient. The theorem must state that `O` presents the Core quotient, never redefine the quotient by `O`.

## 4. Dimension and rank consequences

Derive:

    dim(V / N_C) = rank O.

For every sufficient finite-dimensional linear representation `q : V → R`, prove:

    rank q ≥ dim(V / N_C).

This is a corollary of the stronger Core universal property, not the foundational theorem. No runtime/program-size minimality claim is permitted.

## 5. Coordinate new-operation defect

The primary semantic condition remains:

    A(ker q) ⊆ ker q.

For a finite presentation `O`, define

    δ_A = rank([O; O A]) - rank(O).

Prove:

    δ_A = 0
      ↔ A(ker O) ⊆ ker O
      ↔ ∃ T_A, O A = T_A O.

When `δ_A > 0`, reuse the Core obstruction theorem to obtain a witness `v` with `O v = 0` and `O(A v) ≠ 0`.

Obstruction remains primary; the rank statistic is derived.

## 6. Snapshot optionality

Let current active kernel be `N₀ = ker O₀`. For future interfaces `Oᵢ`, define

    N_F = N₀ ∩ ⋂ᵢ ker Oᵢ.

Interpret `N₀ / N_F` as the distinctions forgotten now but required by the promised future portfolio.

Define

    r_snapshot = dim(N₀ / N_F).

Prove the equivalent stacked-rank formula in finite coordinates:

    r_snapshot = rank([O₀; O₁; ...; O_k]) - rank(O₀).

Necessity: any supplementary linear record `H x` enabling recovery of all promised future interfaces from `(O₀ x, H x)` adds at least `r_snapshot` independent dimensions.

Achievability: construct a complement realizing exactly that bound.

## 7. Maintained optionality

Snapshot recoverability is insufficient if the source may evolve before activation. Let `A_wait` be the fixed waiting-operation vocabulary and define

    N_maintained = ⋂_{w ∈ A_wait*} S_w^{-1}(N_F).

Prove its universal property:

1. `N_maintained ≤ N_F`;
2. each waiting generator preserves `N_maintained`;
3. any waiting-invariant subspace `W ≤ N_F` satisfies `W ≤ N_maintained`.

Thus `N_maintained` is the greatest waiting-action-invariant subspace contained in `N_F`.

Assuming the active kernel `N₀` is waiting-invariant, define

    r_maintained = dim(N₀ / N_maintained).

Prove `r_snapshot ≤ r_maintained`, with equality when snapshot-safe forgetting is already waiting-invariant.

## 8. Active/reserve block dynamics

Choose a finite presentation `Q = [O₀; H]` whose kernel is `N_maintained` and whose first component is active state.

Prove a coordinate form of the reduced dynamics:

    [a']   [T_a  0 ] [a]
    [r'] = [B_a D_a] [r].

The zero block certifies that ordinary active evolution does not read reserve state. The lower row remains explicit because reserve maintenance may still cost work.

No theorem or documentation may imply that inactive reserve is free.

## 9. Fixed-vocabulary shared-option submodularity

For a fixed context/action vocabulary, let `Lᵢ` denote optional future information subspaces and define

    r(S) = dim(L₀ + Σ_{i∈S} Lᵢ) - dim L₀.

Prove normalization, monotonicity, and

    r(S) + r(T) ≥ r(S ∪ T) + r(S ∩ T).

Also derive the marginal formula

    Δ_j(S) = dim L_j - dim(L_j ∩ (L₀ + Σ_{i∈S} Lᵢ))

and diminishing marginal dimension for `S ⊆ T`.

This theorem is only for adding optional observation obligations under a fixed relevant vocabulary.

## 10. Interacting-capability counterexample

Formalize the canonical three-coordinate counterexample where capability selection changes the generated context vocabulary.

Observe only `x₁`. Let `U` swap `x₁,x₂` and `V` swap `x₂,x₃`. Define `g(S)` as additional active dimension required by the closure generated by selected capabilities.

Prove:

    g(∅)=0, g({U})=1, g({V})=0, g({U,V})=2.

Hence

    g({U}) + g({V}) < g({U,V}) + g(∅),

so capability-generated representational cost need not be submodular.

This negative theorem is part of v1 specifically to prevent later policy layers from assuming diminishing marginal cost when capabilities themselves create mixed contexts.

## 11. Module boundaries

Expected new files:

- `qcklean/QCKFiniteLinear.lean`
- `qcklean/QCKFiniteLinearTest.lean`
- `.github/workflows/qck-finite-linear-v1.yml`
- a qualification/freeze manifest after completion.

`qcklean/QCKCore.lean` must not change.

The Lake project may add new module/test roots. No QCK.API typed residuals are implemented in this branch.

## 12. Verification strategy

Use RED → GREEN theorem-first development.

Frozen-Core integrity must verify that `qcklean/QCKCore.lean` still has Git blob SHA:

    b9b1921c49c9947a02009be124286cfe3c723cb4

The gate must fail if Core changes.

Qualification must reject `sorry`, `admit`, QCK-local `axiom`/`constant`, and `unsafe`; build the QCK target; check the full FiniteLinear interface; compile every QCK-owned Lean source directly; and report axiom dependencies of headline FiniteLinear theorems.

Positive interface checks must cover annihilator/closure, executable presentation, rank minimality, operation defect, snapshot reserve, maintained reserve universal property, block dynamics, and fixed-vocabulary submodularity.

The `U,V` counterexample must be a compiled Lean theorem with its explicit strict inequality, not prose-only documentation.

## 13. Claim boundary

QCK.FiniteLinear v1 establishes finite-dimensional linear consequences only. It does not prove nonlinear/global operational minimality, minimum program size/runtime/storage bytes, approximate/noisy sufficiency, optimal reserve portfolios, probabilities of future contracts, autonomous developmental choices, PSD/Gram/Hilbert/quantum structure, or general program/process equivalence.

## 14. Completion criterion

QCK.FiniteLinear v1 is complete only when:

1. frozen-Core integrity passes;
2. every stated v1 theorem is implemented in Lean;
3. the dedicated workflow is green;
4. no placeholders or local axioms are present;
5. both the positive submodularity theorem and negative interacting-capability counterexample compile;
6. the qualified theorem surface and remaining QCK.API frontier are recorded in a freeze manifest.

Final dependency direction:

    QCK.Core → QCK.FiniteLinear → QCK.API

Semantic authority flows only left-to-right.