import Mathlib.LinearAlgebra.Isomorphisms
import Mathlib.LinearAlgebra.Quotient.Basic

/-!
# QCK Core v1

Finite context-stable certified substitution for linear operational systems.

The canonical object is the quotient by exactly those differences that no
admitted finite continuation can expose.  The semantic core is basis-free:
matrices, rank formulae, costs, PSD structure, and approximate equivalence live
outside this file.
-/

namespace QCK

universe u v y r

variable {𝕜 : Type u} [Field 𝕜]
variable {V : Type v} [AddCommGroup V] [Module 𝕜 V]
variable {Y : Type y} [AddCommGroup Y] [Module 𝕜 Y]
variable {A : Type*}

/-- Composite action associated to a finite word. Letters are executed left-to-right. -/
def wordMap (S : A → V →ₗ[𝕜] V) : List A → V →ₗ[𝕜] V
  | [] => LinearMap.id
  | a :: w => (wordMap S w).comp (S a)

@[simp]
theorem wordMap_nil (S : A → V →ₗ[𝕜] V) : wordMap S [] = LinearMap.id := rfl

@[simp]
theorem wordMap_cons (S : A → V →ₗ[𝕜] V) (a : A) (w : List A) :
    wordMap S (a :: w) = (wordMap S w).comp (S a) := rfl

/-- Concatenating words corresponds to composing their action maps. -/
theorem wordMap_append (S : A → V →ₗ[𝕜] V) (u v : List A) :
    wordMap S (u ++ v) = (wordMap S v).comp (wordMap S u) := by
  induction u with
  | nil => simp [wordMap]
  | cons a u ih =>
      simp only [List.cons_append, wordMap_cons, ih]
      rfl

/-- Differences invisible to every admitted finite continuation. -/
def contextNullspace (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) : Submodule 𝕜 V :=
  ⨅ w : List A, LinearMap.ker (C.comp (wordMap S w))

