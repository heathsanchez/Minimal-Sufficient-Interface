import InequivalenceForcesDistinguishingFuture

namespace FiniteExecutableDistinguishingFuture

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open AmbiguityGeneratesDistinguishingExperiment
open InequivalenceForcesDistinguishingFuture

/-- A certified finite future interface supplies a finite complete question basis
    and a Boolean predictor proved faithful to semantic reachability. The search
    algorithm below is executable once this interface is supplied. -/
structure CertifiedFiniteFutureInterface (I F : Type)
    (futureOf : I → F) where
  questions : List F
  covers : ∀ f : F, f ∈ questions
  predict : Repair I → F → Bool
  faithful : ∀ (R : Repair I) (f : F),
    predict R f = true ↔ RepairReachable futureOf R f

/-- Deterministic first-difference scan. -/
def firstDifference {F : Type}
    (left right : F → Bool) : List F → Option F
  | [] => none
  | f :: fs =>
      if left f = right f then firstDifference left right fs else some f

theorem firstDifference_sound
    {F : Type} (left right : F → Bool) (qs : List F) (f : F)
    (h : firstDifference left right qs = some f) :
    f ∈ qs ∧ left f ≠ right f := by
  induction qs with
  | nil => simp [firstDifference] at h
  | cons a as ih =>
      by_cases heq : left a = right a
      · simp [firstDifference, heq] at h
        rcases ih h with ⟨hmem, hdiff⟩
        exact ⟨List.mem_cons_of_mem a hmem, hdiff⟩
      · simp [firstDifference, heq] at h
        subst f
        exact ⟨List.mem_cons_self, heq⟩

theorem firstDifference_complete
    {F : Type} (left right : F → Bool) (qs : List F)
    (h : ∃ f, f ∈ qs ∧ left f ≠ right f) :
    ∃ f, firstDifference left right qs = some f := by
  induction qs with
  | nil =>
      rcases h with ⟨f, hmem, _⟩
      simp at hmem
  | cons a as ih =>
      by_cases heq : left a = right a
      · have htail : ∃ f, f ∈ as ∧ left f ≠ right f := by
          rcases h with ⟨f, hmem, hdiff⟩
          rcases List.mem_cons.mp hmem with hfa | hfas
          · subst f
            exact (hdiff heq).elim
          · exact ⟨f, hfas, hdiff⟩
        rcases ih htail with ⟨f, hf⟩
        exact ⟨f, by simp [firstDifference, heq, hf]⟩
      · exact ⟨a, by simp [firstDifference, heq]⟩

def firstDistinguishingFuture
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R₁ R₂ : Repair I) : Option F :=
  firstDifference (B.predict R₁) (B.predict R₂) B.questions

theorem inequivalence_implies_finite_prediction_difference
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) :
    ∃ f, f ∈ B.questions ∧ B.predict R₁ f ≠ B.predict R₂ f := by
  rcases inequivalence_has_separation hneq with ⟨w⟩
  cases w with
  | leftOnly f hleft hright =>
      have hp₁ : B.predict R₁ f = true := (B.faithful R₁ f).2 hleft
      have hp₂ : B.predict R₂ f ≠ true := by
        intro ht
        exact hright ((B.faithful R₂ f).1 ht)
      have hdiff : B.predict R₁ f ≠ B.predict R₂ f := by
        intro heq
        apply hp₂
        rw [← heq]
        exact hp₁
      exact ⟨f, B.covers f, hdiff⟩
  | rightOnly f hright hleft =>
      have hp₂ : B.predict R₂ f = true := (B.faithful R₂ f).2 hright
      have hp₁ : B.predict R₁ f ≠ true := by
        intro ht
        exact hleft ((B.faithful R₁ f).1 ht)
      have hdiff : B.predict R₁ f ≠ B.predict R₂ f := by
        intro heq
        apply hp₁
        rw [heq]
        exact hp₂
      exact ⟨f, B.covers f, hdiff⟩

