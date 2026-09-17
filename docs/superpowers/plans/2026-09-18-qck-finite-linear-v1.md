# QCK.FiniteLinear v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive finite executable presentations, rank/defect diagnostics, snapshot and maintained optionality, and the fixed-vocabulary/non-submodular-capability boundary from the frozen QCK.Core quotient.

**Architecture:** `QCKFiniteLinear.lean` imports the frozen `QCKCore` and remains quotient-first. The primary finite presentation evaluates a source state against the finite future-observable dual subspace; basis coordinates and rank formulas are derived consequences. A dedicated workflow rejects any mutation of the frozen Core and independently qualifies the FiniteLinear theorem surface.

**Tech Stack:** Lean 4 `v4.35.0-rc2`; Mathlib commit `44ba35c6daa9d69aff8fed9fff9bbde17ded774d`; GitHub Actions Ubuntu 24.04.

**Spec:** `docs/superpowers/specs/2026-09-18-qck-finite-linear-v1-design.md`

## Global Constraints

- `qcklean/QCKCore.lean` must retain Git blob SHA `b9b1921c49c9947a02009be124286cfe3c723cb4`.
- Dependency direction is exactly `QCK.Core → QCK.FiniteLinear → QCK.API`.
- Kernel/submodule statements are authoritative; coordinates, finrank, and defect statistics are corollaries.
- The action alphabet is finite where finite closure computation requires it.
- No PSD/Gram/Hilbert/quantum structure, noisy equivalence, runtime policy, autonomous contract choice, or QCK.API authority types are added.
- No `sorry`, `admit`, QCK-local `axiom`/`constant`, or `unsafe` is permitted.
- Each task follows RED → GREEN and ends with a reviewable commit.

---

## File Structure

- Create `qcklean/QCKFiniteLinear.lean`: all finite-dimensional definitions and theorems.
- Create `qcklean/QCKFiniteLinearTest.lean`: compile-time public-interface checks.
- Modify `qcklean/lakefile.lean`: add FiniteLinear module/test roots only.
- Create `.github/workflows/qck-finite-linear-v1.yml`: frozen-Core integrity and FiniteLinear qualification.
- Create `QCK_FINITE_LINEAR_V1.md` only after all theorem gates are green.
- Do not edit `qcklean/QCKCore.lean`.

---

### Task 1: Establish the RED interface and immutable-Core gate

**Files:**
- Create: `qcklean/QCKFiniteLinearTest.lean`
- Modify: `qcklean/lakefile.lean`
- Create: `.github/workflows/qck-finite-linear-v1.yml`

**Interfaces:**
- Consumes: frozen module `QCKCore`.
- Produces: a deliberately failing `QCKFiniteLinear` import and a CI gate that checks Core before Lean compilation.

- [ ] **Step 1: Extend the Lake roots**

Use this exact root list:

```lean
@[default_target]
lean_lib QCK where
  srcDir := "."
  roots := #[`QCKCore, `QCKCoreTest, `QCKFiniteLinear, `QCKFiniteLinearTest]
```

- [ ] **Step 2: Create the failing interface test**

Create `qcklean/QCKFiniteLinearTest.lean`:

```lean
import QCKFiniteLinear

open QCK

#check QCK.futureObservableSpan
#check QCK.futureObservableSpan_dualCoannihilator
#check QCK.futureObservableSpan_eq_dualAnnihilator
#check QCK.finitePresentation
#check QCK.finitePresentation_ker
#check QCK.canonicalEquivFinitePresentation
#check QCK.canonical_finrank_eq_futureObservableSpan
#check QCK.sufficient_rank_ge_canonical
#check QCK.operationDefect
#check QCK.operationDefect_eq_zero_iff
#check QCK.snapshotSafe
#check QCK.snapshotReserveFinrank
#check QCK.snapshotReserveMap
#check QCK.maintainedSafe
#check QCK.maintainedSafe_greatest
#check QCK.snapshotReserve_le_maintainedReserve
#check QCK.combined_first_component_independent
#check QCK.reserveRank
#check QCK.reserveRank_submodular
#check QCK.interactingCapability_not_submodular
```

