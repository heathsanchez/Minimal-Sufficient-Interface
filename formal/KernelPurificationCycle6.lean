import KernelPurificationCycle5

namespace KernelPurificationCycle6

open KernelPurificationCycle5

universe u

/-- A verifier may expose only that the current and required consequence
    profiles differ.  No coordinate of disagreement is supplied separately. -/
structure GlobalSupportMismatch (I : Type u) where
  current : I → Bool
  required : I → Bool
  mismatch : current ≠ required

/-- Global profile inequality necessarily localizes to at least one support
    coordinate.  The coordinate is derived from the verifier-visible mismatch,
    not passed to the repair kernel as an external choice. -/
theorem global_mismatch_localizes {I : Type u} (g : GlobalSupportMismatch I) :
    ∃ i : I, g.current i ≠ g.required i := by
  classical
  by_cases h : ∃ i : I, g.current i ≠ g.required i
  · exact h
  · have hall : ∀ i : I, g.current i = g.required i := by
      intro i
      by_cases hi : g.current i = g.required i
      · exact hi
      · exact False.elim (h ⟨i, hi⟩)
    exfalso
    apply g.mismatch
    funext i
    exact hall i

/-- Compile a localized profile disagreement into the Cycle-5 support defect.
    This carries no semantic failure-mode label. -/
def localizedDefect {I : Type u} (g : GlobalSupportMismatch I)
    (i : I) (hi : g.current i ≠ g.required i) : SupportDefect where
  current := g.current i
  required := g.required i
  mismatch := hi

/-- A raw global verifier disagreement therefore yields some local defect whose
    repair polarity is determined by the defect itself. -/
theorem global_mismatch_yields_inferred_repair_direction
    {I : Type u} (g : GlobalSupportMismatch I) :
    ∃ i : I, ∃ hi : g.current i ≠ g.required i,
      RequiresRemoval (localizedDefect g i hi) ∨
      RequiresGeneration (localizedDefect g i hi) := by
  rcases global_mismatch_localizes g with ⟨i, hi⟩
  exact ⟨i, hi, mismatch_determines_polarity (localizedDefect g i hi)⟩

/-- If every coordinate already agrees, no global verifier mismatch can exist.
    This is the exact ablation counterpart to localization. -/
theorem pointwise_agreement_blocks_global_mismatch
    {I : Type u} (current required : I → Bool)
    (hagree : ∀ i, current i = required i) :
    ¬ (current ≠ required) := by
  intro hneq
  apply hneq
  funext i
  exact hagree i

/-- Cycle-6 decision: coordinate choice is not required merely to establish
    that a repair site and its direction exist.  What remains open is stronger:
    choosing a canonical/minimal witness when several coordinates disagree. -/
theorem verifier_profile_mismatch_eliminates_supplied_coordinate_for_existence
    {I : Type u} (g : GlobalSupportMismatch I) :
    (∃ i : I, g.current i ≠ g.required i) ∧
    (∃ i : I, ∃ hi : g.current i ≠ g.required i,
      RequiresRemoval (localizedDefect g i hi) ∨
      RequiresGeneration (localizedDefect g i hi)) := by
  exact ⟨global_mismatch_localizes g,
    global_mismatch_yields_inferred_repair_direction g⟩

#check global_mismatch_localizes
#check localizedDefect
#check global_mismatch_yields_inferred_repair_direction
#check pointwise_agreement_blocks_global_mismatch
#check verifier_profile_mismatch_eliminates_supplied_coordinate_for_existence

end KernelPurificationCycle6
