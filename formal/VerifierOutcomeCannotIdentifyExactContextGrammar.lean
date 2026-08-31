import Std

namespace VerifierOutcomeCannotIdentifyExactContextGrammar

/-- A context grammar says which transformations of the raw carrier are
    admissible.  No claim is made here that this grammar is itself observable. -/
abbrev Context (X : Type u) := X → X
abbrev ContextGrammar (X : Type u) := Context X → Prop

/-- What a verifier can observe from a grammar at one current state: which
    verdicts can be produced by some admissible context. -/
def OutcomeProfile {X : Type u}
    (G : ContextGrammar X) (V : X → Bool) (observed : X) : Bool → Prop :=
  fun b => ∃ f, G f ∧ V (f observed) = b

/-- First grammar: identity and Boolean negation are admissible. -/
def grammarNeg : ContextGrammar Bool :=
  fun f => f = id ∨ f = Bool.not

/-- Second grammar: identity and the constant-false map are admissible. -/
def constFalse : Context Bool := fun _ => false

def grammarConst : ContextGrammar Bool :=
  fun f => f = id ∨ f = constFalse

def verifier : Bool → Bool := id
def observed : Bool := true

/-- The grammars are extensionally different: negation belongs only to the
    first. -/
theorem grammars_are_distinct : grammarNeg ≠ grammarConst := by
  intro h
  have hneg : grammarNeg Bool.not := Or.inr rfl
  have hc : grammarConst Bool.not := by
    simpa [h] using hneg
  rcases hc with hId | hConst
  · have : Bool.not true = id true := congrFun hId true
    simp at this
  · have : Bool.not false = constFalse false := congrFun hConst false
    simp [constFalse] at this

/-- Yet at the current state, under the current verifier, both grammars expose
    exactly the same consequence profile: both `true` and `false` are reachable
    verdicts. -/
theorem same_outcome_profile :
    OutcomeProfile grammarNeg verifier observed =
      OutcomeProfile grammarConst verifier observed := by
  funext b
  apply propext
  constructor
  · intro h
    rcases h with ⟨f, hf, hv⟩
    cases b with
    | false =>
        refine ⟨constFalse, Or.inr rfl, ?_⟩
        rfl
    | true =>
        refine ⟨id, Or.inl rfl, ?_⟩
        rfl
  · intro h
    rcases h with ⟨f, hf, hv⟩
    cases b with
    | false =>
        refine ⟨Bool.not, Or.inr rfl, ?_⟩
        rfl
    | true =>
        refine ⟨id, Or.inl rfl, ?_⟩
        rfl

/-- Consequently, no deterministic reconstruction rule whose only input is the
    verifier outcome profile can recover the exact grammar in both worlds. -/
theorem no_profile_only_reconstructor_recovers_both :
    ¬ ∃ infer : (Bool → Prop) → ContextGrammar Bool,
      infer (OutcomeProfile grammarNeg verifier observed) = grammarNeg ∧
      infer (OutcomeProfile grammarConst verifier observed) = grammarConst := by
  rintro ⟨infer, hNeg, hConst⟩
  have hinfer :
      infer (OutcomeProfile grammarNeg verifier observed) =
        infer (OutcomeProfile grammarConst verifier observed) := by
    rw [same_outcome_profile]
  apply grammars_are_distinct
  calc
    grammarNeg = infer (OutcomeProfile grammarNeg verifier observed) := hNeg.symm
    _ = infer (OutcomeProfile grammarConst verifier observed) := hinfer
    _ = grammarConst := hConst

/-- The observable quotient is stable even when the hidden context syntax is
    changed.  Thus pointwise consequence licenses forgetting exact syntax. -/
theorem consequence_determines_profile_not_exact_context_syntax :
    grammarNeg ≠ grammarConst ∧
    OutcomeProfile grammarNeg verifier observed =
      OutcomeProfile grammarConst verifier observed ∧
    (¬ ∃ infer : (Bool → Prop) → ContextGrammar Bool,
      infer (OutcomeProfile grammarNeg verifier observed) = grammarNeg ∧
      infer (OutcomeProfile grammarConst verifier observed) = grammarConst) := by
  exact ⟨grammars_are_distinct, same_outcome_profile,
    no_profile_only_reconstructor_recovers_both⟩

#check grammars_are_distinct
#check same_outcome_profile
#check no_profile_only_reconstructor_recovers_both
#check consequence_determines_profile_not_exact_context_syntax

end VerifierOutcomeCannotIdentifyExactContextGrammar
