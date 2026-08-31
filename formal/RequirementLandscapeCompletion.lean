import GenericVerifiedCompletionKernel

namespace RequirementLandscapeCompletion

open GenericVerifiedCompletionKernel
open IdentityForcedAsMinimalCompletion

/-- A requirement landscape does not name a failed index.  It only states which
    capability indices are required.  The residual set is derived mechanically
    by intersecting that requirement with what is currently absent. -/
structure RequirementLandscape (I : Type) (Cap : I → Type) where
  required : I → Prop

/-- The verifier residual is not supplied as an index: every required capability
    that is currently absent becomes a generated demand. -/
def residualDemand {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) : I → Prop :=
  fun i => L.required i ∧ ¬ Nonempty (Cap i)

/-- The purified completion now operates on the whole derived residual set. -/
def completeLandscape {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) : I → Type :=
  CompletedCapability Cap (residualDemand L)

/-- Every old capability is retained independently of the requirement set. -/
def includeOld {I : Type} {Cap : I → Type}
    {L : RequirementLandscape I Cap} {i : I} (h : Cap i) :
    completeLandscape L i :=
  CompletedCapability.old h

/-- Any requirement that is absent before repair is automatically filled. -/
def fillResidual {I : Type} {Cap : I → Type}
    {L : RequirementLandscape I Cap} {i : I}
    (hreq : L.required i) (habs : ¬ Nonempty (Cap i)) :
    completeLandscape L i :=
  CompletedCapability.forced ⟨hreq, habs⟩

theorem every_required_absence_is_filled
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (hreq : L.required i) (habs : ¬ Nonempty (Cap i)) :
    Nonempty (completeLandscape L i) :=
  ⟨fillResidual hreq habs⟩

/-- Exactness: if an index was absent and was not required, landscape completion
    cannot invent a capability there. -/
theorem no_unrequired_absent_capability_added
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (hnot : ¬ L.required i) (habs : ¬ Nonempty (Cap i)) :
    ¬ Nonempty (completeLandscape L i) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact habs ⟨oldh⟩
  | forced hd => exact hnot hd.1

/-- If a requirement is already satisfied, completion adds no forced generator
    because it is not part of the residual set. -/
theorem satisfied_requirement_is_not_residual
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (hold : Nonempty (Cap i)) :
    ¬ residualDemand L i := by
  intro h
  exact h.2 hold

/-- Causal ablation: erase the requirement landscape and a previously absent
    capability stays absent. -/
def erasedLandscape {I : Type} {Cap : I → Type} :
    RequirementLandscape I Cap where
  required := fun _ => False

theorem erasing_requirements_blocks_genesis
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (hres : residualDemand L i) :
    ¬ Nonempty (completeLandscape (erasedLandscape : RequirementLandscape I Cap) i) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact hres.2 ⟨oldh⟩
  | forced hd => exact hd.1

/-- Universal property inherited by the landscape completion: interpretations
    are determined uniquely by old capabilities and the mechanically derived
    residual generators. -/
theorem landscape_lift_unique
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap)
    (H : I → Type)
    (oldMap : ∀ {i}, Cap i → H i)
    (forcedMap : ∀ {i}, residualDemand L i → H i)
    (g : ∀ {i}, completeLandscape L i → H i)
    (hold : ∀ {i} (h : Cap i),
      g (CompletedCapability.old h) = oldMap h)
    (hforced : ∀ {i} (h : residualDemand L i),
      g (CompletedCapability.forced h) = forcedMap h) :
    ∀ {i} (h : completeLandscape L i),
      g h = GenericVerifiedCompletionKernel.lift H oldMap forcedMap h := by
  exact GenericVerifiedCompletionKernel.lift_unique H oldMap forcedMap g hold hforced

/-- Cycle-3 generic certificate: no failed index is supplied to the completion.
    The landscape itself determines all required-and-absent indices. -/
theorem requirement_landscape_forces_exact_completion
    {I : Type} {Cap : I → Type}
    (L : RequirementLandscape I Cap) {i : I}
    (hreq : L.required i) (habs : ¬ Nonempty (Cap i)) :
    Nonempty (completeLandscape L i) ∧
    ¬ Nonempty (completeLandscape (erasedLandscape : RequirementLandscape I Cap) i) := by
  exact ⟨every_required_absence_is_filled L hreq habs,
    erasing_requirements_blocks_genesis L ⟨hreq, habs⟩⟩

/-- A closed-continuation verifier emits a requirement landscape, not a missing
    index.  The residual index is recovered by `residualDemand`. -/
def identityLandscape
    {S : RawDirectedSubstrate}
    (f : FailureForcesIdentityCompletion.FailedContinuation S) :
    RequirementLandscape (TransportIndex S) (TransportCapability S) where
  required := fun p => p = (f.start, f.start)

theorem identity_failure_is_derived_residual
    {S : RawDirectedSubstrate}
    (f : FailureForcesIdentityCompletion.FailedContinuation S) :
    residualDemand (identityLandscape f) (f.start, f.start) := by
  exact ⟨rfl,
    FailureForcesIdentityCompletion.failure_exposes_missing_self_transport f⟩

/-- A compositional verifier emits the analogous requirement landscape. -/
def compositionLandscape
    {S : RawDirectedSubstrate}
    (f : FailureForcesCompositionCompletion.FailedComposition S) :
    RequirementLandscape (TransportIndex S) (TransportCapability S) where
  required := fun p => p = (f.source, f.target)

theorem composition_failure_is_derived_residual
    {S : RawDirectedSubstrate}
    (f : FailureForcesCompositionCompletion.FailedComposition S) :
    residualDemand (compositionLandscape f) (f.source, f.target) := by
  exact ⟨rfl, f.unrealized⟩

theorem identity_landscape_forces_completion
    {S : RawDirectedSubstrate}
    (f : FailureForcesIdentityCompletion.FailedContinuation S) :
    Nonempty (completeLandscape (identityLandscape f) (f.start, f.start)) ∧
    ¬ Nonempty
      (completeLandscape
        (erasedLandscape : RequirementLandscape (TransportIndex S) (TransportCapability S))
        (f.start, f.start)) := by
  exact requirement_landscape_forces_exact_completion
    (identityLandscape f) rfl
    (FailureForcesIdentityCompletion.failure_exposes_missing_self_transport f)

theorem composition_landscape_forces_completion
    {S : RawDirectedSubstrate}
    (f : FailureForcesCompositionCompletion.FailedComposition S) :
    Nonempty (completeLandscape (compositionLandscape f) (f.source, f.target)) ∧
    ¬ Nonempty
      (completeLandscape
        (erasedLandscape : RequirementLandscape (TransportIndex S) (TransportCapability S))
        (f.source, f.target)) := by
  exact requirement_landscape_forces_exact_completion
    (compositionLandscape f) rfl f.unrealized

#check requirement_landscape_forces_exact_completion
#check no_unrequired_absent_capability_added
#check satisfied_requirement_is_not_residual
#check landscape_lift_unique
#check identity_failure_is_derived_residual
#check composition_failure_is_derived_residual
#check identity_landscape_forces_completion
#check composition_landscape_forces_completion

end RequirementLandscapeCompletion
