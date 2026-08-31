import NewConsequenceSeparatesContextGrammar

namespace AmbiguityInducesDecidingContext

open VerifierOutcomeCannotIdentifyExactContextGrammar
open NewConsequenceSeparatesContextGrammar

/-- The next observation site is not supplied by a named selector.  It is the
    subtype of raw states at which the currently indistinguishable grammars
    become distinguishable by verifier consequence. -/
def DecidingContext : Type :=
  {x : Bool // OutcomeProfile grammarNeg verifier x ≠
    OutcomeProfile grammarConst verifier x}

/-- The current observation site is excluded by the certified ambiguity. -/
theorem current_context_is_not_deciding :
    ¬ OutcomeProfile grammarNeg verifier true ≠
      OutcomeProfile grammarConst verifier true := by
  intro h
  exact h old_consequence_still_cannot_separate

/-- The newly exposed site inhabits the deciding-context type because verifier
    consequence differs there. -/
def generatedDecidingContext : DecidingContext :=
  ⟨false, by
    intro hprofiles
    have hpoint :
        OutcomeProfile grammarNeg verifier false true =
          OutcomeProfile grammarConst verifier false true :=
      congrFun hprofiles true
    have hconst : OutcomeProfile grammarConst verifier false true :=
      hpoint.mp neg_grammar_reaches_true_from_false
    exact const_grammar_cannot_reach_true_from_false hconst⟩

/-- In this finite witness the consequence geometry determines the deciding
    context uniquely: every inhabitant is the state `false`. -/
theorem deciding_context_is_unique (d : DecidingContext) :
    d.1 = false := by
  cases h : d.1 with
  | false => rfl
  | true =>
      exfalso
      exact d.2 (by simpa [h] using old_consequence_still_cannot_separate)

/-- Any context that genuinely resolves the grammar ambiguity is, definitionally,
    an inhabitant of the induced deciding-context ontology. -/
def contextFromSeparation (x : Bool)
    (hsep : OutcomeProfile grammarNeg verifier x ≠
      OutcomeProfile grammarConst verifier x) : DecidingContext :=
  ⟨x, hsep⟩

/-- No semantic label or candidate pool is required to specify the next context:
    its identity is forced by the verifier-relative separation predicate. -/
theorem ambiguity_forces_unique_next_context :
    Nonempty DecidingContext ∧
    (∀ d : DecidingContext, d.1 = generatedDecidingContext.1) ∧
    (¬ OutcomeProfile grammarNeg verifier true ≠
      OutcomeProfile grammarConst verifier true) := by
  refine ⟨⟨generatedDecidingContext⟩, ?_, current_context_is_not_deciding⟩
  intro d
  have hd := deciding_context_is_unique d
  have hg := deciding_context_is_unique generatedDecidingContext
  exact hd.trans hg.symm

/-- The induced context is sufficient to expose the previously unavailable
    structural distinction. -/
theorem induced_context_refines_consequence_equivalence :
    OutcomeProfile grammarNeg verifier generatedDecidingContext.1 ≠
      OutcomeProfile grammarConst verifier generatedDecidingContext.1 := by
  exact generatedDecidingContext.2

/-- Main developmental theorem for this witness:

    current consequence ambiguity
      -> verifier-induced deciding-context ontology
      -> unique next observation site
      -> strictly finer consequence equivalence.

    The remaining scaffold is the raw state carrier and the grammar pair whose
    ambiguity is being diagnosed; no general rule for inventing a larger raw
    carrier is claimed here. -/
theorem ambiguity_induces_next_deciding_context :
    grammarNeg ≠ grammarConst ∧
    OutcomeProfile grammarNeg verifier true =
      OutcomeProfile grammarConst verifier true ∧
    Nonempty DecidingContext ∧
    (∀ d : DecidingContext, d.1 = generatedDecidingContext.1) ∧
    OutcomeProfile grammarNeg verifier generatedDecidingContext.1 ≠
      OutcomeProfile grammarConst verifier generatedDecidingContext.1 := by
  exact ⟨grammars_are_distinct,
    old_consequence_still_cannot_separate,
    ambiguity_forces_unique_next_context.1,
    ambiguity_forces_unique_next_context.2.1,
    induced_context_refines_consequence_equivalence⟩

#check current_context_is_not_deciding
#check generatedDecidingContext
#check deciding_context_is_unique
#check ambiguity_forces_unique_next_context
#check induced_context_refines_consequence_equivalence
#check ambiguity_induces_next_deciding_context

end AmbiguityInducesDecidingContext
