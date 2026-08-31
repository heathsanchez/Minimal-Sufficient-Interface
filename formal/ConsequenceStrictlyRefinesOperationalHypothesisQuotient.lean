import ConsequenceRefinesHypothesisUniverse

namespace ConsequenceStrictlyRefinesOperationalHypothesisQuotient

open VerifierOutcomeCannotIdentifyExactContextGrammar
open VersionSpaceInducesDecidingContext
open ConsequenceRefinesHypothesisUniverse

/-- The old operational observation available before querying the induced
    deciding context. -/
def oldObservation (G : ContextGrammar Bool) : Bool → Prop :=
  OutcomeProfile G verifier true

/-- The new verifier observation produced at the consequence-selected deciding
    context. -/
def decidingObservation (G : ContextGrammar Bool) : Bool → Prop :=
  OutcomeProfile G verifier generatedDecidingContext.1

/-- Development retains the old consequence and adjoins the new one. -/
def refinedObservation (G : ContextGrammar Bool) :
    (Bool → Prop) × (Bool → Prop) :=
  (oldObservation G, decidingObservation G)

def oldSetoid : Setoid (ContextGrammar Bool) where
  r G₁ G₂ := oldObservation G₁ = oldObservation G₂
  iseqv := {
    refl := fun _ => rfl
    symm := fun h => h.symm
    trans := fun h₁ h₂ => h₁.trans h₂
  }

def refinedSetoid : Setoid (ContextGrammar Bool) where
  r G₁ G₂ := refinedObservation G₁ = refinedObservation G₂
  iseqv := {
    refl := fun _ => rfl
    symm := fun h => h.symm
    trans := fun h₁ h₂ => h₁.trans h₂
  }

abbrev OldOperationalHypothesis := Quotient oldSetoid
abbrev RefinedOperationalHypothesis := Quotient refinedSetoid

def oldClass (G : ContextGrammar Bool) : OldOperationalHypothesis :=
  Quotient.mk oldSetoid G

def refinedClass (G : ContextGrammar Bool) : RefinedOperationalHypothesis :=
  Quotient.mk refinedSetoid G

/-- The new consequence never withdraws an old distinction: refined equality
    implies old equality. -/
theorem refined_equivalence_implies_old_equivalence
    {G₁ G₂ : ContextGrammar Bool}
    (h : refinedObservation G₁ = refinedObservation G₂) :
    oldObservation G₁ = oldObservation G₂ := by
  exact congrArg Prod.fst h

/-- Therefore there is a canonical forgetful map from the refined operational
    quotient to the old one. -/
def forgetNewConsequence :
    RefinedOperationalHypothesis → OldOperationalHypothesis :=
  Quotient.lift oldClass (by
    intro G₁ G₂ h
    apply Quotient.sound
    exact refined_equivalence_implies_old_equivalence h)

@[simp] theorem forget_new_on_class (G : ContextGrammar Bool) :
    forgetNewConsequence (refinedClass G) = oldClass G := by
  rfl

/-- The witness grammars were operationally identical before development. -/
theorem witnesses_same_old_operational_class :
    oldClass grammarNeg = oldClass grammarConst := by
  apply Quotient.sound
  exact same_outcome_profile

/-- The consequence-selected deciding context splits that same old class. -/
theorem witnesses_distinct_refined_operational_classes :
    refinedClass grammarNeg ≠ refinedClass grammarConst := by
  intro h
  have href : refinedObservation grammarNeg = refinedObservation grammarConst :=
    Quotient.exact h
  have hnew : decidingObservation grammarNeg = decidingObservation grammarConst :=
    congrArg Prod.snd href
  exact generated_context_separates_witnesses hnew

/-- Strictness is categorical: forgetting the new consequence is not injective.
    Two newly distinct operational hypotheses map to one old hypothesis. -/
theorem forgetful_projection_not_injective :
    ¬ Function.Injective forgetNewConsequence := by
  intro hinj
  apply witnesses_distinct_refined_operational_classes
  apply hinj
  simpa using witnesses_same_old_operational_class

/-- Main result: the consequence-selected deciding context strictly refines the
    operational hypothesis quotient while preserving every old consequence.
    Development is therefore a refinement of verifier-induced operational
    equality, not reconstruction of hidden raw syntax. -/
theorem consequence_selected_context_strictly_refines_operational_quotient :
    (∀ G₁ G₂,
      refinedObservation G₁ = refinedObservation G₂ →
      oldObservation G₁ = oldObservation G₂) ∧
    oldClass grammarNeg = oldClass grammarConst ∧
    refinedClass grammarNeg ≠ refinedClass grammarConst ∧
    ¬ Function.Injective forgetNewConsequence := by
  exact ⟨
    fun _ _ h => refined_equivalence_implies_old_equivalence h,
    witnesses_same_old_operational_class,
    witnesses_distinct_refined_operational_classes,
    forgetful_projection_not_injective⟩

#check refined_equivalence_implies_old_equivalence
#check forgetNewConsequence
#check witnesses_same_old_operational_class
#check witnesses_distinct_refined_operational_classes
#check forgetful_projection_not_injective
#check consequence_selected_context_strictly_refines_operational_quotient

end ConsequenceStrictlyRefinesOperationalHypothesisQuotient
