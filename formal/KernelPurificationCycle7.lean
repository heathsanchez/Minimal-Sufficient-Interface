import KernelPurificationCycle6

namespace KernelPurificationCycle7

open KernelPurificationCycle5
open KernelPurificationCycle6

universe u

/-- The canonical residual of two consequence profiles is not an arbitrarily
    selected witness coordinate, but the full support on which they disagree. -/
def MismatchSupport {I : Type u} (g : GlobalSupportMismatch I) (i : I) : Prop :=
  g.current i ≠ g.required i

/-- The negative orientation of the canonical mismatch support. -/
def RemovalSupport {I : Type u} (g : GlobalSupportMismatch I) (i : I) : Prop :=
  g.current i = true ∧ g.required i = false

/-- The positive orientation of the canonical mismatch support. -/
def GenerationSupport {I : Type u} (g : GlobalSupportMismatch I) (i : I) : Prop :=
  g.current i = false ∧ g.required i = true

/-- A genuine global mismatch makes the canonical support nonempty. -/
theorem mismatch_support_nonempty {I : Type u} (g : GlobalSupportMismatch I) :
    ∃ i : I, MismatchSupport g i := by
  exact global_mismatch_localizes g

/-- Outside the canonical support the current profile already satisfies the
    verified required profile. -/
theorem outside_mismatch_support_already_agrees
    {I : Type u} (g : GlobalSupportMismatch I) (i : I)
    (h : ¬ MismatchSupport g i) :
    g.current i = g.required i := by
  classical
  by_cases heq : g.current i = g.required i
  · exact heq
  · exact False.elim (h heq)

/-- Every coordinate in the canonical support determines its own orientation;
    no semantic failure-mode tag or witness-selection rule is required. -/
theorem mismatch_support_partitions_by_polarity
    {I : Type u} (g : GlobalSupportMismatch I) (i : I)
    (h : MismatchSupport g i) :
    RemovalSupport g i ∨ GenerationSupport g i := by
  exact mismatch_determines_polarity (localizedDefect g i h)

/-- Conversely, either oriented support is necessarily a genuine mismatch. -/
theorem oriented_support_is_mismatch
    {I : Type u} (g : GlobalSupportMismatch I) (i : I) :
    RemovalSupport g i ∨ GenerationSupport g i → MismatchSupport g i := by
  intro hpol
  cases hpol with
  | inl hrem =>
      intro heq
      have htf : true = false := hrem.1.symm.trans (heq.trans hrem.2)
      exact Bool.noConfusion htf
  | inr hgen =>
      intro heq
      have hft : false = true := hgen.1.symm.trans (heq.trans hgen.2)
      exact Bool.noConfusion hft

/-- The full residual support is exactly the disjoint union of inferred removal
    and generation sites. -/
theorem mismatch_support_iff_oriented_support
    {I : Type u} (g : GlobalSupportMismatch I) (i : I) :
    MismatchSupport g i ↔ RemovalSupport g i ∨ GenerationSupport g i := by
  constructor
  · exact mismatch_support_partitions_by_polarity g i
  · exact oriented_support_is_mismatch g i

/-- The two orientations cannot overlap at a coordinate. -/
theorem support_polarities_disjoint
    {I : Type u} (g : GlobalSupportMismatch I) (i : I) :
    ¬ (RemovalSupport g i ∧ GenerationSupport g i) := by
  intro h
  have htf : true = false := h.1.1.symm.trans h.2.1
  exact Bool.noConfusion htf

/-- Exact support ablation: if the full mismatch support is empty, the two
    profiles are extensionally equal, so no global verifier mismatch remains. -/
theorem empty_mismatch_support_forces_profile_agreement
    {I : Type u} (current required : I → Bool)
    (hempty : ∀ i : I, ¬ (current i ≠ required i)) :
    current = required := by
  funext i
  classical
  by_cases h : current i = required i
  · exact h
  · exact False.elim (hempty i h)

/-- Cycle-7 decision: arbitrary single-witness selection is not part of the
    purified kernel.  The verifier profiles canonically determine the entire
    residual support; its orientation is derived pointwise, and outside that
    support nothing requires repair. -/
theorem full_mismatch_support_replaces_witness_selection
    {I : Type u} (g : GlobalSupportMismatch I) :
    (∃ i : I, MismatchSupport g i) ∧
    (∀ i : I,
      MismatchSupport g i ↔ RemovalSupport g i ∨ GenerationSupport g i) ∧
    (∀ i : I, ¬ MismatchSupport g i → g.current i = g.required i) ∧
    (∀ i : I, ¬ (RemovalSupport g i ∧ GenerationSupport g i)) := by
  constructor
  · exact mismatch_support_nonempty g
  constructor
  · intro i
    exact mismatch_support_iff_oriented_support g i
  constructor
  · intro i h
    exact outside_mismatch_support_already_agrees g i h
  · intro i
    exact support_polarities_disjoint g i

#check mismatch_support_nonempty
#check outside_mismatch_support_already_agrees
#check mismatch_support_partitions_by_polarity
#check mismatch_support_iff_oriented_support
#check support_polarities_disjoint
#check empty_mismatch_support_forces_profile_agreement
#check full_mismatch_support_replaces_witness_selection

end KernelPurificationCycle7
