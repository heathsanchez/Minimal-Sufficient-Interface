import ExtensionalOmegaFailureObstruction
import FailureForcesIdentityCompletion

namespace PostLimitStructuralPhaseTransition

open ExtensionalOmegaFailureObstruction
open IdentityForcedAsMinimalCompletion
open FailureForcesIdentityCompletion

/-- A raw operational substrate on the same Nat carrier whose state identity is
    already completely separated by the omega observation family, but whose
    transport structure initially contains no arrows at all. -/
def emptyNatTransport : RawDirectedSubstrate where
  Obj := Nat
  Hom := fun _ _ => Empty

/-- At any already-observationally-distinguished Nat state, a verifier may ask
    for a closed continuation that the raw transport substrate cannot realize. -/
def closedFailureAt (n : Nat) : FailedContinuation emptyNatTransport where
  start := n
  finish := n
  returns := rfl
  unrealized := by
    intro h
    rcases h with ⟨h⟩
    exact Empty.elim h

/-- Exact state identity does not imply developmental terminality.

    The omega family of Nat-bit observations is already point-separating, so
    there is no remaining distinct-but-invisible state pair to refine.  Yet on
    that very same carrier a verifier-certified failed closed continuation can
    still force genuinely new self-transport by the already-proved least/free
    completion, and erasing the failure signal prevents the new law.

    This is the formal phase change from *extensional representation repair* to
    *structural law/transport genesis*: development can continue after the
    behavioural quotient has become discrete, without inventing a finer state
    equality. -/
theorem exact_identity_does_not_imply_developmental_terminal :
    PointSeparating natBitObserve InfiniteBitOmegaFixedPoint.omegaLanguage ∧
    (¬ Nonempty
      (ExtensionalFailure natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    ∃ f : FailedContinuation emptyNatTransport,
      ((¬ Nonempty (emptyNatTransport.Hom f.start f.start)) ∧
        Nonempty
          ((complete emptyNatTransport (generatedDemand f)).Hom
            f.start f.start)) ∧
      (¬ Nonempty
        ((complete emptyNatTransport erasedDemand).Hom
          f.start f.start)) := by
  refine ⟨exact_nat_omega_is_pointSeparating,
    exact_nat_omega_has_no_extensional_failure, ?_⟩
  let f := closedFailureAt 0
  exact ⟨f, verified_failure_forces_identity_as_minimal_completion f⟩

/-- The phase transition is not caused by adding a hidden state coordinate:
    the structural completion has definitionally the same object carrier. -/
theorem structural_completion_preserves_state_carrier
    (n : Nat) :
    (complete emptyNatTransport
      (generatedDemand (closedFailureAt n))).Obj = Nat := rfl

/-- Nor does the new transport require reopening extensional state ambiguity:
    the original omega observation family remains point-separating on the
    unchanged carrier after the structural completion. -/
theorem point_separation_survives_structural_genesis (n : Nat) :
    PointSeparating natBitObserve InfiniteBitOmegaFixedPoint.omegaLanguage :=
  exact_nat_omega_is_pointSeparating

#check exact_identity_does_not_imply_developmental_terminal
#check structural_completion_preserves_state_carrier
#check point_separation_survives_structural_genesis

end PostLimitStructuralPhaseTransition
