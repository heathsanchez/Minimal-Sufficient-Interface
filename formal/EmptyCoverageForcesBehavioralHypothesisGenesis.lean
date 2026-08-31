namespace EmptyCoverageForcesBehavioralHypothesisGenesis

universe u

/-- A hypothesis language is only a predicate on semantic behaviors.  No syntax,
    constructor vocabulary, or grammar representation is assumed. -/
structure HypothesisLanguage (X : Type u) where
  admits : (X → Bool) → Prop

/-- A verifier-certified coverage residual says exactly which behavioral
    consequence is required and certifies that the current language has no
    representative with that behavior. -/
structure CoverageResidual {X : Type u} (L : HypothesisLanguage X) where
  target : X → Bool
  uncovered : ¬ L.admits target

/-- The residual itself determines the behavioral hypothesis to add. -/
def generatedBehavior {X : Type u} {L : HypothesisLanguage X}
    (r : CoverageResidual L) : X → Bool :=
  r.target

/-- Least semantic language extension: retain every old behavior and add exactly
    the verifier-required target behavior. -/
def complete {X : Type u} (L : HypothesisLanguage X) (target : X → Bool) :
    HypothesisLanguage X where
  admits h := L.admits h ∨ h = target

 theorem includeOld {X : Type u} (L : HypothesisLanguage X) (target h : X → Bool)
    (hh : L.admits h) :
    (complete L target).admits h := by
  exact Or.inl hh

 theorem generated_target_admitted {X : Type u} {L : HypothesisLanguage X}
    (r : CoverageResidual L) :
    (complete L (generatedBehavior r)).admits (generatedBehavior r) := by
  exact Or.inr rfl

 theorem generated_target_genuinely_new {X : Type u} {L : HypothesisLanguage X}
    (r : CoverageResidual L) :
    ¬ L.admits (generatedBehavior r) := by
  exact r.uncovered

/-- Nothing unrelated is admitted by completion. -/
theorem no_unrelated_hypothesis {X : Type u} (L : HypothesisLanguage X)
    (target h : X → Bool)
    (hold : ¬ L.admits h) (hne : h ≠ target) :
    ¬ (complete L target).admits h := by
  intro hc
  rcases hc with hc | hc
  · exact hold hc
  · exact hne hc

/-- Universal/leastness property: every language extension containing the old
    language and the demanded target must contain this completion. -/
theorem completion_least {X : Type u} (L M : HypothesisLanguage X)
    (target : X → Bool)
    (hold : ∀ h, L.admits h → M.admits h)
    (htarget : M.admits target) :
    ∀ h, (complete L target).admits h → M.admits h := by
  intro h hc
  rcases hc with hc | hc
  · exact hold h hc
  · simpa [hc] using htarget

/-- If the coverage residual is erased, the old language does not acquire the
    missing behavior by itself. -/
theorem residual_ablation_blocks_genesis {X : Type u} {L : HypothesisLanguage X}
    (r : CoverageResidual L) :
    ¬ L.admits (generatedBehavior r) := by
  exact r.uncovered

/-- Concrete witness: the current language can express only constant Boolean
    behaviors, while the verified consequence requires negation. -/
def constantLanguage : HypothesisLanguage Bool where
  admits h := h = (fun _ => false) ∨ h = (fun _ => true)

def requiredNegation : Bool → Bool := fun b => !b

theorem negation_not_covered :
    ¬ constantLanguage.admits requiredNegation := by
  rintro (h | h)
  · have hp := congrFun h false
    simp [requiredNegation] at hp
  · have hp := congrFun h true
    simp [requiredNegation] at hp

def negationResidual : CoverageResidual constantLanguage where
  target := requiredNegation
  uncovered := negation_not_covered

theorem current_language_has_empty_exact_coverage :
    ¬ ∃ h : Bool → Bool,
      constantLanguage.admits h ∧ h = negationResidual.target := by
  rintro ⟨h, hh, heq⟩
  apply negationResidual.uncovered
  simpa [heq] using hh

/-- Main developmental result: when verified consequence has no representative
    in the current hypothesis language, filtering cannot continue.  The
    consequence itself can be promoted to a semantic hypothesis, and the free
    completion adds exactly that behavior while preserving the old language.

    No target syntax, constructor, or grammar is supplied to the completion.
    The still-supplied scaffold is the semantic behavior carrier `X → Bool`. -/
theorem empty_coverage_forces_behavioral_hypothesis_genesis :
    (¬ constantLanguage.admits negationResidual.target) ∧
    (complete constantLanguage negationResidual.target).admits negationResidual.target ∧
    (∀ h, constantLanguage.admits h →
      (complete constantLanguage negationResidual.target).admits h) ∧
    (∀ h,
      ¬ constantLanguage.admits h →
      h ≠ negationResidual.target →
      ¬ (complete constantLanguage negationResidual.target).admits h) := by
  refine ⟨negationResidual.uncovered,
    generated_target_admitted negationResidual,
    ?_, ?_⟩
  · intro h hh
    exact includeOld constantLanguage negationResidual.target h hh
  · intro h hold hne
    exact no_unrelated_hypothesis constantLanguage negationResidual.target h hold hne

#check generated_target_admitted
#check generated_target_genuinely_new
#check no_unrelated_hypothesis
#check completion_least
#check residual_ablation_blocks_genesis
#check current_language_has_empty_exact_coverage
#check empty_coverage_forces_behavioral_hypothesis_genesis

end EmptyCoverageForcesBehavioralHypothesisGenesis
