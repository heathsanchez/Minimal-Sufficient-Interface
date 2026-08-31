import FailureForcesIdentityCompletion
import FailureForcesCompositionCompletion

namespace GenericVerifiedCompletionKernel

open IdentityForcedAsMinimalCompletion

/-- A completely generic verifier-certified absence.  The kernel knows only an
    index type `I`, an available capability family `Cap`, one index whose
    capability is required, and a certificate that it is currently absent.
    There is no notion of object, endpoint, identity, composition, or transport
    in this primitive. -/
structure MissingCapability (I : Type) (Cap : I → Type) where
  index : I
  unrealized : ¬ Nonempty (Cap index)

/-- A residual generates exactly one demanded capability index. -/
def generatedDemand {I : Type} {Cap : I → Type}
    (r : MissingCapability I Cap) : I → Prop :=
  fun i => i = r.index

/-- Exact ablation of the residual signal. -/
def erasedDemand {I : Type} : I → Prop := fun _ => False

/-- Generic free completion: preserve every old capability and freely adjoin one
    generator at every certified demanded index. -/
inductive CompletedCapability {I : Type}
    (Cap : I → Type) (D : I → Prop) : I → Type where
  | old {i : I} : Cap i → CompletedCapability Cap D i
  | forced {i : I} : D i → CompletedCapability Cap D i

/-- Every old capability survives. -/
def includeOld {I : Type} {Cap : I → Type} {D : I → Prop}
    {i : I} (h : Cap i) : CompletedCapability Cap D i :=
  .old h

/-- Every certified demand receives a filler. -/
def forcedCapability {I : Type} {Cap : I → Type} {D : I → Prop}
    {i : I} (h : D i) : CompletedCapability Cap D i :=
  .forced h

theorem index_is_generated_demand
    {I : Type} {Cap : I → Type} (r : MissingCapability I Cap) :
    generatedDemand r r.index := rfl

theorem residual_forces_filler
    {I : Type} {Cap : I → Type} (r : MissingCapability I Cap) :
    Nonempty (CompletedCapability Cap (generatedDemand r) r.index) :=
  ⟨forcedCapability (index_is_generated_demand r)⟩

theorem residual_forces_genuinely_new_filler
    {I : Type} {Cap : I → Type} (r : MissingCapability I Cap) :
    (¬ Nonempty (Cap r.index)) ∧
      Nonempty (CompletedCapability Cap (generatedDemand r) r.index) := by
  exact ⟨r.unrealized, residual_forces_filler r⟩

/-- No unrelated absent capability is invented. -/
theorem no_unrelated_capability_added
    {I : Type} {Cap : I → Type} (r : MissingCapability I Cap)
    {i : I} (hne : i ≠ r.index) (holdNone : ¬ Nonempty (Cap i)) :
    ¬ Nonempty (CompletedCapability Cap (generatedDemand r) i) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact holdNone ⟨oldh⟩
  | forced hd => exact hne hd

/-- Removing the residual signal blocks genesis at exactly the failed index. -/
theorem erasing_residual_erases_filler
    {I : Type} {Cap : I → Type} (r : MissingCapability I Cap) :
    ¬ Nonempty (CompletedCapability Cap erasedDemand r.index) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact r.unrealized ⟨oldh⟩
  | forced hd => exact hd

/-- Canonical interpretation of the generic free completion. -/
def lift {I : Type} {Cap : I → Type} {D : I → Prop}
    (H : I → Type)
    (oldMap : ∀ {i}, Cap i → H i)
    (forcedMap : ∀ {i}, D i → H i) :
    ∀ {i}, CompletedCapability Cap D i → H i
  | _, .old h => oldMap h
  | _, .forced h => forcedMap h

/-- Universal property: any interpretation agreeing on old and forced generators
    is uniquely determined on every completed capability. -/
theorem lift_unique
    {I : Type} {Cap : I → Type} {D : I → Prop}
    (H : I → Type)
    (oldMap : ∀ {i}, Cap i → H i)
    (forcedMap : ∀ {i}, D i → H i)
    (g : ∀ {i}, CompletedCapability Cap D i → H i)
    (hold : ∀ {i} (h : Cap i), g (CompletedCapability.old h) = oldMap h)
    (hforced : ∀ {i} (h : D i), g (CompletedCapability.forced h) = forcedMap h) :
    ∀ {i} (h : CompletedCapability Cap D i),
      g h = lift H oldMap forcedMap h := by
  intro i h
  cases h with
  | old oldh => exact hold oldh
  | forced hd => exact hforced hd

/-- Purification-cycle-2 certificate. -/
theorem verified_absence_forces_initial_completion
    {I : Type} {Cap : I → Type} (r : MissingCapability I Cap) :
    ((¬ Nonempty (Cap r.index)) ∧
      Nonempty (CompletedCapability Cap (generatedDemand r) r.index)) ∧
    (¬ Nonempty (CompletedCapability Cap erasedDemand r.index)) := by
  exact ⟨residual_forces_genuinely_new_filler r,
    erasing_residual_erases_filler r⟩

/-- Transport is now only one specialization of the generic indexed capability
    family. -/
def TransportIndex (S : RawDirectedSubstrate) := S.Obj × S.Obj

def TransportCapability (S : RawDirectedSubstrate) : TransportIndex S → Type :=
  fun p => S.Hom p.1 p.2

/-- Closed-continuation failure compiles to a generic missing capability. -/
def fromIdentityFailure
    {S : RawDirectedSubstrate}
    (f : FailureForcesIdentityCompletion.FailedContinuation S) :
    MissingCapability (TransportIndex S) (TransportCapability S) where
  index := (f.start, f.start)
  unrealized := FailureForcesIdentityCompletion.failure_exposes_missing_self_transport f

/-- Failed composition compiles to the same generic missing-capability object. -/
def fromCompositionFailure
    {S : RawDirectedSubstrate}
    (f : FailureForcesCompositionCompletion.FailedComposition S) :
    MissingCapability (TransportIndex S) (TransportCapability S) where
  index := (f.source, f.target)
  unrealized := f.unrealized

theorem identity_failure_is_generic_completion_instance
    {S : RawDirectedSubstrate}
    (f : FailureForcesIdentityCompletion.FailedContinuation S) :
    ((¬ Nonempty (TransportCapability S (fromIdentityFailure f).index)) ∧
      Nonempty
        (CompletedCapability (TransportCapability S)
          (generatedDemand (fromIdentityFailure f))
          (fromIdentityFailure f).index)) ∧
    (¬ Nonempty
      (CompletedCapability (TransportCapability S)
        erasedDemand (fromIdentityFailure f).index)) := by
  exact verified_absence_forces_initial_completion (fromIdentityFailure f)

theorem composition_failure_is_generic_completion_instance
    {S : RawDirectedSubstrate}
    (f : FailureForcesCompositionCompletion.FailedComposition S) :
    ((¬ Nonempty (TransportCapability S (fromCompositionFailure f).index)) ∧
      Nonempty
        (CompletedCapability (TransportCapability S)
          (generatedDemand (fromCompositionFailure f))
          (fromCompositionFailure f).index)) ∧
    (¬ Nonempty
      (CompletedCapability (TransportCapability S)
        erasedDemand (fromCompositionFailure f).index)) := by
  exact verified_absence_forces_initial_completion (fromCompositionFailure f)

#check verified_absence_forces_initial_completion
#check identity_failure_is_generic_completion_instance
#check composition_failure_is_generic_completion_instance
#check lift_unique

end GenericVerifiedCompletionKernel
