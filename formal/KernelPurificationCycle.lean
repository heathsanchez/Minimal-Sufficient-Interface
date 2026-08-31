import FailureForcesIdentityCompletion
import FailureForcesCompositionCompletion

namespace KernelPurificationCycle

open IdentityForcedAsMinimalCompletion
open FailureForcesCompositionCompletion

/-- Purified residual: the completion kernel does not know whether the missing
    endpoint came from identity, composition, or any other certified boundary.
    It only knows that transport from `source` to `target` is required and was
    absent in the old substrate. -/
structure FailedEndpoint (S : RawDirectedSubstrate) where
  source : S.Obj
  target : S.Obj
  unrealized : ¬ Nonempty (S.Hom source target)

/-- The residual itself generates exactly one endpoint demand. -/
def endpointDemand {S : RawDirectedSubstrate}
    (r : FailedEndpoint S) : CertifiedTransportDemand S where
  demanded := fun x y => x = r.source ∧ y = r.target

/-- Exact ablation of the residual-to-demand link. -/
def erasedEndpointDemand (S : RawDirectedSubstrate) :
    CertifiedTransportDemand S where
  demanded := fun _ _ => False

theorem endpoint_is_demanded
    {S : RawDirectedSubstrate} (r : FailedEndpoint S) :
    (endpointDemand r).demanded r.source r.target := by
  exact ⟨rfl, rfl⟩

/-- Generic constructive half of the kernel: a certified absent endpoint is
    freely adjoined, independently of the semantic name of the failure. -/
theorem failed_endpoint_forces_genuinely_new_transport
    {S : RawDirectedSubstrate} (r : FailedEndpoint S) :
    (¬ Nonempty (S.Hom r.source r.target)) ∧
    Nonempty
      ((completeTransport S (endpointDemand r)).Hom r.source r.target) := by
  exact ⟨r.unrealized, satisfyDemand (endpoint_is_demanded r)⟩

/-- Purity: no absent endpoint outside the certified residual is manufactured. -/
theorem failed_endpoint_adds_no_unrelated_transport
    {S : RawDirectedSubstrate} (r : FailedEndpoint S)
    {x y : S.Obj}
    (hunrelated : x ≠ r.source ∨ y ≠ r.target)
    (holdNone : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty ((completeTransport S (endpointDemand r)).Hom x y) := by
  apply no_new_transport_outside_demand ?_ holdNone
  intro hxy
  rcases hxy with ⟨hx, hy⟩
  rcases hunrelated with hs | ht
  · exact hs hx
  · exact ht hy

/-- Causal ablation: without the certified residual, no new endpoint appears. -/
theorem erasing_endpoint_failure_blocks_genesis
    {S : RawDirectedSubstrate} (r : FailedEndpoint S) :
    ¬ Nonempty
      ((completeTransport S (erasedEndpointDemand S)).Hom r.source r.target) := by
  apply no_new_transport_outside_demand ?_ r.unrealized
  intro h
  exact h

/-- Universal property of the purified completion: every interpretation of the
    old transports and the single certified endpoint receives the unique map
    induced by the free completion. -/
theorem failed_endpoint_lift_unique
    {S : RawDirectedSubstrate} (r : FailedEndpoint S)
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y}, (endpointDemand r).demanded x y → H x y)
    (g : ∀ {x y}, CompletedTransportHom S (endpointDemand r) x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y),
      g (CompletedTransportHom.old h) = oldMap h)
    (hforced : ∀ {x y} (hxy : (endpointDemand r).demanded x y),
      g (CompletedTransportHom.forced hxy) = forcedMap hxy) :
    ∀ {x y} (h : CompletedTransportHom S (endpointDemand r) x y),
      g h = lift H oldMap forcedMap h := by
  exact lift_unique H oldMap forcedMap g hold hforced

/-- The generic verified-completion certificate. -/
theorem verified_failed_endpoint_initial_completion
    {S : RawDirectedSubstrate} (r : FailedEndpoint S) :
    ((¬ Nonempty (S.Hom r.source r.target)) ∧
      Nonempty
        ((completeTransport S (endpointDemand r)).Hom r.source r.target)) ∧
    (¬ Nonempty
      ((completeTransport S (erasedEndpointDemand S)).Hom r.source r.target)) := by
  exact ⟨failed_endpoint_forces_genuinely_new_transport r,
    erasing_endpoint_failure_blocks_genesis r⟩

/-- Identity failure is only a producer of a generic failed endpoint.  Identity
    is no longer a primitive of the completion kernel. -/
def fromIdentityFailure
    {S : RawDirectedSubstrate}
    (f : FailureForcesIdentityCompletion.FailedContinuation S) :
    FailedEndpoint S where
  source := f.start
  target := f.start
  unrealized := FailureForcesIdentityCompletion.failure_exposes_missing_self_transport f

/-- Composition failure is likewise only a producer of a generic failed
    endpoint.  Composition is no longer a primitive of the completion kernel. -/
def fromCompositionFailure
    {S : RawDirectedSubstrate}
    (f : FailureForcesCompositionCompletion.FailedComposition S) :
    FailedEndpoint S where
  source := f.source
  target := f.target
  unrealized := f.unrealized

/-- First purification decision: both previously separate genesis routes are
    instances of one residual-to-initial-completion theorem. -/
theorem identity_and_composition_share_one_completion_kernel
    {S : RawDirectedSubstrate}
    (i : FailureForcesIdentityCompletion.FailedContinuation S)
    (c : FailureForcesCompositionCompletion.FailedComposition S) :
    (((¬ Nonempty (S.Hom i.start i.start)) ∧
      Nonempty
        ((completeTransport S (endpointDemand (fromIdentityFailure i))).Hom
          i.start i.start)) ∧
      (¬ Nonempty
        ((completeTransport S (erasedEndpointDemand S)).Hom i.start i.start))) ∧
    (((¬ Nonempty (S.Hom c.source c.target)) ∧
      Nonempty
        ((completeTransport S (endpointDemand (fromCompositionFailure c))).Hom
          c.source c.target)) ∧
      (¬ Nonempty
        ((completeTransport S (erasedEndpointDemand S)).Hom
          c.source c.target))) := by
  exact ⟨verified_failed_endpoint_initial_completion (fromIdentityFailure i),
    verified_failed_endpoint_initial_completion (fromCompositionFailure c)⟩

/-- What survives the first purification cycle: completion is generic, while the
    remaining distinction between identity and composition lives entirely in
    the extractor that turns a richer verifier trace into `FailedEndpoint`. -/
theorem purification_localizes_remaining_boundary
    {S : RawDirectedSubstrate}
    (i : FailureForcesIdentityCompletion.FailedContinuation S)
    (c : FailureForcesCompositionCompletion.FailedComposition S) :
    (fromIdentityFailure i).source = i.start ∧
    (fromIdentityFailure i).target = i.start ∧
    (fromCompositionFailure c).source = c.source ∧
    (fromCompositionFailure c).target = c.target := by
  exact ⟨rfl, rfl, rfl, rfl⟩

#check failed_endpoint_forces_genuinely_new_transport
#check failed_endpoint_adds_no_unrelated_transport
#check erasing_endpoint_failure_blocks_genesis
#check failed_endpoint_lift_unique
#check verified_failed_endpoint_initial_completion
#check fromIdentityFailure
#check fromCompositionFailure
#check identity_and_composition_share_one_completion_kernel
#check purification_localizes_remaining_boundary

end KernelPurificationCycle