- [ ] **Step 3: Create the dedicated workflow**

The workflow must begin with this frozen-source check:

```yaml
- name: Verify frozen QCK Core
  run: |
    test "$(git hash-object qcklean/QCKCore.lean)" = \
      "b9b1921c49c9947a02009be124286cfe3c723cb4"
```

Then use the same pinned Lean/Mathlib setup as `qck-core-v1.yml`, reject forbidden tokens only in repository-owned `QCK*.lean`, run `lake build QCK`, run `lake env lean QCKFiniteLinearTest.lean`, compile every QCK-owned source directly, and print axioms for the headline FiniteLinear theorems.

- [ ] **Step 4: Push and verify intentional RED**

Expected sequence: frozen-Core check PASS; toolchain/Mathlib setup PASS; build FAIL because `QCKFiniteLinear` does not exist.

- [ ] **Step 5: Commit**

```bash
git add qcklean/lakefile.lean qcklean/QCKFiniteLinearTest.lean .github/workflows/qck-finite-linear-v1.yml
git commit -m "Add QCK FiniteLinear red qualification gate"
```

---

### Task 2: Define the finite future-observable dual space

**Files:**
- Create: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Consumes: `QCK.wordMap`, `QCK.contextNullspace`.
- Produces: `futureObservableSpan`, `closureStep`, `closureIter`, finite stabilization.

- [ ] **Step 1: Add imports and variables**

Use:

```lean
import QCKCore
import Mathlib.LinearAlgebra.Dual.Lemmas
import Mathlib.LinearAlgebra.Dimension.RankNullity
import Mathlib.LinearAlgebra.FiniteDimensional.Lemmas
import Mathlib.LinearAlgebra.Pi
import Mathlib.LinearAlgebra.Prod
import Mathlib.LinearAlgebra.Projection

namespace QCK

open Module Submodule LinearMap
noncomputable section

universe u v y r

variable {𝕜 : Type u} [Field 𝕜]
variable {V : Type v} [AddCommGroup V] [Module 𝕜 V] [FiniteDimensional 𝕜 V]
variable {Y : Type y} [AddCommGroup Y] [Module 𝕜 Y] [FiniteDimensional 𝕜 Y]
variable {A : Type*} [Fintype A]
```

- [ ] **Step 2: Define the semantic dual span**

```lean
def futureObservableSpan
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    Submodule 𝕜 (Module.Dual 𝕜 V) :=
  ⨆ w : List A, LinearMap.range (C.comp (wordMap S w)).dualMap
```

- [ ] **Step 3: Define constructive closure iteration**

```lean
def closureStep
    (S : A → V →ₗ[𝕜] V)
    (L : Submodule 𝕜 (Module.Dual 𝕜 V)) :
    Submodule 𝕜 (Module.Dual 𝕜 V) :=
  L ⊔ ⨆ a : A, L.map (S a).dualMap

def closureIter
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    ℕ → Submodule 𝕜 (Module.Dual 𝕜 V)
  | 0 => LinearMap.range C.dualMap
  | n + 1 => closureStep S (closureIter S C n)
```

- [ ] **Step 4: Add theorem checks before proofs**

```lean
#check QCK.closureIter_mono
#check QCK.iSup_closureIter_eq_futureObservableSpan
#check QCK.closureIter_stabilizes
```

- [ ] **Step 5: Prove monotonicity and word coverage**

Prove `closureIter_mono` from `L ≤ closureStep S L`. Prove by induction on word length that every range `(C.comp (wordMap S w)).dualMap` is contained in the corresponding closure stage. Prove the reverse inclusion by induction on `closureIter`, using `LinearMap.dualMap_comp_dualMap` to identify the generator extension.

- [ ] **Step 6: Prove finite stabilization**

Package the monotone chain as an order hom `ℕ →o Submodule 𝕜 (Module.Dual 𝕜 V)`. Use the finite-generation stabilization theorem `Submodule.FG.stabilizes_of_iSup_eq` with the equality from Step 5. The finite-dimensional ambient dual gives finite generation.

