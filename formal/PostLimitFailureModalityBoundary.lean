import ExtensionalOmegaFailureObstruction
import ReflexivityNotForcedByDirectedFailure
import FailureForcesIdentityCompletion

namespace PostLimitFailureModalityBoundary

/-- The exact post-limit boundary reached by the current program.

    1. At the genuine Nat-bit omega closure, extensional observations already
       separate points, so no distinct-but-invisible state residual exists.
    2. Replacing that residual by arbitrary one-way directed asymmetry is still
       insufficient to force reflexive/self transport.
    3. A strictly stronger verifier certificate -- a failed continuation whose
       endpoint is certified to return to its start -- does force exactly the
       missing self-transport, and ablation of that failure signal blocks it.

    This theorem deliberately does *not* claim that closed-continuation failure
    is the only possible post-limit modality.  It certifies the boundary between
    two insufficient failure notions and one sufficient, already-proved notion.
-/
theorem post_limit_failure_modality_boundary :
    (¬ Nonempty
      (ExtensionalOmegaFailureObstruction.ExtensionalFailure
        ExtensionalOmegaFailureObstruction.natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    (¬ (∀ (S : ReflexivityNotForcedByDirectedFailure.RawDirectedSubstrate)
          (r : ReflexivityNotForcedByDirectedFailure.DirectedAsymmetry S),
        Nonempty (S.Hom r.left r.left))) ∧
    (¬ (∀ (S : ReflexivityNotForcedByDirectedFailure.RawDirectedSubstrate)
          (r : ReflexivityNotForcedByDirectedFailure.DirectedAsymmetry S),
        Nonempty (S.Hom r.right r.right))) ∧
    (∀ (S : IdentityForcedAsMinimalCompletion.RawDirectedSubstrate)
        (f : FailureForcesIdentityCompletion.FailedContinuation S),
      ((¬ Nonempty (S.Hom f.start f.start)) ∧
        Nonempty
          ((IdentityForcedAsMinimalCompletion.complete S
            (FailureForcesIdentityCompletion.generatedDemand f)).Hom
              f.start f.start)) ∧
      (¬ Nonempty
        ((IdentityForcedAsMinimalCompletion.complete S
          FailureForcesIdentityCompletion.erasedDemand).Hom
            f.start f.start))) := by
  exact ⟨
    ExtensionalOmegaFailureObstruction.exact_nat_omega_has_no_extensional_failure,
    ReflexivityNotForcedByDirectedFailure.source_reflexivity_not_forced,
    ReflexivityNotForcedByDirectedFailure.target_reflexivity_not_forced,
    fun _ f =>
      FailureForcesIdentityCompletion.verified_failure_forces_identity_as_minimal_completion f
  ⟩

/-- Scientific corollary stated without any ordinal-tagged post-limit object:
    the completed finite observation family itself exhausts extensional
    state-separation evidence, so any further justified structural genesis must
    use evidence not reducible to a fresh invisible state pair. -/
theorem exact_omega_requires_nonextensional_evidence_for_further_refinement :
    ¬ Nonempty
      (ExtensionalOmegaFailureObstruction.ExtensionalFailure
        ExtensionalOmegaFailureObstruction.natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage) :=
  ExtensionalOmegaFailureObstruction.exact_nat_omega_has_no_extensional_failure

#check post_limit_failure_modality_boundary
#check exact_omega_requires_nonextensional_evidence_for_further_refinement

end PostLimitFailureModalityBoundary
