import VerifierOutcomeCannotIdentifyExactHypothesisUniverse

namespace NewConsequenceInducesHypothesisUniverse

open VerifierOutcomeCannotIdentifyExactContextGrammar
open NewConsequenceSeparatesContextGrammar
open VersionSpaceInducesDecidingContext
open VerifierOutcomeCannotIdentifyExactHypothesisUniverse

/-- A newly returned verifier profile at the consequence-selected deciding
    context induces the next retained hypothesis universe by intersecting the
    current version space with that new consequence.  No hidden universe is an
    input to this update rule. -/
def RefinedCompatible (newProfile : Bool → Prop) (G : ContextGrammar Bool) : Prop :=
  Compatible G ∧
    OutcomeProfile G verifier generatedDecidingContext.1 = newProfile

abbrev RefinedUniverse (newProfile : Bool → Prop) :=
  {G : ContextGrammar Bool // RefinedCompatible newProfile G}

/-- The concrete new consequence returned by the witness world at the
    consequence-selected next context. -/
def observedNextProfile : Bool → Prop :=
  OutcomeProfile grammarNeg verifier generatedDecidingContext.1

/-- The currently viable negation grammar survives the consequence-induced
    update. -/
theorem neg_survives_refined_universe :
    RefinedCompatible observedNextProfile grammarNeg := by
  constructor
  · rfl
  · rfl

/-- The constant grammar was compatible with the old consequence. -/
theorem const_was_currently_compatible :
    Compatible grammarConst := by
  exact same_outcome_profile.symm

/-- The new consequence excludes the constant grammar. -/
theorem const_eliminated_by_new_consequence :
    ¬ RefinedCompatible observedNextProfile grammarConst := by
  rintro ⟨_, hnext⟩
  have hprofiles :
      OutcomeProfile grammarConst verifier false =
        OutcomeProfile grammarNeg verifier false := by
    simpa [observedNextProfile, generatedDecidingContext] using hnext
  have hpoint :
      OutcomeProfile grammarConst verifier false true =
        OutcomeProfile grammarNeg verifier false true :=
    congrFun hprofiles true
  have hconst : OutcomeProfile grammarConst verifier false true :=
    hpoint.mpr neg_grammar_reaches_true_from_false
  exact const_grammar_cannot_reach_true_from_false hconst

/-- The induced next universe is a strict refinement of the current version
    space: every retained grammar was previously compatible, while at least one
    previously compatible grammar is now excluded. -/
theorem refined_universe_is_strictly_smaller :
    (∀ G : ContextGrammar Bool,
      RefinedCompatible observedNextProfile G → Compatible G) ∧
    (∃ G : ContextGrammar Bool,
      Compatible G ∧ ¬ RefinedCompatible observedNextProfile G) := by
  constructor
  · intro G h
    exact h.1
  · exact ⟨grammarConst, const_was_currently_compatible,
      const_eliminated_by_new_consequence⟩

/-- The two exact hidden hypothesis universes were observationally identical at
    the old site, but the consequence-selected new site makes their operational
    images different. -/
theorem new_context_separates_observable_hypothesis_universes :
    ObservableUniverse universeNeg generatedDecidingContext.1 ≠
      ObservableUniverse universeConst generatedDecidingContext.1 := by
  intro h
  have hpoint := congrFun h true
  have hneg :
      ObservableUniverse universeNeg generatedDecidingContext.1 true := by
    refine ⟨grammarNeg, rfl, ?_⟩
    simpa [generatedDecidingContext] using neg_grammar_reaches_true_from_false
  have hconst :
      ObservableUniverse universeConst generatedDecidingContext.1 true :=
    hpoint.mp hneg
  rcases hconst with ⟨G, hG, hout⟩
  subst G
  have : OutcomeProfile grammarConst verifier false true := by
    simpa [generatedDecidingContext] using hout
  exact const_grammar_cannot_reach_true_from_false this

/-- The positive developmental step: current consequence leaves a nontrivial
    version space; that ambiguity induces a unique deciding context; the
    verifier result at that context induces the next retained hypothesis
    universe; and the new universe is strictly finer than the old one.

    The update rule receives the current consequence and the newly verified
    profile, not an externally supplied target universe. -/
theorem consequence_selected_context_generates_stricter_hypothesis_universe :
    (¬ SplitsVersionSpace true) ∧
    (∀ d : DecidingContext, d.1 = generatedDecidingContext.1) ∧
    RefinedCompatible observedNextProfile grammarNeg ∧
    Compatible grammarConst ∧
    ¬ RefinedCompatible observedNextProfile grammarConst ∧
    ObservableUniverse universeNeg true = ObservableUniverse universeConst true ∧
    ObservableUniverse universeNeg generatedDecidingContext.1 ≠
      ObservableUniverse universeConst generatedDecidingContext.1 := by
  exact ⟨
    current_context_cannot_split_version_space,
    deciding_context_is_unique,
    neg_survives_refined_universe,
    const_was_currently_compatible,
    const_eliminated_by_new_consequence,
    same_current_observable_universe,
    new_context_separates_observable_hypothesis_universes⟩

#check neg_survives_refined_universe
#check const_was_currently_compatible
#check const_eliminated_by_new_consequence
#check refined_universe_is_strictly_smaller
#check new_context_separates_observable_hypothesis_universes
#check consequence_selected_context_generates_stricter_hypothesis_universe

end NewConsequenceInducesHypothesisUniverse