Target theorem:

```lean
theorem closureIter_stabilizes (S) (C) :
    ∃ n, closureIter S C n = futureObservableSpan S C
```

- [ ] **Step 7: Run and commit**

```bash
cd qcklean
lake env lean QCKFiniteLinear.lean
lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Formalize QCK finite observation closure"
```

---

### Task 3: Identify the annihilator and build the canonical finite presentation

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Consumes: `futureObservableSpan`, Core `contextNullspace`.
- Produces: dual/coannihilator equality, `finitePresentation`, its kernel and quotient equivalence.

- [ ] **Step 1: Add RED theorem checks**

```lean
#check QCK.futureObservableSpan_dualCoannihilator
#check QCK.futureObservableSpan_eq_dualAnnihilator
#check QCK.finitePresentation_apply
#check QCK.finitePresentation_ker
#check QCK.finitePresentation_surjective
#check QCK.canonicalEquivFinitePresentation
```

- [ ] **Step 2: Prove the coannihilator theorem**

Target:

```lean
theorem futureObservableSpan_dualCoannihilator
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    (futureObservableSpan S C).dualCoannihilator = contextNullspace S C
```

Proof by extensional membership: membership in the coannihilator says every future-observable functional vanishes. Use `LinearMap.dualMap_apply` and `Module.forall_dual_apply_eq_zero_iff` to convert that to `C (wordMap S w x) = 0` for every word, then use `mem_contextNullspace_iff`.

- [ ] **Step 3: Derive the annihilator equality**

Use finite-dimensional reflexivity:

```lean
theorem futureObservableSpan_eq_dualAnnihilator (S) (C) :
    futureObservableSpan S C = (contextNullspace S C).dualAnnihilator
```

Rewrite by `futureObservableSpan_dualCoannihilator` and use `Subspace.dualCoannihilator_dualAnnihilator_eq`.

- [ ] **Step 4: Define the executable presentation by evaluation**

Let `W := futureObservableSpan S C`. Mathlib already provides the perfect finite-dimensional pairing
`W.quotDualCoannihilatorToDual : V ⧸ W.dualCoannihilator →ₗ[𝕜] Module.Dual 𝕜 W`.

Define:

```lean
def finitePresentation (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    V →ₗ[𝕜] Module.Dual 𝕜 (futureObservableSpan S C) :=
  (futureObservableSpan S C).quotDualCoannihilatorToDual.comp
    (futureObservableSpan S C).dualCoannihilator.mkQ
```

and prove:

```lean
@[simp] theorem finitePresentation_apply (S) (C) (x : V)
    (φ : futureObservableSpan S C) :
    finitePresentation S C x φ = φ.1 x
```

using `Submodule.quotDualCoannihilatorToDual_apply`.

- [ ] **Step 5: Prove kernel and surjectivity**

Use `Submodule.quotDualCoannihilatorToDual_bijective`, quotient-map surjectivity, and Step 2:

```lean
theorem finitePresentation_ker (S) (C) :
    LinearMap.ker (finitePresentation S C) = contextNullspace S C

theorem finitePresentation_surjective (S) (C) :
    Function.Surjective (finitePresentation S C)
```

- [ ] **Step 6: Build the equivalence with the frozen canonical quotient**

Use `LinearMap.quotKerEquivOfSurjective` on `finitePresentation S C`, then transport the domain quotient along `finitePresentation_ker`:

```lean
noncomputable def canonicalEquivFinitePresentation (S) (C) :
    Canonical S C ≃ₗ[𝕜] Module.Dual 𝕜 (futureObservableSpan S C)
```

