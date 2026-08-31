import BehavioralRepairVersionSpace

namespace AmbiguityGeneratesDistinguishingExperiment

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace

/-- A certified behavioural divergence does not name a preferred repair. It
    carries only a future on which the two repairs make opposite reachability
    predictions. That future is therefore a mechanically available experiment. -/
inductive SeparationWitness {I F : Type}
    (futureOf : I → F) (R₁ R₂ : Repair I) where
  | leftOnly (future : F)
      (leftReachable : RepairReachable futureOf R₁ future)
      (rightUnreachable : ¬ RepairReachable futureOf R₂ future)
  | rightOnly (future : F)
      (rightReachable : RepairReachable futureOf R₂ future)
      (leftUnreachable : ¬ RepairReachable futureOf R₁ future)

/-- The diagnostic question is extracted from the unresolved behavioural
    divergence itself; there is no separate experiment selector. -/
def generatedQuestion {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (w : SeparationWitness futureOf R₁ R₂) : F :=
  match w with
  | .leftOnly f _ _ => f
  | .rightOnly f _ _ => f

/-- A repair survives a certified observation exactly when its prediction about
    the generated future agrees with external truth. The verifier supplies the
    truth value, not the candidate identity. -/
def ConsistentAt {I F : Type}
    (futureOf : I → F) (truth : F → Prop) (f : F) (R : Repair I) : Prop :=
  RepairReachable futureOf R f ↔ truth f

/-- A separation witness guarantees that the generated experiment decides the
    pair: for every possible external outcome, exactly one candidate agrees. -/
theorem generated_question_decides_pair
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (w : SeparationWitness futureOf R₁ R₂)
    (truth : F → Prop) :
    (ConsistentAt futureOf truth (generatedQuestion w) R₁ ∧
      ¬ ConsistentAt futureOf truth (generatedQuestion w) R₂) ∨
    (ConsistentAt futureOf truth (generatedQuestion w) R₂ ∧
      ¬ ConsistentAt futureOf truth (generatedQuestion w) R₁) := by
  cases w with
  | leftOnly f hleft hright =>
      by_cases ht : truth f
      · left
        constructor
        · constructor
          · intro _
            exact ht
          · intro _
            exact hleft
        · intro hcons
          exact hright (hcons.mpr ht)
      · right
        constructor
        · constructor
          · intro hreach
            exact (hright hreach).elim
          · intro htruth
            exact (ht htruth).elim
        · intro hcons
          exact ht (hcons.mp hleft)
  | rightOnly f hright hleft =>
      by_cases ht : truth f
      · right
        constructor
        · constructor
          · intro _
            exact ht
          · intro _
            exact hright
        · intro hcons
          exact hleft (hcons.mpr ht)
      · left
        constructor
        · constructor
          · intro hreach
            exact (hleft hreach).elim
          · intro htruth
            exact (ht htruth).elim
        · intro hcons
          exact ht (hcons.mp hright)

/-- Behaviourally equivalent repairs cannot produce a genuine separation
    witness. This prevents gratuitous experiments after the quotient has already
    collapsed the pair. -/
theorem equivalent_repairs_have_no_separation
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (heq : RepairEquivalent futureOf R₁ R₂) :
    ¬ Nonempty (SeparationWitness futureOf R₁ R₂) := by
  rintro ⟨w⟩
  cases w with
  | leftOnly f hleft hright =>
      exact hright ((heq f).mp hleft)
  | rightOnly f hright hleft =>
      exact hleft ((heq f).mpr hright)

/-- Conversely, every explicit separation witness certifies that the two repairs
    lie in different consequential classes. -/
theorem separation_certifies_non_equivalence
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (w : SeparationWitness futureOf R₁ R₂) :
    ¬ RepairEquivalent futureOf R₁ R₂ := by
  intro heq
  exact equivalent_repairs_have_no_separation heq ⟨w⟩

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness

/-- Cycle 6 already certified this exact behavioural split. Cycle 7 turns its
    witness into the deciding experiment without naming a preferred repair. -/
def divergence : SeparationWitness futureOf leftRepair rightRepair :=
  .leftOnly .alpha alpha_left alpha_not_right

/-- The question is not supplied separately: it is projected from divergence. -/
theorem question_is_generated_from_divergence :
    generatedQuestion divergence = Fut.alpha := rfl

/-- A concrete external world used only to demonstrate resolution. The world
    says alpha is realizable and beta is not; it does not mention repairs. -/
def worldTruth : Fut → Prop
  | .alpha => True
  | .beta => False

/-- Under that external truth, the left repair survives and the right repair is
    eliminated by the question generated from their own disagreement. -/
theorem external_verifier_resolves_without_repair_selector :
    ConsistentAt futureOf worldTruth (generatedQuestion divergence) leftRepair ∧
    ¬ ConsistentAt futureOf worldTruth (generatedQuestion divergence) rightRepair := by
  constructor
  · constructor
    · intro _
      trivial
    · intro _
      exact alpha_left
  · intro h
    exact alpha_not_right (h.mpr trivial)

/-- More strongly, no matter what the external verifier reports at the generated
    question, one and only one of the two behavioural classes survives. -/
theorem generated_experiment_always_shrinks_binary_version_space
    (truth : Fut → Prop) :
    (ConsistentAt futureOf truth (generatedQuestion divergence) leftRepair ∧
      ¬ ConsistentAt futureOf truth (generatedQuestion divergence) rightRepair) ∨
    (ConsistentAt futureOf truth (generatedQuestion divergence) rightRepair ∧
      ¬ ConsistentAt futureOf truth (generatedQuestion divergence) leftRepair) := by
  exact generated_question_decides_pair divergence truth

end Witness

/-- Cycle-7 conclusion: once quotienting leaves more than one behavioural repair
    class, an explicit class-separation witness already contains a deciding
    future. External verification contributes only the outcome; candidate choice
    is a consequence of consistency with that outcome. -/
theorem ambiguity_generates_its_own_deciding_experiment :
    (¬ RepairEquivalent
        BehavioralRepairVersionSpace.DivergentWitness.futureOf
        BehavioralRepairVersionSpace.DivergentWitness.leftRepair
        BehavioralRepairVersionSpace.DivergentWitness.rightRepair) ∧
    Nonempty
      (SeparationWitness
        BehavioralRepairVersionSpace.DivergentWitness.futureOf
        BehavioralRepairVersionSpace.DivergentWitness.leftRepair
        BehavioralRepairVersionSpace.DivergentWitness.rightRepair) ∧
    (∀ truth,
      (ConsistentAt
          BehavioralRepairVersionSpace.DivergentWitness.futureOf truth
          (generatedQuestion Witness.divergence)
          BehavioralRepairVersionSpace.DivergentWitness.leftRepair ∧
        ¬ ConsistentAt
          BehavioralRepairVersionSpace.DivergentWitness.futureOf truth
          (generatedQuestion Witness.divergence)
          BehavioralRepairVersionSpace.DivergentWitness.rightRepair) ∨
      (ConsistentAt
          BehavioralRepairVersionSpace.DivergentWitness.futureOf truth
          (generatedQuestion Witness.divergence)
          BehavioralRepairVersionSpace.DivergentWitness.rightRepair ∧
        ¬ ConsistentAt
          BehavioralRepairVersionSpace.DivergentWitness.futureOf truth
          (generatedQuestion Witness.divergence)
          BehavioralRepairVersionSpace.DivergentWitness.leftRepair)) := by
  constructor
  · exact BehavioralRepairVersionSpace.DivergentWitness.not_behaviorally_equivalent
  constructor
  · exact ⟨Witness.divergence⟩
  · intro truth
    exact Witness.generated_experiment_always_shrinks_binary_version_space truth

#check SeparationWitness
#check generatedQuestion
#check ConsistentAt
#check generated_question_decides_pair
#check equivalent_repairs_have_no_separation
#check separation_certifies_non_equivalence
#check Witness.question_is_generated_from_divergence
#check Witness.external_verifier_resolves_without_repair_selector
#check Witness.generated_experiment_always_shrinks_binary_version_space
#check ambiguity_generates_its_own_deciding_experiment

end AmbiguityGeneratesDistinguishingExperiment
