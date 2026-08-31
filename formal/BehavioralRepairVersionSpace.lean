import VerifierDoesNotDeterminePointwiseRequirement

namespace BehavioralRepairVersionSpace

open VerifierDoesNotDeterminePointwiseRequirement

/-- Inclusion order on repairs. -/
def RepairLE {I : Type} (R₁ R₂ : Repair I) : Prop :=
  ∀ i, R₁ i → R₂ i

/-- An accepted repair is minimal when no strictly smaller accepted repair
    exists. -/
def MinimalAccepted {I : Type}
    (V : RepairVerifier I) (R : Repair I) : Prop :=
  V.accepts R ∧
  ∀ S, V.accepts S → RepairLE S R → RepairLE R S

/-- A repair exposes a future exactly when it contains some capability mapped to
    that future. -/
def RepairReachable {I F : Type}
    (futureOf : I → F) (R : Repair I) : F → Prop :=
  fun f => ∃ i, R i ∧ futureOf i = f

/-- Consequential/behavioural equivalence of repairs: they induce exactly the
    same reachable future set. Literal capability identities may differ. -/
def RepairEquivalent {I F : Type}
    (futureOf : I → F) (R₁ R₂ : Repair I) : Prop :=
  ∀ f, RepairReachable futureOf R₁ f ↔ RepairReachable futureOf R₂ f

/-- Consequential confluence is the exact extra condition needed to recover one
    behavioural developmental outcome from a syntactically nonunique minimal
    repair version space. -/
def ConsequentiallyConfluent {I F : Type}
    (V : RepairVerifier I) (futureOf : I → F) : Prop :=
  ∀ R₁ R₂,
    MinimalAccepted V R₁ → MinimalAccepted V R₂ →
    RepairEquivalent futureOf R₁ R₂

/-- Under consequential confluence, all minimal accepted repairs determine one
    behavioural repair class. -/
theorem minimal_repairs_unique_up_to_consequence
    {I F : Type}
    (V : RepairVerifier I) (futureOf : I → F)
    (hconf : ConsequentiallyConfluent V futureOf)
    {R₁ R₂ : Repair I}
    (h₁ : MinimalAccepted V R₁)
    (h₂ : MinimalAccepted V R₂) :
    RepairEquivalent futureOf R₁ R₂ := by
  exact hconf R₁ R₂ h₁ h₂

/- Witness A: syntactically distinct minimal repairs can collapse to a single
   consequential class when both capabilities realize the same future. -/
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

theorem left_accepted : V.accepts leftRepair := Or.inl trivial
theorem right_accepted : V.accepts rightRepair := Or.inr trivial

theorem left_minimal : MinimalAccepted V leftRepair := by
  constructor
  · exact left_accepted
  · intro S hS hsub i hi
    have hSleft : S .left := by
      rcases hS with hleft | hright
      · exact hleft
      · exact (hsub .right hright).elim
    cases i with
    | left => exact hSleft
    | right => exact hi.elim

theorem right_minimal : MinimalAccepted V rightRepair := by
  constructor
  · exact right_accepted
  · intro S hS hsub i hi
    have hSright : S .right := by
      rcases hS with hleft | hright
      · exact (hsub .left hleft).elim
      · exact hright
    cases i with
    | left => exact hi.elim
    | right => exact hSright

/-- The two minimal repairs are syntactically incomparable. -/
theorem syntactically_distinct :
    (¬ RepairLE leftRepair rightRepair) ∧
    (¬ RepairLE rightRepair leftRepair) := by
  constructor
  · intro h
    exact h .left trivial
  · intro h
    exact h .right trivial

/-- But they expose exactly the same future. -/
theorem behaviorally_equivalent :
    RepairEquivalent futureOf leftRepair rightRepair := by
  intro f
  cases f
  constructor
  · intro _
    exact ⟨.right, trivial, rfl⟩
  · intro _
    exact ⟨.left, trivial, rfl⟩

/-- Every minimal accepted repair exposes the sole future, so the whole version
    space collapses to one behavioural class. -/
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

/- Witness B: verifier acceptance alone does NOT guarantee consequential
   confluence. Two minimal accepted repairs may expose genuinely different
   futures. -/
namespace DivergentWitness

inductive Idx where | left | right
inductive Fut where | alpha | beta deriving DecidableEq

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

theorem left_accepted : V.accepts leftRepair := Or.inl trivial
theorem right_accepted : V.accepts rightRepair := Or.inr trivial

theorem left_minimal : MinimalAccepted V leftRepair := by
  constructor
  · exact left_accepted
  · intro S hS hsub i hi
    have hSleft : S .left := by
      rcases hS with hleft | hright
      · exact hleft
      · exact (hsub .right hright).elim
    cases i with
    | left => exact hSleft
    | right => exact hi.elim

theorem right_minimal : MinimalAccepted V rightRepair := by
  constructor
  · exact right_accepted
  · intro S hS hsub i hi
    have hSright : S .right := by
      rcases hS with hleft | hright
      · exact (hsub .left hleft).elim
      · exact hright
    cases i with
    | left => exact hi.elim
    | right => exact hSright

/-- Alpha is reachable under the left repair. -/
theorem alpha_left : RepairReachable futureOf leftRepair .alpha :=
  ⟨.left, trivial, rfl⟩

/-- Alpha is not reachable under the right repair. -/
theorem alpha_not_right : ¬ RepairReachable futureOf rightRepair .alpha := by
  rintro ⟨i, hi, hif⟩
  cases i with
  | left => exact hi
  | right => cases hif

/-- Therefore the two minimal accepted repairs are not behaviourally
    equivalent. -/
theorem not_behaviorally_equivalent :
    ¬ RepairEquivalent futureOf leftRepair rightRepair := by
  intro h
  exact alpha_not_right ((h .alpha).1 alpha_left)

/-- Generic verifier success therefore does not determine even one behavioural
    next state. -/
theorem verifier_not_consequentially_confluent :
    ¬ ConsequentiallyConfluent V futureOf := by
  intro h
  exact not_behaviorally_equivalent (h leftRepair rightRepair left_minimal right_minimal)

end DivergentWitness

/-- Cycle-6 conclusion: the correct purified object after verifier failure is a
    version space of minimal accepted repairs. Quotienting by future behaviour
    can recover a unique class only when consequential confluence holds; that
    confluence is not implied by verifier acceptance alone. -/
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