- [ ] **Step 7: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Identify QCK quotient with finite dual presentation"
```

---

### Task 4: Derive finrank minimality and operation-defect diagnostics

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Consumes: `canonicalEquivFinitePresentation`, Core universal property and `KernelStable`.
- Produces: finrank equalities/lower bounds and `operationDefect`.

- [ ] **Step 1: Add RED checks**

```lean
#check QCK.canonical_finrank_eq_futureObservableSpan
#check QCK.sufficient_rank_ge_canonical
#check QCK.stackedOperationMap
#check QCK.operationDefect
#check QCK.operationDefect_eq_zero_iff
#check QCK.operationDefect_positive_witness
```

- [ ] **Step 2: Prove the dimension identity**

Use the equivalence from Task 3 and `Subspace.dual_finrank_eq`:

```lean
theorem canonical_finrank_eq_futureObservableSpan (S) (C) :
    Module.finrank 𝕜 (Canonical S C) =
      Module.finrank 𝕜 (futureObservableSpan S C)
```

- [ ] **Step 3: Prove sufficient representations have at least canonical rank**

Target:

```lean
theorem sufficient_rank_ge_canonical
    {R : Type r} [AddCommGroup R] [Module 𝕜 R] [FiniteDimensional 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y)
    (q : V →ₗ[𝕜] R) (hq : Sufficient S C q) :
    Module.finrank 𝕜 (Canonical S C) ≤
      Module.finrank 𝕜 (LinearMap.range q)
```

Apply Core `canonicalFactor_surjective` and finite-dimensional `LinearMap.finrank_le_of_surjective` to the factor from `range q` onto the canonical quotient.

- [ ] **Step 4: Define the stacked map and defect**

```lean
def stackedOperationMap
    (O : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) :
    V →ₗ[𝕜] R × R :=
  LinearMap.prod O (O.comp Aop)

def operationDefect
    (O : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) : ℕ :=
  Module.finrank 𝕜 (LinearMap.range (stackedOperationMap O Aop)) -
    Module.finrank 𝕜 (LinearMap.range O)
```

- [ ] **Step 5: Prove defect zero iff kernel stability**

Use rank-nullity for `O` and `stackedOperationMap O Aop`; prove

```lean
LinearMap.ker (stackedOperationMap O Aop) =
  LinearMap.ker O ⊓ LinearMap.ker (O.comp Aop)
```

then prove:

```lean
theorem operationDefect_eq_zero_iff
    [FiniteDimensional 𝕜 R]
    (O : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) :
    operationDefect O Aop = 0 ↔ KernelStable O Aop
```

- [ ] **Step 6: Connect positive defect to Core's witness**

```lean
theorem operationDefect_positive_witness
    [FiniteDimensional 𝕜 R]
    (O : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V)
    (h : 0 < operationDefect O Aop) :
    ∃ v : V, O v = 0 ∧ O (Aop v) ≠ 0
```

Obtain `¬ KernelStable O Aop` from Step 5 and invoke Core `operation_defect_witness`.

- [ ] **Step 7: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Derive QCK rank and operation defect diagnostics"
```

---

### Task 5: Formalize snapshot optionality and an attained minimal reserve

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Produces: `snapshotSafe`, quotient reserve dimension, necessity, and a concrete reserve map attaining the bound.

- [ ] **Step 1: Define snapshot-safe forgetting**

For a finite portfolio indexed by `ι`:

```lean
def snapshotSafe
    {ι : Type*} [Finite ι]
    (N0 : Submodule 𝕜 V) (N : ι → Submodule 𝕜 V) : Submodule 𝕜 V :=
  N0 ⊓ ⨅ i, N i
```

Prove `snapshotSafe N0 N ≤ N0`.

- [ ] **Step 2: Define the relative forgotten subspace and reserve dimension**

```lean
def snapshotSafeInActive
    {ι : Type*} [Finite ι]
    (N0 : Submodule 𝕜 V) (N : ι → Submodule 𝕜 V) : Submodule 𝕜 N0 :=
  (snapshotSafe N0 N).comap N0.subtype

def snapshotReserveFinrank
    {ι : Type*} [Finite ι]
    (N0 : Submodule 𝕜 V) (N : ι → Submodule 𝕜 V) : ℕ :=
  Module.finrank 𝕜 (N0 ⧸ snapshotSafeInActive N0 N)
```

Prove with `Submodule.finrank_quotient_add_finrank`:

