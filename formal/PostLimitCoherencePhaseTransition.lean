import ExtensionalOmegaFailureObstruction
import FailureForcesCoherenceCompletion

namespace PostLimitCoherencePhaseTransition

open FailureForcesCoherenceCompletion

/-- Before a composition constructor is admitted, the chain contains identities
    and three atomic transports only. -/
inductive AtomicChainHom : Nat → Nat → Type where
  | id (n : Nat) : AtomicChainHom n n
  | e01 : AtomicChainHom 0 1
  | e12 : AtomicChainHom 1 2
  | e23 : AtomicChainHom 2 3

/-- There is no atomic 0→3 transport.  Thus a threefold-composite coherence
    residual cannot even be formed in the pre-composition language. -/
theorem no_three_step_endpoint_before_composition :
    ¬ Nonempty (AtomicChainHom 0 3) := by
  intro h
  rcases h with ⟨h⟩
  cases h

/-- Composition closes the arrow language under binary composition while
    retaining the same Nat object carrier.  Parenthesized composites remain
    syntactically visible so coherence has not been assumed in advance. -/
inductive CompositionalChainHom : Nat → Nat → Type where
  | id (n : Nat) : CompositionalChainHom n n
  | e01 : CompositionalChainHom 0 1
  | e12 : CompositionalChainHom 1 2
  | e23 : CompositionalChainHom 2 3
  | comp {a b c : Nat} :
      CompositionalChainHom a b →
      CompositionalChainHom b c →
      CompositionalChainHom a c

/-- The post-composition stage contains no equations between composite syntax
    trees yet. -/
def compositionalStage : RawCompositionalSubstrate where
  Obj := Nat
  Hom := CompositionalChainHom
  id := CompositionalChainHom.id
  comp := CompositionalChainHom.comp
  Law := fun _ _ => False

def f01 : compositionalStage.Hom 0 1 := CompositionalChainHom.e01
def f12 : compositionalStage.Hom 1 2 := CompositionalChainHom.e12
def f23 : compositionalStage.Hom 2 3 := CompositionalChainHom.e23

def leftTriple : compositionalStage.Hom 0 3 :=
  compositionalStage.comp (compositionalStage.comp f01 f12) f23

def rightTriple : compositionalStage.Hom 0 3 :=
  compositionalStage.comp f01 (compositionalStage.comp f12 f23)

/-- Composition creates both continuations needed for the next residual. -/
theorem both_bracketed_composites_exist :
    Nonempty (compositionalStage.Hom 0 3) ∧
    Nonempty (compositionalStage.Hom 0 3) := by
  exact ⟨⟨leftTriple⟩, ⟨rightTriple⟩⟩

/-- The two bracketings are genuinely distinct syntax before any coherence law
    is admitted. -/
theorem bracketings_are_distinct_before_coherence :
    leftTriple ≠ rightTriple := by
  intro h
  cases h

/-- The newly expressible verifier-certified residual: all constituent arrows
    and both bracketed composites exist, but their associativity law does not. -/
def chainAssociativityFailure : FailedAssociativity compositionalStage where
  a := 0
  b := 1
  c := 2
  d := 3
  f := f01
  g := f12
  h := f23
  unrealized := by
    intro h
    exact h

/-- The exact omega state representation is already point-separating while the
    independently represented structural layer still admits a coherence
    residual on the same Nat object carrier. -/
