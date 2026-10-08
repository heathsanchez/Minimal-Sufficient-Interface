import VerifiedDevelopmentCore

/-!
Executable finite *illustration*, not a universal expressiveness theorem.
Unit actions avoid distracting operational assumptions.
-/

namespace VerifiedDevelopmentExample

open VerifiedDevelopmentCore
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
  scopeLE := fun _ _ => True
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


/-! A genuinely non-identity continuation: `true` exposes a hidden bit. -/

/-- Composition is Boolean OR, with `false` the identity action. -/
def revealAction : ActionMonoid Bool (Bool × Bool) where
  one := false
  mul := fun a b => a || b
  act := fun m x => if m then (x.1, x.1) else x
  one_mul := by intro a; cases a <;> rfl
  mul_one := by intro a; cases a <;> rfl
  mul_assoc := by intro a b c; cases a <;> cases b <;> cases c <;> rfl
  one_act := by intro x; rfl
  mul_act := by
    intro a b x
    rcases x with ⟨first, second⟩
    cases a <;> cases b <;> cases first <;> cases second <;> rfl

/-- The original stage protects only the identity; the new one admits `true`. -/
def initialStage : Stage revealAction where
  allow := fun m => m = false
  one_allow := rfl
  mul_allow := by
    intro g f hg hf
    subst g
    subst f
    rfl

def expandedStage : Stage revealAction where
  allow := fun _ => True
  one_allow := trivial
  mul_allow := by intro g f hg hf; trivial

def before : Bool × Bool := (false, false)
def after : Bool × Bool := (true, false)
def visible (x : Bool × Bool) : Bool := x.2
def visibleEq (x y : Bool × Bool) : Prop := visible x = visible y

theorem original_stage_merges :
    BehEqAt revealAction initialStage visible before after := by
  intro m hm
  have h : m = false := hm
  subst m
  rfl

theorem identity_does_not_separate :
    visible (revealAction.act false before) =
      visible (revealAction.act false after) := by
  rfl

theorem actual_action_separates :
    visible (revealAction.act true before) ≠
      visible (revealAction.act true after) := by
  decide

/-- At the original stage this pair is still retained. -/
theorem original_refinement_still_merges :
    Refine revealAction initialStage visibleEq visible before after := by
  refine ⟨rfl, ?_⟩
  intro m hm
  have h : m = false := hm
  subst m
  rfl

def revealAdmission : ScopeAdmission Unit Bool where
  scopeLE := fun _ _ => True
  allows := fun _ _ => True
  monotone := by intro σ τ _ m _; trivial

def revealBank : CertBank revealAction Unit Unit Bool where
  admitted := revealAdmission
  obs := visible
  claim := fun _ => .separate before after
  scope := fun _ => ()
  check := fun _ => True
  depends := fun _ _ => False
  checker_sound := by
    intro r _
    cases r
    change ∃ m : Bool, True ∧
      visible (revealAction.act m before) ≠
      visible (revealAction.act m after)
    exact ⟨true, trivial, actual_action_separates⟩

theorem reveal_record_valid :
    Valid revealBank.check revealBank.depends () := by
  apply Valid.admit ()
  · trivial
  · intro p hp
    exact False.elim hp

theorem reveal_separator_certified :
    CertifiedSeparator revealAction revealBank () before after := by
  exact ⟨(), reveal_record_valid, rfl, trivial⟩

theorem reveal_error :
    ErrorResidual revealAction revealBank visibleEq () before after := by
  exact ⟨rfl, reveal_separator_certified⟩

/-- The scope bridge fails for the old stage, so that stage is not refined. -/
theorem scope_not_in_original_stage :
    ¬ (∀ m, revealBank.admitted.allows () m →
      initialStage.allow m) := by
  intro h
  have bad : (true : Bool) = false := h true trivial
  cases bad

/-- Only after admitting the revealing action is the split warranted. -/
theorem nontrivial_certified_split :
    visibleEq before after ∧
      ¬ Refine revealAction expandedStage visibleEq visible before after := by
  apply certified_error_forces_split revealAction expandedStage
    revealBank visibleEq
  · intro m hm
    trivial
  · exact reveal_error

end VerifiedDevelopmentExample
