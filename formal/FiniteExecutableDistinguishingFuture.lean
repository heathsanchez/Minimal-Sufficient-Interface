import InequivalenceForcesDistinguishingFuture

namespace FiniteExecutableDistinguishingFuture

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open AmbiguityGeneratesDistinguishingExperiment
open InequivalenceForcesDistinguishingFuture

/-- A certified finite future interface exposes a finite question basis and a
    Boolean reachability procedure whose answers are proved faithful to the
    semantic `RepairReachable` relation. The executable search below depends on
    this interface, not on classical choice. -/
structure CertifiedFiniteFutureInterface (I F : Type)
    (futureOf : I → F) where
  questions : List F
  covers : ∀ f : F, f ∈ questions
  predict : Repair I → F → Bool
  faithful : ∀ (R : Repair I) (f : F),
    predict R f = true ↔ RepairReachable futureOf R f

/-- Executable first-difference search. -/
def firstDifference {F : Type}
    (left right : F → Bool) : List F → Option F
  | [] => none
  | f :: fs =>
      if left f = right f then firstDifference left right fs else some f

/-- Every returned question is genuinely prediction-separating. -/
theorem firstDifference_sound
    {F : Type} (left right : F → Bool) (qs : List F) (f : F)
    (h : firstDifference left right qs = some f) :
    f ∈ qs ∧ left f ≠ right f := by
  induction qs with
  | nil =>
      simp [firstDifference] at h
  | cons a as ih =>
      by_cases heq : left a = right a
      · simp [firstDifference, heq] at h
        rcases ih h with ⟨hmem, hdiff⟩
        exact ⟨List.mem_cons_of_mem a hmem, hdiff⟩
      · simp [firstDifference, heq] at h
        subst f
        exact ⟨List.mem_cons_self, heq⟩

/-- If the finite list contains any disagreement, the executable search returns
    one. -/
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

/-- The actual executable experiment generator. No proof of inequivalence and no
    separator witness is an argument to this program. -/
def firstDistinguishingFuture
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R₁ R₂ : Repair I) : Option F :=
  firstDifference (B.predict R₁) (B.predict R₂) B.questions

/-- Semantic inequivalence guarantees a Boolean disagreement somewhere in every
    complete faithful finite interface. Classical reasoning is used only in this
    correctness proof; it is absent from `firstDistinguishingFuture`. -/
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

/-- Therefore executable search cannot return `none` on behaviorally distinct
    repairs. -/
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

/-- Two unequal Boolean predictions are complementary, so any external Boolean
    outcome keeps exactly one candidate. -/
theorem unequal_predictions_exactly_one_matches
    {a b outcome : Bool} (hneq : a ≠ b) :
    (a = outcome ∧ b ≠ outcome) ∨
    (b = outcome ∧ a ≠ outcome) := by
  cases a <;> cases b <;> cases outcome <;> simp_all

/-- A future returned by the executable search is therefore a deciding
    experiment for the binary version space. -/
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

/-- A concrete finite certified interface for the cycle-6 divergent pair. -/
def basis : CertifiedFiniteFutureInterface Idx Fut futureOf where
  questions := [.alpha, .beta]
  covers := by
    intro f
    cases f <;> simp
  predict := fun R f =>
    match f with
    | .alpha => decide (R .left)
    | .beta => decide (R .right)
  faithful := by
    intro R f
    cases f with
    | alpha =>
        constructor
        · intro h
          have hleft : R .left := by
            simpa using h
          exact ⟨.left, hleft, rfl⟩
        · rintro ⟨i, hi, hif⟩
          cases i with
          | left => simpa using hi
          | right => cases hif
    | beta =>
        constructor
        · intro h
          have hright : R .right := by
            simpa using h
          exact ⟨.right, hright, rfl⟩
        · rintro ⟨i, hi, hif⟩
          cases i with
          | left => cases hif
          | right => simpa using hi

/-- In the witness, the actual executable search returns alpha directly. -/
theorem computes_alpha :
    firstDistinguishingFuture basis leftRepair rightRepair = some .alpha := by
  rfl

/-- The computed question decides the pair for every external outcome. -/
theorem computed_question_always_decides (outcome : Bool) :
    (basis.predict leftRepair .alpha = outcome ∧
      basis.predict rightRepair .alpha ≠ outcome) ∨
    (basis.predict rightRepair .alpha = outcome ∧
      basis.predict leftRepair .alpha ≠ outcome) := by
  exact executable_question_decides_pair basis computes_alpha outcome

end Witness

/-- Cycle-9 conclusion: under an explicit finite, complete, verifier-certified
    future interface, behavioral inequivalence is converted to a deciding
    experiment by an executable recursive search. `Classical.choice` is no
    longer part of the experiment generator. -/
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
