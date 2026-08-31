import VerifierDoesNotDeterminePointwiseRequirement

namespace BehavioralRepairVersionSpace

open VerifierDoesNotDeterminePointwiseRequirement

def RepairLE {I : Type} (R₁ R₂ : Repair I) : Prop :=
  ∀ i, R₁ i → R₂ i

def MinimalAccepted {I : Type}
    (V : RepairVerifier I) (R : Repair I) : Prop :=
  V.accepts R ∧
  ∀ S, V.accepts S → RepairLE S R → RepairLE R S

def RepairReachable {I F : Type}
    (futureOf : I → F) (R : Repair I) : F → Prop :=
  fun f => ∃ i, R i ∧ futureOf i = f

def RepairEquivalent {I F : Type}
    (futureOf : I → F) (R₁ R₂ : Repair I) : Prop :=
  ∀ f, RepairReachable futureOf R₁ f ↔ RepairReachable futureOf R₂ f

def ConsequentiallyConfluent {I F : Type}
    (V : RepairVerifier I) (futureOf : I → F) : Prop :=
  ∀ R₁ R₂,
    MinimalAccepted V R₁ → MinimalAccepted V R₂ →
    RepairEquivalent futureOf R₁ R₂

theorem minimal_repairs_unique_up_to_consequence
    {I F : Type}
    (V : RepairVerifier I) (futureOf : I → F)
    (hconf : ConsequentiallyConfluent V futureOf)
    {R₁ R₂ : Repair I}
    (h₁ : MinimalAccepted V R₁)
    (h₂ : MinimalAccepted V R₂) :
    RepairEquivalent futureOf R₁ R₂ := by
  exact hconf R₁ R₂ h₁ h₂

namespace EquivalentWitness

inductive Idx where | left | right
inductive Fut where | goal

def V : RepairVerifier Idx where
  accepts := fun R => R .left ∨ R .right

def leftRepair : Repair Idx
  | .left => True
  | .right => False

def rightRepair : Repair Idx
  | .left => False
  | .right => True

def futureOf : Idx → Fut := fun _ => .goal

theorem left_accepted : V.accepts leftRepair := Or.inl True.intro
theorem right_accepted : V.accepts rightRepair := Or.inr True.intro

theorem left_minimal : MinimalAccepted V leftRepair := by
  constructor
  · exact left_accepted
  · intro S hS hsub
    intro i hi
    cases i with
    | left =>
        show S .left
        rcases hS with hleft | hright
        · exact hleft
        · have hf : False := hsub .right hright
          exact False.elim hf
    | right =>
        exact False.elim hi

theorem right_minimal : MinimalAccepted V rightRepair := by
  constructor
  · exact right_accepted
  · intro S hS hsub
    intro i hi
    cases i with
    | left =>
        exact False.elim hi
    | right =>
        show S .right
        rcases hS with hleft | hright
        · have hf : False := hsub .left hleft
          exact False.elim hf
        · exact hright

theorem syntactically_distinct :
    (¬ RepairLE leftRepair rightRepair) ∧
    (¬ RepairLE rightRepair leftRepair) := by
  constructor
  · intro h
    exact h .left True.intro
  · intro h
    exact h .right True.intro

theorem behaviorally_equivalent :
    RepairEquivalent futureOf leftRepair rightRepair := by
  intro f
  cases f
  constructor
  · intro _
    exact ⟨.right, True.intro, rfl⟩
  · intro _
    exact ⟨.left, True.intro, rfl⟩

theorem consequentially_confluent :
    ConsequentiallyConfluent V futureOf := by
  intro R₁ R₂ h₁ h₂ f
  cases f
  constructor
  · intro _
    rcases h₂.1 with hleft | hright
    · exact ⟨.left, hleft, rfl⟩
    · exact ⟨.right, hright, rfl⟩
  · intro _
    rcases h₁.1 with hleft | hright
    · exact ⟨.left, hleft, rfl⟩
    · exact ⟨.right, hright, rfl⟩

