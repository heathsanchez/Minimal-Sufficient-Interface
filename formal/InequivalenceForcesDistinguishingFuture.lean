import AmbiguityGeneratesDistinguishingExperiment

namespace InequivalenceForcesDistinguishingFuture

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open AmbiguityGeneratesDistinguishingExperiment

/-- Bare behavioural inequivalence already entails the existence of a future
    separating the two repairs. No separator is supplied as additional data.

    This theorem is deliberately classical: it removes the logical primitive
    `SeparationWitness`, but does not yet claim an executable separator search. -/
theorem inequivalence_has_separation
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) :
    Nonempty (SeparationWitness futureOf R₁ R₂) := by
  classical
  apply Classical.byContradiction
  intro hnone
  apply hneq
  intro f
  constructor
  · intro h₁
    by_cases h₂ : RepairReachable futureOf R₂ f
    · exact h₂
    · exact False.elim (hnone ⟨.leftOnly f h₁ h₂⟩)
  · intro h₂
    by_cases h₁ : RepairReachable futureOf R₁ f
    · exact h₁
    · exact False.elim (hnone ⟨.rightOnly f h₂ h₁⟩)

/-- A separator can therefore be chosen from inequivalence itself. The use of
    `Classical.choice` is explicit so the remaining computational boundary is
    visible rather than hidden. -/
noncomputable def separatorFromInequivalence
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) :
    SeparationWitness futureOf R₁ R₂ :=
  Classical.choice (inequivalence_has_separation hneq)

/-- The next question is now a function of bare behavioural inequivalence,
    rather than an independently supplied separator witness. -/
noncomputable def questionFromInequivalence
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) : F :=
  generatedQuestion (separatorFromInequivalence hneq)

/-- Whatever truth the external verifier returns, the question selected from
    bare inequivalence decides the binary repair pair. -/
theorem inequivalence_generated_question_decides_pair
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂)
    (truth : F → Prop) :
    (ConsistentAt futureOf truth (questionFromInequivalence hneq) R₁ ∧
      ¬ ConsistentAt futureOf truth (questionFromInequivalence hneq) R₂) ∨
    (ConsistentAt futureOf truth (questionFromInequivalence hneq) R₂ ∧
      ¬ ConsistentAt futureOf truth (questionFromInequivalence hneq) R₁) := by
  exact generated_question_decides_pair (separatorFromInequivalence hneq) truth

/-- The logical boundary is exact: behavioural equivalence rules out separators,
    while inequivalence forces one. -/
theorem separation_exists_iff_inequivalent
    {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I} :
    Nonempty (SeparationWitness futureOf R₁ R₂) ↔
      ¬ RepairEquivalent futureOf R₁ R₂ := by
  constructor
  · rintro ⟨w⟩
    exact separation_certifies_non_equivalence w
  · exact inequivalence_has_separation

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness

/-- In the cycle-6 divergent version space, even the separator witness is no
    longer supplied to the experiment generator. -/
noncomputable def generatedFromBareInequivalence : Fut :=
  questionFromInequivalence not_behaviorally_equivalent

/-- The generated question necessarily decides the two minimal repair classes
    for every possible verifier truth assignment. -/
theorem bare_inequivalence_always_generates_a_decider
    (truth : Fut → Prop) :
    (ConsistentAt futureOf truth generatedFromBareInequivalence leftRepair ∧
      ¬ ConsistentAt futureOf truth generatedFromBareInequivalence rightRepair) ∨
    (ConsistentAt futureOf truth generatedFromBareInequivalence rightRepair ∧
      ¬ ConsistentAt futureOf truth generatedFromBareInequivalence leftRepair) := by
  exact inequivalence_generated_question_decides_pair
    not_behaviorally_equivalent truth

end Witness

/-- Cycle-8 conclusion: at the logical level, unresolved behavioural
    inequivalence is sufficient to generate a deciding experiment without an
    extra separator input. The remaining supplied ingredient is classical
    choice; executable finite extraction is the next boundary. -/
theorem bare_ambiguity_logically_forces_deciding_experiment :
    ∀ {I F : Type} {futureOf : I → F} {R₁ R₂ : Repair I}
      (hneq : ¬ RepairEquivalent futureOf R₁ R₂),
      ∀ truth : F → Prop,
        (ConsistentAt futureOf truth
            (questionFromInequivalence hneq) R₁ ∧
          ¬ ConsistentAt futureOf truth
            (questionFromInequivalence hneq) R₂) ∨
        (ConsistentAt futureOf truth
            (questionFromInequivalence hneq) R₂ ∧
          ¬ ConsistentAt futureOf truth
            (questionFromInequivalence hneq) R₁) := by
  intro I F futureOf R₁ R₂ hneq truth
  exact inequivalence_generated_question_decides_pair hneq truth

#check inequivalence_has_separation
#check separatorFromInequivalence
#check questionFromInequivalence
#check inequivalence_generated_question_decides_pair
#check separation_exists_iff_inequivalent
#check Witness.generatedFromBareInequivalence
#check Witness.bare_inequivalence_always_generates_a_decider
#check bare_ambiguity_logically_forces_deciding_experiment

end InequivalenceForcesDistinguishingFuture