```lean
theorem snapshotReserveFinrank_eq_sub (N0) (N) :
    snapshotReserveFinrank N0 N =
      Module.finrank 𝕜 N0 - Module.finrank 𝕜 (snapshotSafe N0 N)
```

- [ ] **Step 3: Prove the lower bound for any supplementary record**

State necessity kernel-first. If `O0 : V →ₗ R0`, `H : V →ₗ RH`, `ker O0 = N0`, and

```lean
LinearMap.ker (LinearMap.prod O0 H) ≤ snapshotSafe N0 N
```

then prove:

```lean
snapshotReserveFinrank N0 N ≤ Module.finrank 𝕜 (LinearMap.range H)
```

Use rank-nullity on `O0`, `H`, and the product map; the product-kernel condition says the supplementary record splits every active equivalence class that the future portfolio requires.

- [ ] **Step 4: Construct a reserve map attaining the quotient dimension**

Let `NF := snapshotSafe N0 N`. Choose a complement of `N0` in `V` using `Submodule.exists_isCompl`. Use `LinearMap.linearProjOfIsCompl` to project `V` onto `N0`, then quotient `N0` by `NF.comap N0.subtype`:

```lean
noncomputable def snapshotReserveMap
    {ι : Type*} [Finite ι]
    (N0 : Submodule 𝕜 V) (N : ι → Submodule 𝕜 V) :
    V →ₗ[𝕜] (N0 ⧸ snapshotSafeInActive N0 N)
```

Prove projection is identity on `N0`, then prove the attained combined-kernel theorem for any active map with `ker O0 = N0`:

```lean
theorem ker_prod_active_snapshotReserveMap
    (O0 : V →ₗ[𝕜] R0) (hO0 : LinearMap.ker O0 = N0) :
    LinearMap.ker (LinearMap.prod O0 (snapshotReserveMap N0 N)) =
      snapshotSafe N0 N
```

The reserve codomain has exactly `snapshotReserveFinrank N0 N` dimensions by definition, so necessity and achievability match.

- [ ] **Step 5: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Formalize QCK snapshot optionality"
```

---

### Task 6: Formalize maintained optionality and its universal property

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Consumes: Core `wordMap`; Task 5 snapshot-safe subspace.
- Produces: greatest invariant safely-forgettable subspace and maintained reserve comparison.

- [ ] **Step 1: Define maintained-safe forgetting**

```lean
def maintainedSafe
    (S : A → V →ₗ[𝕜] V) (NF : Submodule 𝕜 V) : Submodule 𝕜 V :=
  ⨅ w : List A, NF.comap (wordMap S w)
```

- [ ] **Step 2: Prove the three universal-property clauses**

```lean
theorem maintainedSafe_le (S) (NF) : maintainedSafe S NF ≤ NF

theorem maintainedSafe_invariant (S) (NF) (a : A) :
    maintainedSafe S NF ≤ (maintainedSafe S NF).comap (S a)

theorem le_maintainedSafe
    (S) (NF) (W : Submodule 𝕜 V)
    (hWF : W ≤ NF)
    (hInv : ∀ a, W ≤ W.comap (S a)) :
    W ≤ maintainedSafe S NF
```

Package the three as:

```lean
theorem maintainedSafe_greatest (S) (NF) :
    IsGreatest
      {W : Submodule 𝕜 V | W ≤ NF ∧ ∀ a, W ≤ W.comap (S a)}
      (maintainedSafe S NF)
```

- [ ] **Step 3: Define maintained reserve dimension relative to the active kernel**

Given `hM0 : maintainedSafe S NF ≤ N0`, define the relative submodule in `N0` and:

```lean
def maintainedReserveFinrank
    (N0 NF : Submodule 𝕜 V) (S : A → V →ₗ[𝕜] V) : ℕ :=
  Module.finrank 𝕜
    (N0 ⧸ (maintainedSafe S NF).comap N0.subtype)
