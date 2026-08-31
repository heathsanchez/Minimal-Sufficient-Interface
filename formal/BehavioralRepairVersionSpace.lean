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
    same reachable future set.  Literal capability identities may differ. -/
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

instance : DecidableEq Idx := by infer_instance

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
    cases i with
    | left =>
      exact hsub .left (by exact trivial)
    | right => exact hi.elim

theorem right_minimal : MinimalAccepted V rightRepair := by
  constructor
  · exact right_accepted
  · intro S hS hsub i hi
    cases i with
    | left => exact hi.elim
    | right =>
      exact hsub .right (by exact trivial)

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
  constructor
  · rintro ⟨i, hi, hif⟩
    cases i with
    | left => exact ⟨.right, trivial, hif⟩
    | right => exact hi.elim
  · rintro ⟨i, hi, hif⟩
    cases i with
    | left => exact hi.elim
    | right => exact ⟨.left, trivial, hif⟩

/-- This version space is consequentially confluent even though syntax is not
    unique. -/
theorem consequentially_confluent :
    ConsequentiallyConfluent V futureOf := by
  intro R₁ R₂ h₁ h₂ f
  have classify : ∀ R, MinimalAccepted V R →
      (RepairLE R leftRepair ∧ RepairLE leftRepair R) ∨
      (RepairLE R rightRepair ∧ RepairLE rightRepair R) := by
    intro R hR
    rcases hR.1 with hl | hr
    · left
      constructor
      · intro i hi
        cases i with
        | left => trivial
        | right =>
          have hLR : RepairLE leftRepair R := fun j hj => by
            cases j with
            | left => exact hl
            | right => exact hj.elim
          have hEq := hR.2 leftRepair left_accepted hLR
          exact (hEq .right hi).elim
      · intro i hi
        cases i with
        | left => exact hl
        | right => exact hi.elim
    · right
      constructor
      · intro i hi
        cases i with
        | left =>
          have hRR : RepairLE rightRepair R := fun j hj => by
            cases j with
            | left => exact hj.elim
            | right => exact hr
          have hEq := hR.2 rightRepair right_accepted hRR
          exact (hEq .left hi).elim
        | right => trivial
      · intro i hi
        cases i with
        | left => exact hi.elim
        | right => exact hr
  rcases classify R₁ h₁ with h1L | h1R <;>
  rcases classify R₂ h₂ with h2L | h2R
  · constructor <;> rintro ⟨i, hi, hif⟩ <;>
      exact ⟨i, (if h : R₂ i then h else by
        exfalso
        have := h2L.2 i (h1L.1 i hi)
        exact h this), hif⟩
  · exact behaviorally_equivalent f
  · exact (behaviorally_equivalent f).symm
  · constructor <;> rintro ⟨i, hi, hif⟩ <;>
      exact ⟨i, (if h : R₂ i then h else by
        exfalso
        have := h2R.2 i (h1R.1 i hi)
        exact h this), hif⟩

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
    cases i with
    | left => exact hsub .left trivial
    | right => exact hi.elim

theorem right_minimal : MinimalAccepted V rightRepair := by
  constructor
  · exact right_accepted
  · intro S hS hsub i hi
    cases i with
    | left => exact hi.elim
    | right => exact hsub .right trivial

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
    version space of minimal accepted repairs.  Quotienting by future behaviour
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
#check DivergentWitness.not_behaviorally_equivalent
#check DivergentWitness.verifier_not_consequentially_confluent
#check version_space_quotient_is_the_correct_boundary

end BehavioralRepairVersionSpace
