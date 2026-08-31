import CapabilityGeneratedFutureInterface

namespace CapabilityGeneratedFutureExactness

open GenericVerifiedCompletionKernel
open RequirementLandscapeCompletion
open CapabilityGeneratedFutureInterface

/-- The recomputed future set after completion has exactly two sources: an old
    inhabited capability, or a mechanically derived residual generator.  There
    is no third way for a future to appear. -/
theorem generated_after_iff_old_or_residual
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I} :
    generatedReachableAfter L i ↔
      generatedReachable Cap i ∨ residualDemand L i := by
  constructor
  · rintro ⟨h⟩
    cases h with
    | old hold => exact Or.inl ⟨hold⟩
    | forced hres => exact Or.inr hres
  · intro h
    cases h with
    | inl hold =>
        rcases hold with ⟨hold⟩
        exact ⟨CompletedCapability.old hold⟩
    | inr hres =>
        exact ⟨CompletedCapability.forced hres⟩

/-- At an index that was genuinely absent before completion, post-completion
    reachability is equivalent to being in the verifier-derived residual set. -/
theorem new_reachability_iff_residual
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (habs : ¬ generatedReachable Cap i) :
    generatedReachableAfter L i ↔ residualDemand L i := by
  constructor
  · intro hafter
    rcases (generated_after_iff_old_or_residual L).1 hafter with hold | hres
    · exact False.elim (habs hold)
    · exact hres
  · intro hres
    exact (generated_after_iff_old_or_residual L).2 (Or.inr hres)

/-- A genuinely new future is therefore not merely correlated with a residual:
    its novelty is exactly residual membership. -/
theorem genuinely_new_future_iff_residual
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I} :
    (generatedReachableAfter L i ∧ ¬ generatedReachable Cap i) ↔
      residualDemand L i := by
  constructor
  · rintro ⟨hafter, habs⟩
    exact (new_reachability_iff_residual L habs).1 hafter
  · intro hres
    exact ⟨
      (generated_after_iff_old_or_residual L).2 (Or.inr hres),
      hres.2
    ⟩

/-- No unrelated future genesis: every genuinely new future must have been both
    required by the landscape and absent before completion. -/
theorem no_unrelated_future_genesis
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (hnew : generatedReachableAfter L i ∧ ¬ generatedReachable Cap i) :
    L.required i ∧ ¬ Nonempty (Cap i) := by
  exact (genuinely_new_future_iff_residual L).1 hnew

/-- Conversely, every verifier-derived residual is realized as exactly such a
    genuinely new future.  This gives extensional equality between residual
    indices and newly generated future indices. -/
theorem residuals_are_exactly_new_futures
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) (i : I) :
    residualDemand L i ↔
      generatedReachableAfter L i ∧ ¬ generatedReachable Cap i := by
  exact (genuinely_new_future_iff_residual L).symm

/-- Requirement ablation leaves no new futures at all. -/
theorem ablated_interface_has_no_new_futures
    {I : Type} {Cap : I → Type} {i : I} :
    ¬ (generatedReachableAfter
          (erasedLandscape : RequirementLandscape I Cap) i ∧
        ¬ generatedReachable Cap i) := by
  intro hnew
  have hres := (genuinely_new_future_iff_residual
    (erasedLandscape : RequirementLandscape I Cap)).1 hnew
  exact hres.1

namespace Witness

inductive Idx where
  | old
  | new
  | unrelated
  deriving DecidableEq

inductive Existing where | token

abbrev Cap : Idx → Type
  | .old => Existing
  | .new => Empty
  | .unrelated => Empty

def L : RequirementLandscape Idx Cap where
  required
    | .new => True
    | _ => False

theorem old_before : generatedReachable Cap Idx.old :=
  ⟨Existing.token⟩

theorem new_absent : ¬ generatedReachable Cap Idx.new := by
  intro h
  rcases h with ⟨h⟩
  exact nomatch h

theorem unrelated_absent : ¬ generatedReachable Cap Idx.unrelated := by
  intro h
  rcases h with ⟨h⟩
  exact nomatch h

theorem new_residual : residualDemand L Idx.new :=
  ⟨trivial, new_absent⟩

theorem exact_new_future :
    generatedReachableAfter L Idx.new ∧
      ¬ generatedReachable Cap Idx.new := by
  exact (genuinely_new_future_iff_residual L).2 new_residual

theorem unrelated_not_generated :
    ¬ generatedReachableAfter L Idx.unrelated := by
  intro hafter
  have hres := (new_reachability_iff_residual L unrelated_absent).1 hafter
  exact hres.1

theorem old_retained : generatedReachableAfter L Idx.old := by
  exact old_generated_futures_embed L old_before

end Witness

#check generated_after_iff_old_or_residual
#check new_reachability_iff_residual
#check genuinely_new_future_iff_residual
#check no_unrelated_future_genesis
#check residuals_are_exactly_new_futures
#check ablated_interface_has_no_new_futures
#check Witness.exact_new_future
#check Witness.unrelated_not_generated
#check Witness.old_retained

end CapabilityGeneratedFutureExactness