theorem executable_search_finds_separator
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) :
    ∃ f,
      firstDistinguishingFuture B R₁ R₂ = some f ∧
      B.predict R₁ f ≠ B.predict R₂ f := by
  have hex := inequivalence_implies_finite_prediction_difference B hneq
  rcases firstDifference_complete
      (B.predict R₁) (B.predict R₂) B.questions hex with ⟨f, hfind⟩
  have hs := firstDifference_sound
      (B.predict R₁) (B.predict R₂) B.questions f hfind
  exact ⟨f, hfind, hs.2⟩

theorem unequal_predictions_exactly_one_matches
    {a b outcome : Bool} (hneq : a ≠ b) :
    (a = outcome ∧ b ≠ outcome) ∨
    (b = outcome ∧ a ≠ outcome) := by
  cases a <;> cases b <;> cases outcome <;> simp_all

theorem executable_question_decides_pair
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    {R₁ R₂ : Repair I} {f : F}
    (hfind : firstDistinguishingFuture B R₁ R₂ = some f)
    (outcome : Bool) :
    (B.predict R₁ f = outcome ∧ B.predict R₂ f ≠ outcome) ∨
    (B.predict R₂ f = outcome ∧ B.predict R₁ f ≠ outcome) := by
  have hdiff := (firstDifference_sound
    (B.predict R₁) (B.predict R₂) B.questions f hfind).2
  exact unequal_predictions_exactly_one_matches hdiff

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness

/-- The logical repair representation is Prop-valued. Constructing a Boolean
    predictor for every arbitrary Prop-valued repair therefore requires a
    decidability choice in this concrete witness. This is intentionally marked
    noncomputable; the generic `firstDistinguishingFuture` itself remains a
    deterministic executable scan once an executable predictor is supplied. -/
noncomputable def basis : CertifiedFiniteFutureInterface Idx Fut futureOf := by
  classical
  refine {
    questions := [.alpha, .beta]
    covers := ?_
    predict := fun R f =>
      match f with
      | .alpha => if R .left then true else false
      | .beta => if R .right then true else false
    faithful := ?_
  }
  · intro f
    cases f <;> simp
  · intro R f
    cases f with
    | alpha =>
        constructor
        · intro h
          by_cases hr : R .left
          · exact ⟨.left, hr, rfl⟩
          · simp [hr] at h
        · rintro ⟨i, hi, hif⟩
          cases i with
          | left => simp [hi]
          | right => cases hif
    | beta =>
        constructor
        · intro h
          by_cases hr : R .right
          · exact ⟨.right, hr, rfl⟩
          · simp [hr] at h
        · rintro ⟨i, hi, hif⟩
          cases i with
          | left => cases hif
          | right => simp [hi]

theorem computes_alpha :
    firstDistinguishingFuture basis leftRepair rightRepair = some .alpha := by
  classical
  simp [firstDistinguishingFuture, basis, firstDifference, leftRepair, rightRepair]

theorem computed_question_always_decides (outcome : Bool) :
    (basis.predict leftRepair .alpha = outcome ∧
      basis.predict rightRepair .alpha ≠ outcome) ∨
    (basis.predict rightRepair .alpha = outcome ∧
      basis.predict leftRepair .alpha ≠ outcome) := by
  exact executable_question_decides_pair basis computes_alpha outcome

end Witness

theorem finite_verified_ambiguity_has_executable_decider :
    ∀ {I F : Type} {futureOf : I → F}
      (B : CertifiedFiniteFutureInterface I F futureOf)
      {R₁ R₂ : Repair I},
      (¬ RepairEquivalent futureOf R₁ R₂) →
      ∃ f,
        firstDistinguishingFuture B R₁ R₂ = some f ∧
        B.predict R₁ f ≠ B.predict R₂ f := by
  intro I F futureOf B R₁ R₂ hneq
  exact executable_search_finds_separator B hneq

#check CertifiedFiniteFutureInterface
#check firstDifference
#check firstDifference_sound
#check firstDifference_complete
#check firstDistinguishingFuture
#check executable_search_finds_separator
#check executable_question_decides_pair
#check Witness.computes_alpha
#check Witness.computed_question_always_decides
#check finite_verified_ambiguity_has_executable_decider

end FiniteExecutableDistinguishingFuture