```

The public theorem may carry hypotheses `NF ≤ N0` and active-kernel invariance rather than storing proofs inside the definition.

- [ ] **Step 4: Prove snapshot reserve is no larger**

For `NF ≤ N0`:

```lean
theorem snapshotReserve_le_maintainedReserve
    (hFN : NF ≤ N0) :
    Module.finrank 𝕜 (N0 ⧸ NF.comap N0.subtype) ≤
      maintainedReserveFinrank N0 NF S
```

Use `maintainedSafe_le` plus finrank monotonicity/rank-nullity.

- [ ] **Step 5: Prove equality under waiting invariance**

If `∀ a, NF ≤ NF.comap (S a)`, use `maintainedSafe_greatest` to prove `maintainedSafe S NF = NF`, then:

```lean
theorem maintainedReserve_eq_snapshot_of_invariant
    (hInv : ∀ a, NF ≤ NF.comap (S a)) :
    maintainedReserveFinrank N0 NF S =
      Module.finrank 𝕜 (N0 ⧸ NF.comap N0.subtype)
```

- [ ] **Step 6: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Formalize QCK maintained optionality"
```

---

### Task 7: Certify reserve independence from active execution

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Consumes: Core `descendedOperation` and `operation_descends_iff`.
- Produces: invariant first-component theorem and explicit block-triangular decomposition.

- [ ] **Step 1: Define a combined active/reserve map**

```lean
def combinedMap
    (O0 : V →ₗ[𝕜] R0) (H : V →ₗ[𝕜] RH) : V →ₗ[𝕜] R0 × RH :=
  LinearMap.prod O0 H
```

- [ ] **Step 2: Prove the first component of descended combined dynamics is active-only**

Assume `O0` and `combinedMap O0 H` are surjective and both kernels are stable under `Aop`. Let `T` and `M` be Core `descendedOperation` maps. Prove:

```lean
theorem combined_first_component_independent
    (O0 : V →ₗ[𝕜] R0) (H : V →ₗ[𝕜] RH)
    (hO0 : Function.Surjective O0)
    (hQ : Function.Surjective (combinedMap O0 H))
    (h0 : KernelStable O0 Aop)
    (hQstable : KernelStable (combinedMap O0 H) Aop) :
    (LinearMap.fst 𝕜 R0 RH).comp
        (descendedOperation (combinedMap O0 H) hQ Aop hQstable) =
      (descendedOperation O0 hO0 Aop h0).comp
        (LinearMap.fst 𝕜 R0 RH)
```

Prove by precomposing both sides with the surjective combined map and using both Core intertwining theorems.

- [ ] **Step 3: Derive a block decomposition**

For `M : R0 × RH →ₗ R0 × RH`, define:

```lean
def blockLowerLeft (M) : R0 →ₗ[𝕜] RH :=
  (LinearMap.snd 𝕜 R0 RH).comp (M.comp (LinearMap.inl 𝕜 R0 RH))

def blockLowerRight (M) : RH →ₗ[𝕜] RH :=
  (LinearMap.snd 𝕜 R0 RH).comp (M.comp (LinearMap.inr 𝕜 R0 RH))
```

Use `combined_first_component_independent` to prove pointwise:

```lean
M (a, r) =
  (T a, blockLowerLeft M a + blockLowerRight M r)
```

for the descended combined map `M`. This is the Lean statement corresponding to the block matrix `[T 0; B D]`.

- [ ] **Step 4: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Certify QCK active reserve block dynamics"
```

---

### Task 8: Prove fixed-vocabulary reserve submodularity

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Produces: option-span rank, monotonicity, submodularity, and diminishing marginal dimension.

- [ ] **Step 1: Define finite option span and rank**

For `[DecidableEq ι]`:

```lean
def optionSpan
    (L0 : Submodule 𝕜 W) (L : ι → Submodule 𝕜 W) (s : Finset ι) :
    Submodule 𝕜 W :=
  L0 ⊔ s.sup L

def reserveRank
    (L0 : Submodule 𝕜 W) (L : ι → Submodule 𝕜 W) (s : Finset ι) : ℕ :=
  Module.finrank 𝕜 (optionSpan L0 L s) - Module.finrank 𝕜 L0
