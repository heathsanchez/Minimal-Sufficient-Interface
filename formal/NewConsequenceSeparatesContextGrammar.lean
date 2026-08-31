import VerifierOutcomeCannotIdentifyExactContextGrammar

namespace NewConsequenceSeparatesContextGrammar

open VerifierOutcomeCannotIdentifyExactContextGrammar

/-- The current consequence sees only one observed state.  The developmental
    extension asks the same verifier question at every state of the raw carrier. -/
def ExpandedProfile (G : ContextGrammar Bool) : Bool → Bool → Prop :=
  fun x => OutcomeProfile G verifier x

/-- At the original state the two genuinely different grammars remain
    operationally indistinguishable. -/
theorem old_consequence_still_cannot_separate :
    OutcomeProfile grammarNeg verifier true =
      OutcomeProfile grammarConst verifier true := by
  exact same_outcome_profile

/-- The negation grammar can produce verdict `true` from the newly queried
    state `false`. -/
theorem neg_grammar_reaches_true_from_false :
    OutcomeProfile grammarNeg verifier false true := by
  refine ⟨Bool.not, Or.inr rfl, ?_⟩
  rfl

/-- The identity/constant-false grammar cannot do so. -/
theorem const_grammar_cannot_reach_true_from_false :
    ¬ OutcomeProfile grammarConst verifier false true := by
  rintro ⟨f, hf, hv⟩
  rcases hf with hId | hConst
  · subst f
    simp [verifier] at hv
  · subst f
    simp [verifier, constFalse] at hv

/-- The extra verifier context therefore separates the two grammars that were
    provably indistinguishable under the old consequence. -/
theorem expanded_consequence_separates_grammars :
    ExpandedProfile grammarNeg ≠ ExpandedProfile grammarConst := by
  intro h
  have hreach : OutcomeProfile grammarConst verifier false true := by
    have hpoint : ExpandedProfile grammarNeg false = ExpandedProfile grammarConst false :=
      congrFun h false
    have hprop :
        OutcomeProfile grammarNeg verifier false true =
          OutcomeProfile grammarConst verifier false true :=
      congrFun hpoint true
    exact hprop.mp neg_grammar_reaches_true_from_false
  exact const_grammar_cannot_reach_true_from_false hreach

/-- Developmental phase transition: a representation ambiguity that cannot be
    resolved from the current verifier consequence becomes resolvable only after
    admitting a genuinely new deciding context.  We do not claim that this
    expanded profile uniquely identifies arbitrary grammars; only that it
    strictly refines the previous consequence equivalence in this witness. -/
theorem new_consequence_creates_new_structural_distinction :
    grammarNeg ≠ grammarConst ∧
    OutcomeProfile grammarNeg verifier true =
      OutcomeProfile grammarConst verifier true ∧
    ExpandedProfile grammarNeg ≠ ExpandedProfile grammarConst := by
  exact ⟨grammars_are_distinct,
    old_consequence_still_cannot_separate,
    expanded_consequence_separates_grammars⟩

#check old_consequence_still_cannot_separate
#check neg_grammar_reaches_true_from_false
#check const_grammar_cannot_reach_true_from_false
#check expanded_consequence_separates_grammars
#check new_consequence_creates_new_structural_distinction

end NewConsequenceSeparatesContextGrammar
