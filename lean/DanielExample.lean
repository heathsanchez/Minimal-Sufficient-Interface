import DanielCore

/-!
Executable finite *illustration*, not a universal expressiveness theorem.
Unit actions avoid distracting operational assumptions.
-/

namespace DanielExample

open DanielCore
open ScopedCertificates

def toyAction : ActionMonoid Unit (Bool × Bool) where
  one := ()
  mul := fun _ _ => ()
  act := fun _ x => x
  one_mul := by intro a; cases a; rfl
  mul_one := by intro a; cases a; rfl
  mul_assoc := by intro a b c; rfl
  one_act := by intro x; rfl
  mul_act := by intro a b x; rfl

def toyStage : Stage toyAction where
  allow := fun _ => True
  one_allow := trivial
  mul_allow := by intro g f _ _; trivial

def p : Bool × Bool := (true, false)
def q : Bool × Bool := (true, true)
def oldObs (x : Bool × Bool) : Bool := x.1
def newObs (x : Bool × Bool) : Bool := x.2
def oldRelation (x y : Bool × Bool) : Prop := oldObs x = oldObs y

theorem old_states_merged : oldRelation p q := by rfl

theorem old_futures_agree : BehEqAt toyAction toyStage oldObs p q := by
  intro m _
  cases m
  rfl

def toyAdmission : ScopeAdmission Unit Unit where
  extendsScope := fun _ _ => True
  allows := fun _ _ => True
  monotone := by intro σ τ _ m _; trivial

/-- One checked record asserts the second-coordinate separator, at unit scope. -/
def toyBank : CertBank toyAction Unit Unit Bool where
  admitted := toyAdmission
  obs := newObs
  claim := fun _ => .separate p q
  scope := fun _ => ()
  check := fun _ => True
  depends := fun _ _ => False
  checker_sound := by
    intro r _
    cases r
    change ∃ m : Unit, True ∧ (false : Bool) ≠ true
    exact ⟨(), trivial, by decide⟩

theorem toy_record_valid : Valid toyBank.check toyBank.depends () := by
  apply Valid.admit ()
  · trivial
  · intro dep h
    exact False.elim h

theorem toy_separator_certified :
    CertifiedSeparator toyAction toyBank () p q := by
  exact ⟨(), toy_record_valid, rfl, trivial⟩

theorem toy_error_residual :
    ErrorResidual toyAction toyBank oldRelation () p q := by
  exact ⟨old_states_merged, toy_separator_certified⟩

/-- End-to-end: certificate ⇒ verified error residual ⇒ required split. -/
theorem toy_certified_split :
    oldRelation p q ∧
      ¬ Refine toyAction toyStage oldRelation newObs p q := by
  exact certified_error_forces_split toyAction toyStage toyBank oldRelation
    (by intro m hm; trivial) toy_error_residual

end DanielExample
