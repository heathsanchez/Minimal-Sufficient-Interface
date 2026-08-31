import ExtensionalOmegaFailureObstruction
import FailureForcesCompositionCompletion

namespace PostLimitCompositionPhaseTransition

open ExtensionalOmegaFailureObstruction
open IdentityForcedAsMinimalCompletion
open FailureForcesCompositionCompletion

/-- Same Nat state carrier as the exact omega theorem, now equipped with an
    identity transport at every state and two consecutive nonidentity
    transports.  The endpoint composite 0 -> 2 is deliberately absent. -/
inductive IdentityChainHom : Nat → Nat → Type where
  | id (n : Nat) : IdentityChainHom n n
  | e01 : IdentityChainHom 0 1
  | e12 : IdentityChainHom 1 2

def identityChainTransport : RawDirectedSubstrate where
  Obj := Nat
  Hom := IdentityChainHom

/-- Reflexive transport is already present everywhere before the new phase. -/
theorem identity_transport_present_everywhere :
    ∀ n : Nat, Nonempty (identityChainTransport.Hom n n) := by
  intro n
  exact ⟨IdentityChainHom.id n⟩

/-- The two-step path exists before repair. -/
theorem composable_inputs_present :
    Nonempty (identityChainTransport.Hom 0 1) ∧
    Nonempty (identityChainTransport.Hom 1 2) := by
  exact ⟨⟨IdentityChainHom.e01⟩, ⟨IdentityChainHom.e12⟩⟩

/-- But its composite endpoint transport is not representable yet. -/
theorem composite_02_absent :
    ¬ Nonempty (identityChainTransport.Hom 0 2) := by
  intro h
  rcases h with ⟨h⟩
  cases h

/-- Verifier-certified compositional residual on a carrier that already has
    identities. -/
def failedChainComposition : FailedComposition identityChainTransport where
  source := 0
  middle := 1
  target := 2
  first := IdentityChainHom.e01
  second := IdentityChainHom.e12
  unrealized := composite_02_absent

/-- At exact extensional omega, point separation and all identities can already
    hold while a strictly new compositional consequence is still forced by
    verified failure.  Erasing the failure signal blocks that consequence. -/
theorem exact_identity_and_reflexivity_do_not_imply_composition_terminal :
    PointSeparating natBitObserve
      InfiniteBitOmegaFixedPoint.omegaLanguage ∧
    (¬ Nonempty
      (ExtensionalFailure natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    (∀ n : Nat, Nonempty (identityChainTransport.Hom n n)) ∧
    ((¬ Nonempty (identityChainTransport.Hom 0 2)) ∧
      Nonempty
        ((completeTransport identityChainTransport
          (generatedCompositeDemand failedChainComposition)).Hom 0 2)) ∧
    (¬ Nonempty
      ((completeTransport identityChainTransport
        (erasedDemand identityChainTransport)).Hom 0 2)) := by
  refine ⟨exact_nat_omega_is_pointSeparating,
    exact_nat_omega_has_no_extensional_failure,
    identity_transport_present_everywhere, ?_, ?_⟩
  · exact failure_forces_genuinely_new_composite failedChainComposition
  · exact erasing_failure_signal_erases_composite failedChainComposition

/-- The structural phase transition changes no extensional state: its object
    carrier remains exactly Nat. -/
theorem composition_completion_preserves_state_carrier :
    (completeTransport identityChainTransport
      (generatedCompositeDemand failedChainComposition)).Obj = Nat := rfl

/-- The already complete Nat-bit identity remains point-separating after the
    compositional repair. -/
theorem point_separation_survives_composition_genesis :
    PointSeparating natBitObserve
      InfiniteBitOmegaFixedPoint.omegaLanguage :=
  exact_nat_omega_is_pointSeparating

/-- The failure-generated repair is local: for any absent endpoint pair other
    than 0 -> 2, no new transport is manufactured. -/
theorem composition_repair_is_local
    {x y : Nat}
    (hunrelated : x ≠ 0 ∨ y ≠ 2)
    (holdNone : ¬ Nonempty (identityChainTransport.Hom x y)) :
    ¬ Nonempty
      ((completeTransport identityChainTransport
        (generatedCompositeDemand failedChainComposition)).Hom x y) := by
  exact failure_repair_adds_no_unrelated_transport
    failedChainComposition hunrelated holdNone

/-- Exact phase certificate: extensional completion is exhausted, identities
    are already everywhere, the composable inputs are already present, yet the
    verified composition residual forces a new transport and only that repair;
    deleting the residual prevents the transition. -/
theorem post_limit_composition_phase_transition :
    (¬ Nonempty
      (ExtensionalFailure natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    (∀ n : Nat, Nonempty (identityChainTransport.Hom n n)) ∧
    (Nonempty (identityChainTransport.Hom 0 1) ∧
      Nonempty (identityChainTransport.Hom 1 2)) ∧
    (¬ Nonempty (identityChainTransport.Hom 0 2)) ∧
    Nonempty
      ((completeTransport identityChainTransport
        (generatedCompositeDemand failedChainComposition)).Hom 0 2) ∧
    (¬ Nonempty
      ((completeTransport identityChainTransport
        (erasedDemand identityChainTransport)).Hom 0 2)) := by
  exact ⟨exact_nat_omega_has_no_extensional_failure,
    identity_transport_present_everywhere,
    composable_inputs_present,
    composite_02_absent,
    failure_forces_composite failedChainComposition,
    erasing_failure_signal_erases_composite failedChainComposition⟩

#check identity_transport_present_everywhere
#check composable_inputs_present
#check composite_02_absent
#check exact_identity_and_reflexivity_do_not_imply_composition_terminal
#check composition_completion_preserves_state_carrier
#check point_separation_survives_composition_genesis
#check composition_repair_is_local
#check post_limit_composition_phase_transition

end PostLimitCompositionPhaseTransition