theorem exact_extensional_identity_does_not_imply_coherence_terminal :
    ExtensionalOmegaFailureObstruction.PointSeparating
      ExtensionalOmegaFailureObstruction.natBitObserve
      InfiniteBitOmegaFixedPoint.omegaLanguage ∧
    (¬ Nonempty
      (ExtensionalOmegaFailureObstruction.ExtensionalFailure
        ExtensionalOmegaFailureObstruction.natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    (¬ compositionalStage.Law leftTriple rightTriple) := by
  exact ⟨
    ExtensionalOmegaFailureObstruction.exact_nat_omega_is_pointSeparating,
    ExtensionalOmegaFailureObstruction.exact_nat_omega_has_no_extensional_failure,
    by intro h; exact h⟩

/-- The failure-generated repair adds the associativity instance at the law
    layer and nowhere below it. -/
theorem verified_coherence_failure_forces_new_law_only :
    (¬ compositionalStage.Law leftTriple rightTriple) ∧
    (completeLaws compositionalStage
      (generatedAssociativityDemand chainAssociativityFailure)).Law
      leftTriple rightTriple ∧
    ((completeLaws compositionalStage
      (generatedAssociativityDemand chainAssociativityFailure)).Obj = Nat) ∧
    ((completeLaws compositionalStage
      (generatedAssociativityDemand chainAssociativityFailure)).Hom =
      CompositionalChainHom) := by
  have hcore :=
    verified_failure_forces_associativity_as_minimal_law_completion
      chainAssociativityFailure
  exact ⟨hcore.1, hcore.2.1, rfl, rfl⟩

/-- Causal ablation: without the certified failure signal the associativity
    instance remains unavailable. -/
theorem coherence_failure_ablation_blocks_law_genesis :
    ¬ (completeLaws compositionalStage
      (erasedLawDemand compositionalStage)).Law leftTriple rightTriple := by
  exact erasing_failure_signal_erases_associativity_instance
    chainAssociativityFailure

/-- State-level exact identity survives because coherence completion changes no
    state carrier and no verifier observation. -/
theorem point_separation_survives_coherence_genesis :
    ExtensionalOmegaFailureObstruction.PointSeparating
      ExtensionalOmegaFailureObstruction.natBitObserve
      InfiniteBitOmegaFixedPoint.omegaLanguage :=
  ExtensionalOmegaFailureObstruction.exact_nat_omega_is_pointSeparating

/-- The key developmental entailment: the pre-composition language cannot even
    realize the endpoint needed for this residual; composition creates both
    bracketings; only then does a verifier-certified law-level failure become
    expressible, and its least repair is a new coherence law rather than a new
    object or arrow. -/
theorem new_structure_exposes_new_necessity :
    (¬ Nonempty (AtomicChainHom 0 3)) ∧
    Nonempty (compositionalStage.Hom 0 3) ∧
    (¬ compositionalStage.Law leftTriple rightTriple) ∧
    (completeLaws compositionalStage
      (generatedAssociativityDemand chainAssociativityFailure)).Law
      leftTriple rightTriple ∧
    (¬ (completeLaws compositionalStage
      (erasedLawDemand compositionalStage)).Law leftTriple rightTriple) := by
  exact ⟨
    no_three_step_endpoint_before_composition,
    ⟨leftTriple⟩,
    chainAssociativityFailure.unrealized,
    failure_forces_associativity_instance chainAssociativityFailure,
    coherence_failure_ablation_blocks_law_genesis⟩

/-- Integrated post-limit phase transition:

    exact extensional identity
      → no extensional residual
      → composition supplies previously unavailable continuations
      → a new associativity/coherence residual becomes expressible
      → verified failure forces the least new law
      → objects/arrows/state identity remain unchanged.

    This proves one associativity instance, not a globally associative category. -/
theorem post_limit_coherence_phase_transition :
    ExtensionalOmegaFailureObstruction.PointSeparating
      ExtensionalOmegaFailureObstruction.natBitObserve
      InfiniteBitOmegaFixedPoint.omegaLanguage ∧
    (¬ Nonempty
      (ExtensionalOmegaFailureObstruction.ExtensionalFailure
        ExtensionalOmegaFailureObstruction.natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    (¬ Nonempty (AtomicChainHom 0 3)) ∧
    Nonempty (compositionalStage.Hom 0 3) ∧
    (¬ compositionalStage.Law leftTriple rightTriple) ∧
    (completeLaws compositionalStage
      (generatedAssociativityDemand chainAssociativityFailure)).Law
      leftTriple rightTriple ∧
    (¬ (completeLaws compositionalStage
      (erasedLawDemand compositionalStage)).Law leftTriple rightTriple) := by
  exact ⟨
    ExtensionalOmegaFailureObstruction.exact_nat_omega_is_pointSeparating,
    ExtensionalOmegaFailureObstruction.exact_nat_omega_has_no_extensional_failure,
    no_three_step_endpoint_before_composition,
    ⟨leftTriple⟩,
    chainAssociativityFailure.unrealized,
    failure_forces_associativity_instance chainAssociativityFailure,
    coherence_failure_ablation_blocks_law_genesis⟩

#check no_three_step_endpoint_before_composition
#check both_bracketed_composites_exist
#check bracketings_are_distinct_before_coherence
#check exact_extensional_identity_does_not_imply_coherence_terminal
#check verified_coherence_failure_forces_new_law_only
#check coherence_failure_ablation_blocks_law_genesis
#check point_separation_survives_coherence_genesis
#check new_structure_exposes_new_necessity
#check post_limit_coherence_phase_transition

end PostLimitCoherencePhaseTransition
