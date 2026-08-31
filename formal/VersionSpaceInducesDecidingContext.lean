import AmbiguityInducesDecidingContext

namespace VersionSpaceInducesDecidingContext

open VerifierOutcomeCannotIdentifyExactContextGrammar
open NewConsequenceSeparatesContextGrammar

/-- The only retained datum from the current observation is its verifier-outcome
    profile.  Grammars are not supplied as a distinguished pair to the selector. -/
def currentProfile : Bool → Prop :=
  OutcomeProfile grammarNeg verifier true

/-- Residual-relative grammar version space: every grammar still compatible with
    the current verifier consequence. -/
def Compatible (G : ContextGrammar Bool) : Prop :=
  OutcomeProfile G verifier true = currentProfile

abbrev VersionSpace := {G : ContextGrammar Bool // Compatible G}

/-- The known witness grammars merely certify that the version space is genuinely
    non-singleton; they are not parameters of the deciding-context definition. -/
def negVersion : VersionSpace := ⟨grammarNeg, rfl⟩

def constVersion : VersionSpace :=
  ⟨grammarConst, by
    exact same_outcome_profile.symm⟩

theorem version_space_contains_distinct_grammars :
    negVersion.1 ≠ constVersion.1 := by
  exact grammars_are_distinct

/-- A state is deciding exactly when it splits some pair of grammars that remain
    possible under the current consequence.  No distinguished grammar pair or
    finite context pool is supplied. -/
def SplitsVersionSpace (x : Bool) : Prop :=
  ∃ G₁ G₂ : VersionSpace,
    OutcomeProfile G₁.1 verifier x ≠ OutcomeProfile G₂.1 verifier x

abbrev DecidingContext := {x : Bool // SplitsVersionSpace x}

/-- Every currently compatible grammar has the same profile at the current site,
    so the current site cannot split the version space. -/
theorem current_context_cannot_split_version_space :
    ¬ SplitsVersionSpace true := by
  rintro ⟨G₁, G₂, hdiff⟩
  apply hdiff
  calc
    OutcomeProfile G₁.1 verifier true = currentProfile := G₁.2
    _ = OutcomeProfile G₂.1 verifier true := G₂.2.symm

/-- The consequence geometry itself certifies that another site splits the
    surviving version space. -/
theorem false_context_splits_version_space :
    SplitsVersionSpace false := by
  refine ⟨negVersion, constVersion, ?_⟩
  intro hprofiles
  have hpoint :
      OutcomeProfile grammarNeg verifier false true =
        OutcomeProfile grammarConst verifier false true :=
    congrFun hprofiles true
  have hconst : OutcomeProfile grammarConst verifier false true :=
    hpoint.mp neg_grammar_reaches_true_from_false
  exact const_grammar_cannot_reach_true_from_false hconst

def generatedDecidingContext : DecidingContext :=
  ⟨false, false_context_splits_version_space⟩

/-- In this witness the version-space split criterion uniquely determines the
    next observation site. -/
theorem deciding_context_is_unique (d : DecidingContext) :
    d.1 = generatedDecidingContext.1 := by
  cases h : d.1 with
  | false => rfl
  | true =>
      exfalso
      apply current_context_cannot_split_version_space
      simpa [h] using d.2

/-- Any representation of the next-query decision that is sufficient to name a
    splitter must choose from the consequence-induced splitter subtype; there is
    no privileged grammar pair in that interface. -/
theorem version_space_ambiguity_forces_next_context :
    Nonempty VersionSpace ∧
    (∃ G₁ G₂ : VersionSpace, G₁.1 ≠ G₂.1) ∧
    (¬ SplitsVersionSpace true) ∧
    Nonempty DecidingContext ∧
    (∀ d : DecidingContext, d.1 = generatedDecidingContext.1) := by
  exact ⟨⟨negVersion⟩,
    ⟨negVersion, constVersion, version_space_contains_distinct_grammars⟩,
    current_context_cannot_split_version_space,
    ⟨generatedDecidingContext⟩,
    deciding_context_is_unique⟩

/-- Main result: current verifier consequence induces a grammar version space;
    unresolved multiplicity in that space induces the ontology of deciding
    contexts; in this finite witness that ontology has one underlying state.

    The remaining supplied scaffold is the raw Bool carrier and the hypothesis
    universe `ContextGrammar Bool`, not a hand-selected grammar pair. -/
theorem residual_version_space_induces_unique_deciding_context :
    (∃ G₁ G₂ : VersionSpace, G₁.1 ≠ G₂.1) ∧
    (¬ SplitsVersionSpace true) ∧
    SplitsVersionSpace generatedDecidingContext.1 ∧
    (∀ d : DecidingContext, d.1 = generatedDecidingContext.1) := by
  exact ⟨
    ⟨negVersion, constVersion, version_space_contains_distinct_grammars⟩,
    current_context_cannot_split_version_space,
    generatedDecidingContext.2,
    deciding_context_is_unique⟩

#check version_space_contains_distinct_grammars
#check current_context_cannot_split_version_space
#check false_context_splits_version_space
#check deciding_context_is_unique
#check version_space_ambiguity_forces_next_context
#check residual_version_space_induces_unique_deciding_context

end VersionSpaceInducesDecidingContext