```

- [ ] **Step 2: Prove normalization and monotonicity**

```lean
theorem reserveRank_empty (L0) (L) : reserveRank L0 L ∅ = 0

theorem reserveRank_mono
    (hst : s ⊆ t) : reserveRank L0 L s ≤ reserveRank L0 L t
```

- [ ] **Step 3: Prove submodularity**

Use `Submodule.finrank_sup_add_finrank_inf_eq` on
`optionSpan L0 L s` and `optionSpan L0 L t`.

Prove the lattice facts:

```lean
optionSpan L0 L (s ∪ t) = optionSpan L0 L s ⊔ optionSpan L0 L t

optionSpan L0 L (s ∩ t) ≤ optionSpan L0 L s ⊓ optionSpan L0 L t
```

then derive:

```lean
theorem reserveRank_submodular (L0) (L) (s t : Finset ι) :
    reserveRank L0 L (s ∪ t) + reserveRank L0 L (s ∩ t) ≤
      reserveRank L0 L s + reserveRank L0 L t
```

- [ ] **Step 4: Prove diminishing marginal rank**

Define:

```lean
def reserveMarginal (L0) (L) (s : Finset ι) (j : ι) : ℕ :=
  reserveRank L0 L (insert j s) - reserveRank L0 L s
```

Derive from submodularity:

```lean
theorem reserveMarginal_antitone
    (hst : s ⊆ t) :
    reserveMarginal L0 L t j ≤ reserveMarginal L0 L s j
```

- [ ] **Step 5: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Prove QCK shared optionality submodularity"
```

---

### Task 9: Formalize the interacting-capability non-submodularity counterexample

**Files:**
- Modify: `qcklean/QCKFiniteLinear.lean`
- Modify: `qcklean/QCKFiniteLinearTest.lean`

**Interfaces:**
- Produces: an explicit exact three-coordinate negative theorem.

- [ ] **Step 1: Define the concrete source and operations over `ℚ`**

Use `TriState := Fin 3 → ℚ` and coordinate observation `obs0 := LinearMap.proj 0`.

Define endomorphisms pointwise:

```lean
def swap01 : TriState →ₗ[ℚ] TriState := {
  toFun := fun x i => if i = 0 then x 1 else if i = 1 then x 0 else x 2
  map_add' := by intro x y; ext i; fin_cases i <;> simp
  map_smul' := by intro c x; ext i; fin_cases i <;> simp
}

def swap12 : TriState →ₗ[ℚ] TriState := {
  toFun := fun x i => if i = 1 then x 2 else if i = 2 then x 1 else x 0
  map_add' := by intro x y; ext i; fin_cases i <;> simp
  map_smul' := by intro c x; ext i; fin_cases i <;> simp
}
```

- [ ] **Step 2: Define four action vocabularies**

Use `PEmpty` for no actions, `Unit` for a single action, and `Bool` for both actions:

```lean
def noActions : PEmpty → TriState →ₗ[ℚ] TriState := PEmpty.elim
def onlyU : Unit → TriState →ₗ[ℚ] TriState := fun _ => swap01
def onlyV : Unit → TriState →ₗ[ℚ] TriState := fun _ => swap12
def bothUV : Bool → TriState →ₗ[ℚ] TriState
  | false => swap01
  | true => swap12
```

- [ ] **Step 3: Prove the four context-nullspace descriptions**

Prove by extensionality and coordinate simplification:

```lean
contextNullspace noActions obs0 = LinearMap.ker obs0

contextNullspace onlyU obs0 =
  LinearMap.ker obs0 ⊓ LinearMap.ker (LinearMap.proj 1)

contextNullspace onlyV obs0 = LinearMap.ker obs0

contextNullspace bothUV obs0 = ⊥
```

For the final equality use words `[]`, `[false]`, and `[true, false]` to expose coordinates 0, 1, and 2 respectively.

- [ ] **Step 4: Compute canonical dimensions**

Use `Submodule.finrank_quotient_add_finrank` plus the explicit kernels to prove:

