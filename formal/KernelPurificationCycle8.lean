import KernelPurificationCycle7

namespace KernelPurificationCycle8

open KernelPurificationCycle6
open KernelPurificationCycle7

universe u

/-- The verifier need not return Boolean-valued profiles.  At the purified
    level it is enough to expose, at every coordinate, the propositions that
    are currently supported and consequentially required. -/
structure LogicalProfileMismatch (I : Type u) where
  current : I → Prop
  required : I → Prop
  mismatch : ¬ (∀ i : I, current i ↔ required i)

/-- The representation-free residual support is logical disagreement. -/
def LogicalMismatchSupport {I : Type u} (g : LogicalProfileMismatch I) (i : I) : Prop :=
  ¬ (g.current i ↔ g.required i)

def LogicalRemovalSupport {I : Type u} (g : LogicalProfileMismatch I) (i : I) : Prop :=
  g.current i ∧ ¬ g.required i

def LogicalGenerationSupport {I : Type u} (g : LogicalProfileMismatch I) (i : I) : Prop :=
  ¬ g.current i ∧ g.required i

/-- Global logical disagreement localizes without a supplied coordinate. -/
theorem logical_profile_mismatch_localizes
    {I : Type u} (g : LogicalProfileMismatch I) :
    ∃ i : I, LogicalMismatchSupport g i := by
  classical
  by_cases h : ∃ i : I, LogicalMismatchSupport g i
  · exact h
  · exfalso
    apply g.mismatch
    intro i
    by_cases hi : g.current i ↔ g.required i
    · exact hi
    · exact False.elim (h ⟨i, hi⟩)

/-- Logical mismatch determines the same two repair orientations.  Boolean
    truth values are therefore not needed to infer repair polarity. -/
theorem logical_support_partitions_by_polarity
    {I : Type u} (g : LogicalProfileMismatch I) (i : I)
    (h : LogicalMismatchSupport g i) :
    LogicalRemovalSupport g i ∨ LogicalGenerationSupport g i := by
  classical
  by_cases hc : g.current i
  · by_cases hr : g.required i
    · exact False.elim (h ⟨fun _ => hr, fun _ => hc⟩)
    · exact Or.inl ⟨hc, hr⟩
  · by_cases hr : g.required i
    · exact Or.inr ⟨hc, hr⟩
    · have heq : g.current i ↔ g.required i := by
        constructor
        · intro hcur
          exact False.elim (hc hcur)
        · intro hreq
          exact False.elim (hr hreq)
      exact False.elim (h heq)

/-- Either orientation is genuinely a logical mismatch. -/
theorem logical_oriented_support_is_mismatch
    {I : Type u} (g : LogicalProfileMismatch I) (i : I) :
    LogicalRemovalSupport g i ∨ LogicalGenerationSupport g i →
      LogicalMismatchSupport g i := by
  intro hpol
  cases hpol with
  | inl hrem =>
      intro heq
      exact hrem.2 (heq.mp hrem.1)
  | inr hgen =>
      intro heq
      exact hgen.1 (heq.mpr hgen.2)

/-- The canonical logical residual is exactly its two inferred orientations. -/
theorem logical_mismatch_iff_oriented_support
    {I : Type u} (g : LogicalProfileMismatch I) (i : I) :
    LogicalMismatchSupport g i ↔
      LogicalRemovalSupport g i ∨ LogicalGenerationSupport g i := by
  constructor
  · exact logical_support_partitions_by_polarity g i
  · exact logical_oriented_support_is_mismatch g i

/-- Logical repair orientations remain disjoint. -/
theorem logical_polarities_disjoint
    {I : Type u} (g : LogicalProfileMismatch I) (i : I) :
    ¬ (LogicalRemovalSupport g i ∧ LogicalGenerationSupport g i) := by
  intro h
  exact h.2.1 h.1.1

/-- Outside the residual support the two consequential propositions already
    agree. -/
theorem outside_logical_support_already_agrees
    {I : Type u} (g : LogicalProfileMismatch I) (i : I)
    (h : ¬ LogicalMismatchSupport g i) :
    g.current i ↔ g.required i := by
  classical
  by_cases heq : g.current i ↔ g.required i
  · exact heq
  · exact False.elim (h heq)

/-- Empty logical support is exact closure: current and required consequence
    profiles agree pointwise. -/
theorem empty_logical_support_is_pointwise_closure
    {I : Type u} (current required : I → Prop)
    (hempty : ∀ i : I, ¬ (¬ (current i ↔ required i))) :
    ∀ i : I, current i ↔ required i := by
  intro i
  classical
  by_cases h : current i ↔ required i
  · exact h
  · exact False.elim (hempty i h)

/-- Boolean support disagreement is only a concrete presentation of logical
    support disagreement through the proposition `b = true`. -/
theorem bool_mismatch_is_logical_mismatch (a b : Bool) :
    (a ≠ b) ↔ ¬ ((a = true) ↔ (b = true)) := by
  cases a <;> cases b <;> decide

/-- Cycle-8 decision: the Boolean support alphabet falls off.  The surviving
    object is proposition-valued consequential disagreement, whose full support
    still canonically partitions into remove-vs-generate directions. -/
theorem propositional_consequence_support_is_sufficient
    {I : Type u} (g : LogicalProfileMismatch I) :
    (∃ i : I, LogicalMismatchSupport g i) ∧
    (∀ i : I,
      LogicalMismatchSupport g i ↔
        LogicalRemovalSupport g i ∨ LogicalGenerationSupport g i) ∧
    (∀ i : I, ¬ (LogicalRemovalSupport g i ∧ LogicalGenerationSupport g i)) := by
  constructor
  · exact logical_profile_mismatch_localizes g
  constructor
  · intro i
    exact logical_mismatch_iff_oriented_support g i
  · intro i
    exact logical_polarities_disjoint g i

#check logical_profile_mismatch_localizes
#check logical_support_partitions_by_polarity
#check logical_mismatch_iff_oriented_support
#check logical_polarities_disjoint
#check outside_logical_support_already_agrees
#check empty_logical_support_is_pointwise_closure
#check bool_mismatch_is_logical_mismatch
#check propositional_consequence_support_is_sufficient

end KernelPurificationCycle8
