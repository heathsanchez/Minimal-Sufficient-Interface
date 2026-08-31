import GenericResidualCompletion
import ResidualGeneratesNextObligation
import ConsequenceDeterminesSelection

namespace RecursiveConsequenceSelectedDevelopment

open GenericResidualCompletion
open ResidualGeneratesNextObligation
open ConsequenceDeterminesSelection

/-- A tiny base language with two already-realized anchors and one missing
    capability.  The names are used only to make the deciding experiment
    finite and inspectable. -/
inductive BaseObligation where
  | anchorA
  | anchorB
  | missing
  deriving DecidableEq

/-- Only the two anchors are initially realized. -/
def baseState : CapabilityState where
  Obligation := BaseObligation
  Realize
    | .anchorA => Unit
    | .anchorB => Unit
    | .missing => Empty

/-- The lower verifier certifies exactly the missing base capability. -/
def lowerResidual : VerifiedResidual baseState where
  target := .missing
  unrealized := by
    intro h
    rcases h with ⟨h⟩
    exact Empty.elim h

abbrev repairedBase : CapabilityState :=
  complete baseState (generatedDemand lowerResidual)

def anchorAWitness : baseState.Realize .anchorA := ()
def anchorBWitness : baseState.Realize .anchorB := ()

/-- After lower repair, two distinct higher candidates become constructible by
    combining the generated target token with either retained anchor. -/
def higherCandidate : Bool → NextObligation repairedBase
  | false => emergentHigherObligation lowerResidual anchorAWitness
  | true  => emergentHigherObligation lowerResidual anchorBWitness

/-- The verifier consequence sees anonymous candidate indices.  Exactly the
    candidate associated with anchorB passes this consequence. -/
def verifierConsequence : Bool → Bool
  | false => false
  | true => true

/-- A contrasting verifier consequence selects the other anonymous candidate. -/
def alternateConsequence : Bool → Bool
  | false => true
  | true => false

/-- The candidate pool is fixed independently of either consequence. -/
def candidatePool : List Bool := [false, true]

 theorem verifierConsequence_unique :
    UniqueSeparator verifierConsequence true := by
  constructor
  · rfl
  · intro x hx
    cases x <;> simp [verifierConsequence] at hx ⊢

 theorem alternateConsequence_unique :
    UniqueSeparator alternateConsequence false := by
  constructor
  · rfl
  · intro x hx
    cases x <;> simp [alternateConsequence] at hx ⊢

/-- The target index is recovered from consequence rather than supplied as an
    identity parameter. -/
theorem verifier_selects_emergent_target :
    selectByConsequence verifierConsequence candidatePool = some true := by
  exact unique_separator_selected verifierConsequence candidatePool true
    (by simp [candidatePool]) verifierConsequence_unique

/-- Changing only verifier consequence changes which generated higher
    obligation is selected. -/
theorem changing_verifier_consequence_changes_target :
    selectByConsequence verifierConsequence candidatePool = some true ∧
    selectByConsequence alternateConsequence candidatePool = some false := by
  exact changing_consequence_changes_selected_identity candidatePool true false
    verifierConsequence alternateConsequence
    (by simp [candidatePool]) (by simp [candidatePool])
    verifierConsequence_unique alternateConsequence_unique

/-- A concrete chosen index extracted from the consequence selector.  The
    default is observationally irrelevant below because selection is proved to
    succeed. -/
def chosenIndex : Bool :=
  (selectByConsequence verifierConsequence candidatePool).getD false

 theorem chosenIndex_is_consequence_selected : chosenIndex = true := by
  simp [chosenIndex, verifier_selects_emergent_target]

abbrev higherState : CapabilityState := nextState repairedBase

/-- Every generated higher candidate is currently unrealized; therefore the
    consequence-selected candidate carries a verifier certificate. -/
def residualAt (i : Bool) : VerifiedResidual higherState where
  target := higherCandidate i
  unrealized := by
    intro h
    rcases h with ⟨h⟩
    exact Empty.elim h

/-- Crucially, this residual's target is not named directly: it is the
    obligation indexed by the consequence-selected output. -/
def selectedHigherResidual : VerifiedResidual higherState :=
  residualAt chosenIndex

 theorem selected_residual_target_is_verifier_determined :
    selectedHigherResidual.target = higherCandidate true := by
  simp [selectedHigherResidual, chosenIndex_is_consequence_selected]

/-- The unchanged semantic-kind-blind completion repairs the target selected by
    verifier consequence. -/
theorem same_generic_operator_repairs_selected_target :
    Nonempty
      ((complete higherState (generatedDemand selectedHigherResidual)).Realize
        selectedHigherResidual.target) := by
  exact failure_forces_target_realization selectedHigherResidual

/-- Removing consequence removes target selection altogether. -/
theorem consequence_ablation_blocks_target_selection :
    selectByConsequence (fun _ : Bool => false) candidatePool = none := by
  exact no_consequence_no_selection candidatePool

/-- Removing the lower residual still prevents the missing target from entering
    the next-stage language, so consequence cannot substitute for the
    developmental prerequisite. -/
theorem lower_residual_ablation_blocks_candidate_genesis :
    ¬ Nonempty
      (TargetAnchored
        (complete baseState (erasedDemand baseState))
        lowerResidual.target BaseObligation.anchorB) := by
  exact lower_failure_ablation_blocks_next_obligation_genesis lowerResidual

/-- End-to-end deciding theorem.

    1. the lower residual is necessary to make the next candidate family
       inhabitable;
    2. after repair, multiple higher obligations are available;
    3. verifier consequence, not candidate identity, selects the higher target;
    4. changing consequence changes the selected target;
    5. the same generic completion repairs that target;
    6. ablating either the lower residual or the consequence breaks the chain.

    The Bool-sized candidate index and token-pair grammar are deliberately
    supplied.  Therefore this proves consequence-selected targeting inside a
    recursively generated residual address space, not unrestricted invention of
    arbitrary ontologies. -/
theorem recursive_consequence_selected_development :
    (¬ Nonempty
      (TargetAnchored baseState lowerResidual.target BaseObligation.anchorB)) ∧
    selectByConsequence verifierConsequence candidatePool = some true ∧
    selectedHigherResidual.target = higherCandidate true ∧
    Nonempty
      ((complete higherState (generatedDemand selectedHigherResidual)).Realize
        selectedHigherResidual.target) ∧
    selectByConsequence (fun _ : Bool => false) candidatePool = none ∧
    (¬ Nonempty
      (TargetAnchored
        (complete baseState (erasedDemand baseState))
        lowerResidual.target BaseObligation.anchorB)) := by
  refine ⟨target_cannot_generate_next_obligation_before_repair lowerResidual,
    verifier_selects_emergent_target,
    selected_residual_target_is_verifier_determined,
    same_generic_operator_repairs_selected_target,
    consequence_ablation_blocks_target_selection,
    lower_residual_ablation_blocks_candidate_genesis⟩

#check verifier_selects_emergent_target
#check changing_verifier_consequence_changes_target
#check chosenIndex_is_consequence_selected
#check selected_residual_target_is_verifier_determined
#check same_generic_operator_repairs_selected_target
#check consequence_ablation_blocks_target_selection
#check lower_residual_ablation_blocks_candidate_genesis
#check recursive_consequence_selected_development

end RecursiveConsequenceSelectedDevelopment