end EquivalentWitness

namespace DivergentWitness

inductive Idx where | left | right
inductive Fut where | alpha | beta

def V : RepairVerifier Idx where
  accepts := fun R => R .left ∨ R .right

def leftRepair : Repair Idx
  | .left => True
  | .right => False

def rightRepair : Repair Idx
  | .left => False
  | .right => True

def futureOf : Idx → Fut
  | .left => .alpha
  | .right => .beta

theorem left_accepted : V.accepts leftRepair := Or.inl True.intro
theorem right_accepted : V.accepts rightRepair := Or.inr True.intro

theorem left_minimal : MinimalAccepted V leftRepair := by
  constructor
  · exact left_accepted
  · intro S hS hsub
    intro i hi
    cases i with
    | left =>
        show S .left
        rcases hS with hleft | hright
        · exact hleft
        · have hf : False := hsub .right hright
          exact False.elim hf
    | right =>
        exact False.elim hi

theorem right_minimal : MinimalAccepted V rightRepair := by
  constructor
  · exact right_accepted
  · intro S hS hsub
    intro i hi
    cases i with
    | left =>
        exact False.elim hi
    | right =>
        show S .right
        rcases hS with hleft | hright
        · have hf : False := hsub .left hleft
          exact False.elim hf
        · exact hright

theorem alpha_left : RepairReachable futureOf leftRepair .alpha :=
  ⟨.left, True.intro, rfl⟩

theorem alpha_not_right : ¬ RepairReachable futureOf rightRepair .alpha := by
  rintro ⟨i, hi, hif⟩
  cases i with
  | left =>
      exact False.elim hi
  | right =>
      cases hif

theorem not_behaviorally_equivalent :
    ¬ RepairEquivalent futureOf leftRepair rightRepair := by
  intro h
  exact alpha_not_right ((h .alpha).1 alpha_left)

theorem verifier_not_consequentially_confluent :
    ¬ ConsequentiallyConfluent V futureOf := by
  intro h
  exact not_behaviorally_equivalent
    (h leftRepair rightRepair left_minimal right_minimal)

end DivergentWitness

theorem version_space_quotient_is_the_correct_boundary :
    (∃ (I F : Type) (V : RepairVerifier I) (futureOf : I → F)
        (R₁ R₂ : Repair I),
      MinimalAccepted V R₁ ∧ MinimalAccepted V R₂ ∧
      (¬ RepairLE R₁ R₂) ∧ (¬ RepairLE R₂ R₁) ∧
      RepairEquivalent futureOf R₁ R₂) ∧
    (∃ (I F : Type) (V : RepairVerifier I) (futureOf : I → F),
      ¬ ConsequentiallyConfluent V futureOf) := by
  constructor
  · exact ⟨EquivalentWitness.Idx, EquivalentWitness.Fut,
      EquivalentWitness.V, EquivalentWitness.futureOf,
      EquivalentWitness.leftRepair, EquivalentWitness.rightRepair,
      EquivalentWitness.left_minimal, EquivalentWitness.right_minimal,
      EquivalentWitness.syntactically_distinct.1,
      EquivalentWitness.syntactically_distinct.2,
      EquivalentWitness.behaviorally_equivalent⟩
  · exact ⟨DivergentWitness.Idx, DivergentWitness.Fut,
      DivergentWitness.V, DivergentWitness.futureOf,
      DivergentWitness.verifier_not_consequentially_confluent⟩

#check MinimalAccepted
#check RepairEquivalent
#check ConsequentiallyConfluent
#check minimal_repairs_unique_up_to_consequence
#check EquivalentWitness.behaviorally_equivalent
#check EquivalentWitness.consequentially_confluent
#check DivergentWitness.not_behaviorally_equivalent
#check DivergentWitness.verifier_not_consequentially_confluent
#check version_space_quotient_is_the_correct_boundary

end BehavioralRepairVersionSpace
