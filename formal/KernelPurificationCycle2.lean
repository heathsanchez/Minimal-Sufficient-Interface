import KernelPurificationCycle

namespace KernelPurificationCycle2

open IdentityForcedAsMinimalCompletion
open FailureForcesCompositionCompletion
open KernelPurificationCycle

/-- The second purification removes `FailedEndpoint` from the completion stage.
    The constructive kernel consumes only a certified demand relation.  How that
    relation was obtained is provenance, not completion semantics. -/
def demandCompletion
    (S : RawDirectedSubstrate) (D : CertifiedTransportDemand S) :
    RawDirectedSubstrate :=
  completeTransport S D

/-- Every old transport survives for every demand, so retention is intrinsic to
    demand completion and does not require a semantic failure label. -/
def retainOld
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj} (h : S.Hom x y) :
    (demandCompletion S D).Hom x y :=
  includeOld h

/-- Every demanded endpoint is realized, independently of the provenance of D. -/
theorem every_demand_is_filled
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj} (hxy : D.demanded x y) :
    Nonempty ((demandCompletion S D).Hom x y) := by
  exact satisfyDemand hxy

/-- Exactness is likewise demand-relative: if an endpoint was neither old nor
    demanded, completion cannot invent it. -/
theorem demand_completion_adds_nothing_unsupported
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj}
    (hnot : ¬ D.demanded x y)
    (hold : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty ((demandCompletion S D).Hom x y) := by
  exact no_new_transport_outside_demand hnot hold

/-- The unique-lift/free property is a property of the demand interface itself,
    not of identity, composition, endpoint residuals, or their provenance. -/
theorem demand_completion_lift_unique
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y}, D.demanded x y → H x y)
    (g : ∀ {x y}, CompletedTransportHom S D x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y),
      g (CompletedTransportHom.old h) = oldMap h)
    (hforced : ∀ {x y} (hxy : D.demanded x y),
      g (CompletedTransportHom.forced hxy) = forcedMap hxy) :
    ∀ {x y} (h : CompletedTransportHom S D x y),
      g h = lift H oldMap forcedMap h := by
  exact lift_unique H oldMap forcedMap g hold hforced

/-- A localized endpoint residual contributes to the constructive stage only by
    compiling to its demand relation. -/
def compileEndpointResidual
    {S : RawDirectedSubstrate} (r : FailedEndpoint S) :
    CertifiedTransportDemand S :=
  endpointDemand r

/-- Identity provenance factors completely through the generic demand interface. -/
def identityDemand
    {S : RawDirectedSubstrate}
    (i : FailureForcesIdentityCompletion.FailedContinuation S) :
    CertifiedTransportDemand S :=
  compileEndpointResidual (fromIdentityFailure i)

/-- Composition provenance factors completely through the same interface. -/
def compositionDemand
    {S : RawDirectedSubstrate}
    (c : FailureForcesCompositionCompletion.FailedComposition S) :
    CertifiedTransportDemand S :=
  compileEndpointResidual (fromCompositionFailure c)

theorem identity_demand_fills_exact_endpoint
    {S : RawDirectedSubstrate}
    (i : FailureForcesIdentityCompletion.FailedContinuation S) :
    Nonempty ((demandCompletion S (identityDemand i)).Hom i.start i.start) := by
  exact every_demand_is_filled (endpoint_is_demanded (fromIdentityFailure i))

theorem composition_demand_fills_exact_endpoint
    {S : RawDirectedSubstrate}
    (c : FailureForcesCompositionCompletion.FailedComposition S) :
    Nonempty ((demandCompletion S (compositionDemand c)).Hom c.source c.target) := by
  exact every_demand_is_filled (endpoint_is_demanded (fromCompositionFailure c))

/-- Second purification decision: after residual localization, neither the
    `FailedEndpoint` wrapper nor the semantic failure class is required by the
    completion mechanism.  Both identity and composition compile to the single
    demand interface and are then handled identically. -/
theorem endpoint_wrapper_and_failure_labels_fall_off
    {S : RawDirectedSubstrate}
    (i : FailureForcesIdentityCompletion.FailedContinuation S)
    (c : FailureForcesCompositionCompletion.FailedComposition S) :
    Nonempty ((demandCompletion S (identityDemand i)).Hom i.start i.start) ∧
    Nonempty ((demandCompletion S (compositionDemand c)).Hom c.source c.target) := by
  exact ⟨identity_demand_fills_exact_endpoint i,
    composition_demand_fills_exact_endpoint c⟩

/-- What hardens after cycle 2 is the demand relation itself: ablate it and an
    endpoint absent in the old substrate remains absent. -/
theorem demand_is_causally_necessary
    {S : RawDirectedSubstrate} (r : FailedEndpoint S) :
    Nonempty ((demandCompletion S (compileEndpointResidual r)).Hom r.source r.target) ∧
    ¬ Nonempty ((demandCompletion S (erasedEndpointDemand S)).Hom r.source r.target) := by
  exact ⟨every_demand_is_filled (endpoint_is_demanded r),
    erasing_endpoint_failure_blocks_genesis r⟩

#check every_demand_is_filled
#check demand_completion_adds_nothing_unsupported
#check demand_completion_lift_unique
#check identity_demand_fills_exact_endpoint
#check composition_demand_fills_exact_endpoint
#check endpoint_wrapper_and_failure_labels_fall_off
#check demand_is_causally_necessary

end KernelPurificationCycle2