/-- Semantic characterization of membership in the context-stable nullspace. -/
theorem mem_contextNullspace_iff (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (x : V) :
    x ∈ contextNullspace S C ↔ ∀ w : List A, C (wordMap S w x) = 0 := by
  simp [contextNullspace, LinearMap.mem_ker]

/-- The canonical nullspace is invariant under each admitted generator. -/
theorem contextNullspace_invariant (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (a : A) :
    contextNullspace S C ≤ (contextNullspace S C).comap (S a) := by
  intro x hx
  change S a x ∈ contextNullspace S C
  rw [mem_contextNullspace_iff] at hx ⊢
  intro w
  simpa [wordMap] using hx (a :: w)

/-- The canonical context-stable replacement space. -/
abbrev Canonical (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :=
  V ⧸ contextNullspace S C

/-- Canonical quotient map from source state to replacement state. -/
def canonicalMap (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    V →ₗ[𝕜] Canonical S C :=
  (contextNullspace S C).mkQ

/-- Each admitted source generator descends to the canonical quotient. -/
def reducedAction (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (a : A) :
    Canonical S C →ₗ[𝕜] Canonical S C :=
  (contextNullspace S C).mapQ (contextNullspace S C) (S a)
    (contextNullspace_invariant S C a)

@[simp]
theorem reducedAction_canonicalMap
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (a : A) (x : V) :
    reducedAction S C a (canonicalMap S C x) = canonicalMap S C (S a x) := rfl

/-- Immediate observation vanishes on the canonical nullspace. -/
theorem contextNullspace_le_ker_observation
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    contextNullspace S C ≤ LinearMap.ker C := by
  intro x hx
  have h := (mem_contextNullspace_iff S C x).1 hx []
  simpa [wordMap] using h

/-- Observation induced on the canonical quotient. -/
def reducedObservation (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) :
    Canonical S C →ₗ[𝕜] Y :=
  (contextNullspace S C).liftQ C (contextNullspace_le_ker_observation S C)

@[simp]
theorem reducedObservation_canonicalMap
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (x : V) :
    reducedObservation S C (canonicalMap S C x) = C x := rfl

/-- The canonical quotient intertwines every finite source word with the reduced word. -/
theorem canonicalMap_wordMap
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (w : List A) (x : V) :
    canonicalMap S C (wordMap S w x) =
      wordMap (reducedAction S C) w (canonicalMap S C x) := by
  induction w generalizing x with
  | nil => rfl
  | cons a w ih =>
      simp only [wordMap_cons, LinearMap.comp_apply]
      rw [ih]
      rfl

/-- Finite generator equations certify every protected finite continuation observation. -/
theorem allWordSubstitution
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (w : List A) (x : V) :
    reducedObservation S C
        (wordMap (reducedAction S C) w (canonicalMap S C x)) =
      C (wordMap S w x) := by
  rw [← canonicalMap_wordMap S C w x]
  rfl

/-- A linear representation is sufficient when every protected continuation observation factors through it. -/
def Sufficient
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (q : V →ₗ[𝕜] R) : Prop :=
  ∀ w : List A, ∃ D : R →ₗ[𝕜] Y,
    C.comp (wordMap S w) = D.comp q

/-- Every sufficient representation may identify only differences already invisible to all protected futures. -/
theorem ker_le_contextNullspace
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (q : V →ₗ[𝕜] R)
    (hq : Sufficient S C q) :
    LinearMap.ker q ≤ contextNullspace S C := by
  intro x hx
  rw [mem_contextNullspace_iff S C x]
  intro w
  obtain ⟨D, hD⟩ := hq w
  have hpoint := congrArg (fun f : V →ₗ[𝕜] Y => f x) hD
  have hqx : q x = 0 := by simpa [LinearMap.mem_ker] using hx
  simpa [LinearMap.comp_apply, hqx] using hpoint

/-- Universal factor from the realized image of any sufficient representation onto the canonical quotient. -/
noncomputable def canonicalFactor
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (q : V →ₗ[𝕜] R)
    (hq : Sufficient S C q) :
    LinearMap.range q →ₗ[𝕜] Canonical S C :=
  (Submodule.factor (ker_le_contextNullspace S C q hq)).comp
    q.quotKerEquivRange.symm.toLinearMap

@[simp]
theorem canonicalFactor_rangeRestrict
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (q : V →ₗ[𝕜] R)
    (hq : Sufficient S C q) (x : V) :
    canonicalFactor S C q hq (q.rangeRestrict x) = canonicalMap S C x := by
  change (Submodule.factor (ker_le_contextNullspace S C q hq))
      (q.quotKerEquivRange.symm (q.rangeRestrict x)) =
    (contextNullspace S C).mkQ x
  have hr : q.rangeRestrict x =
      ⟨q x, LinearMap.mem_range_self q x⟩ := rfl
  rw [hr, LinearMap.quotKerEquivRange_symm_apply_image]
  exact Submodule.factor_mk (ker_le_contextNullspace S C q hq) x

/-- The universal factor is surjective: every sufficient realized representation factors onto the canonical one. -/
theorem canonicalFactor_surjective
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y) (q : V →ₗ[𝕜] R)
    (hq : Sufficient S C q) :
    Function.Surjective (canonicalFactor S C q hq) := by
  intro z
  obtain ⟨x, rfl⟩ := Submodule.Quotient.mk_surjective (contextNullspace S C) z
  exact ⟨q.rangeRestrict x, canonicalFactor_rangeRestrict S C q hq x⟩

/-- A generic certified substitution over a shared generator alphabet. -/
structure Certificate
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y)
    (q : V →ₗ[𝕜] R) (T : A → R →ₗ[𝕜] R) (D : R →ₗ[𝕜] Y) : Prop where
  action : ∀ a, (T a).comp q = q.comp (S a)
  observe : D.comp q = C

/-- Certified substitutions compose without reopening the source implementation. -/
theorem Certificate.comp
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    {U : Type*} [AddCommGroup U] [Module 𝕜 U]
    (S : A → V →ₗ[𝕜] V) (C : V →ₗ[𝕜] Y)
    (q₁ : V →ₗ[𝕜] R) (T : A → R →ₗ[𝕜] R) (D : R →ₗ[𝕜] Y)
    (q₂ : R →ₗ[𝕜] U) (Uact : A → U →ₗ[𝕜] U) (E : U →ₗ[𝕜] Y)
    (h₁ : Certificate S C q₁ T D)
    (h₂ : Certificate T D q₂ Uact E) :
    Certificate S C (q₂.comp q₁) Uact E := by
  constructor
  · intro a
    ext x
    have h₂x : Uact a (q₂ (q₁ x)) = q₂ (T a (q₁ x)) := by
      exact congrArg (fun f : R →ₗ[𝕜] U => f (q₁ x)) (h₂.action a)
    have h₁x : T a (q₁ x) = q₁ (S a x) := by
      exact congrArg (fun f : V →ₗ[𝕜] R => f x) (h₁.action a)
    calc
      Uact a ((q₂.comp q₁) x) = Uact a (q₂ (q₁ x)) := rfl
      _ = q₂ (T a (q₁ x)) := h₂x
      _ = q₂ (q₁ (S a x)) := by rw [h₁x]
      _ = (q₂.comp q₁) (S a x) := rfl
  · ext x
    have h₂x : E (q₂ (q₁ x)) = D (q₁ x) := by
      exact congrArg (fun f : R →ₗ[𝕜] Y => f (q₁ x)) h₂.observe
    have h₁x : D (q₁ x) = C x := by
      exact congrArg (fun f : V →ₗ[𝕜] Y => f x) h₁.observe
    calc
      E ((q₂.comp q₁) x) = E (q₂ (q₁ x)) := rfl
      _ = D (q₁ x) := h₂x
      _ = C x := h₁x

/-- Kernel stability is the primary semantic condition for a proposed operation to descend. -/
def KernelStable
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) : Prop :=
  LinearMap.ker q ≤ (LinearMap.ker q).comap Aop

/-- The reduced operation induced by a kernel-stable source operation and a surjective presentation. -/
noncomputable def descendedOperation
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (q : V →ₗ[𝕜] R) (hq : Function.Surjective q)
    (Aop : V →ₗ[𝕜] V) (hstable : KernelStable q Aop) : R →ₗ[𝕜] R :=
  let e := q.quotKerEquivOfSurjective hq
  e.toLinearMap.comp
    (((LinearMap.ker q).mapQ (LinearMap.ker q) Aop hstable).comp e.symm.toLinearMap)

@[simp]
theorem descendedOperation_intertwines
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (q : V →ₗ[𝕜] R) (hq : Function.Surjective q)
    (Aop : V →ₗ[𝕜] V) (hstable : KernelStable q Aop) :
    (descendedOperation q hq Aop hstable).comp q = q.comp Aop := by
  ext x
  simp only [descendedOperation, LinearMap.comp_apply]
  rw [LinearMap.quotKerEquivOfSurjective_symm_apply]
  rw [Submodule.mapQ_apply]
  rw [LinearMap.quotKerEquivOfSurjective_apply_mk]

/-- A source operation descends uniquely through a surjective representation exactly when its kernel is stable. -/
theorem operation_descends_iff
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (q : V →ₗ[𝕜] R) (hq : Function.Surjective q) (Aop : V →ₗ[𝕜] V) :
    KernelStable q Aop ↔
      ∃! T : R →ₗ[𝕜] R, T.comp q = q.comp Aop := by
  constructor
  · intro hstable
    refine ⟨descendedOperation q hq Aop hstable,
      descendedOperation_intertwines q hq Aop hstable, ?_⟩
    intro T hT
    apply LinearMap.ext
    intro y
    obtain ⟨x, rfl⟩ := hq y
    have hTx := congrArg (fun f : V →ₗ[𝕜] R => f x) hT
    have hDx := congrArg (fun f : V →ₗ[𝕜] R => f x)
      (descendedOperation_intertwines q hq Aop hstable)
    exact hTx.trans hDx.symm
  · rintro ⟨T, hT, _⟩
    intro x hx
    have hpoint := congrArg (fun f : V →ₗ[𝕜] R => f x) hT
    have hqx : q x = 0 := by simpa [LinearMap.mem_ker] using hx
    have hzero : q (Aop x) = 0 := by
      simpa [LinearMap.comp_apply, hqx] using hpoint.symm
    simpa [LinearMap.mem_ker] using hzero

/-- Failure of kernel stability supplies an erased source difference exposed by the proposed operation. -/
theorem operation_defect_witness
    {R : Type r} [AddCommGroup R] [Module 𝕜 R]
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V)
    (h : ¬ KernelStable q Aop) :
    ∃ v : V, q v = 0 ∧ q (Aop v) ≠ 0 := by
  by_contra hn
  apply h
  intro v hv
  change q (Aop v) = 0
  by_contra hne
  apply hn
  exact ⟨v, (by simpa [LinearMap.mem_ker] using hv), hne⟩

end QCK