```lean
Module.finrank ℚ (Canonical noActions obs0) = 1
Module.finrank ℚ (Canonical onlyU obs0) = 2
Module.finrank ℚ (Canonical onlyV obs0) = 1
Module.finrank ℚ (Canonical bothUV obs0) = 3
```

Define additional-dimension costs by subtracting the baseline 1:

```lean
def gNone : ℕ := Module.finrank ℚ (Canonical noActions obs0) - 1
def gU : ℕ := Module.finrank ℚ (Canonical onlyU obs0) - 1
def gV : ℕ := Module.finrank ℚ (Canonical onlyV obs0) - 1
def gUV : ℕ := Module.finrank ℚ (Canonical bothUV obs0) - 1
```

- [ ] **Step 5: Prove the negative theorem**

```lean
theorem interactingCapability_not_submodular :
    gU + gV < gUV + gNone := by
  norm_num [gU, gV, gUV, gNone,
    canonical_finrank_noActions, canonical_finrank_onlyU,
    canonical_finrank_onlyV, canonical_finrank_bothUV]
```

- [ ] **Step 6: Run and commit**

```bash
cd qcklean && lake build QCK && lake env lean QCKFiniteLinearTest.lean
git add QCKFiniteLinear.lean QCKFiniteLinearTest.lean
git commit -m "Add QCK interacting capability counterexample"
```

---

### Task 10: Final qualification and freeze manifest

**Files:**
- Modify: `.github/workflows/qck-finite-linear-v1.yml`
- Create: `QCK_FINITE_LINEAR_V1.md`

**Interfaces:**
- Produces: authoritative qualified theorem surface and explicit QCK.API frontier.

- [ ] **Step 1: Expand the interface test to every public v1 theorem**

The final `QCKFiniteLinearTest.lean` must `#check` every exported v1 declaration, including the positive submodularity and negative interacting-capability theorem.

- [ ] **Step 2: Add direct-source compilation and axiom audit to CI**

Compile every repository-owned `QCK*.lean` individually. Create a temporary audit file importing `QCKFiniteLinear` and print axioms for at least:

```lean
#print axioms QCK.futureObservableSpan_eq_dualAnnihilator
#print axioms QCK.finitePresentation_ker
#print axioms QCK.sufficient_rank_ge_canonical
#print axioms QCK.operationDefect_eq_zero_iff
#print axioms QCK.maintainedSafe_greatest
#print axioms QCK.reserveRank_submodular
#print axioms QCK.interactingCapability_not_submodular
```

- [ ] **Step 3: Run the complete workflow and require GREEN**

Required green stages: frozen-Core hash; pinned dependencies; placeholder/local-axiom scan; Lake build; full interface; per-source compilation; axiom audit.

- [ ] **Step 4: Create the freeze manifest**

`QCK_FINITE_LINEAR_V1.md` must record:

- branch and qualified commit;
- frozen Core blob;
- Lean and Mathlib pins;
- authoritative workflow run/job;
- public theorem surface;
- standard Lean axioms reported by the audit;
- claim boundary;
- remaining `QCK.API` frontier.

- [ ] **Step 5: Re-run qualification with the manifest inside the workflow trigger**

Do not call FiniteLinear frozen until the manifest commit itself has a fresh green qualification run.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/qck-finite-linear-v1.yml QCK_FINITE_LINEAR_V1.md qcklean/QCKFiniteLinearTest.lean
git commit -m "Freeze qualified QCK FiniteLinear v1"
```

---

## Self-Review Checklist

- Every section of the approved spec maps to a task above.
- Core integrity is checked before every FiniteLinear qualification.
- The executable presentation is derived from the semantic quotient via the finite future-observable pairing; no coordinate choice becomes semantic authority.
- Snapshot reserve includes both necessity and an attained linear construction.
- Maintained reserve has its greatest-invariant-subspace universal property.
- Active/reserve block structure is expressed as an exact first-component independence theorem plus lower-block decomposition.
- Fixed-vocabulary submodularity and capability-vocabulary non-submodularity are both formal theorems.
- No PSD/CP/API/Collatz scope has entered the plan.
- No implementation may change `QCKCore.lean`.