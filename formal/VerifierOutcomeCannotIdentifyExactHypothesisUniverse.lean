import VersionSpaceInducesDecidingContext

namespace VerifierOutcomeCannotIdentifyExactHypothesisUniverse

open VerifierOutcomeCannotIdentifyExactContextGrammar

/-- A hypothesis universe is only a predicate saying which raw context grammars
    are currently admissible.  No privileged enumeration or ordering is assumed. -/
abbrev HypothesisUniverse := ContextGrammar Bool → Prop

/-- Two genuinely different singleton hypothesis universes. -/
def universeNeg : HypothesisUniverse := fun G => G = grammarNeg

def universeConst : HypothesisUniverse := fun G => G = grammarConst

/-- What the current verifier consequence can see of a hypothesis universe:
    which Boolean verifier outcomes are possible at the observed state. -/
def ObservableUniverse (U : HypothesisUniverse) (x : Bool) : Bool → Prop :=
  fun b => ∃ G : ContextGrammar Bool, U G ∧ OutcomeProfile G verifier x b

/-- The two hypothesis universes are extensionally different. -/
theorem hypothesis_universes_are_distinct : universeNeg ≠ universeConst := by
  intro h
  have hpoint := congrFun h grammarNeg
  have hneg : universeNeg grammarNeg := rfl
  have hconst : universeConst grammarNeg := hpoint.mp hneg
  exact grammars_are_distinct hconst

/-- Under the currently admitted observation, the verifier sees exactly the same
    possible outcome set from both distinct hypothesis universes. -/
theorem same_current_observable_universe :
    ObservableUniverse universeNeg true = ObservableUniverse universeConst true := by
  funext b
  apply propext
  constructor
  · rintro ⟨G, hG, hout⟩
    subst G
    refine ⟨grammarConst, rfl, ?_⟩
    have hp := congrFun same_outcome_profile b
    exact hp.mp hout
  · rintro ⟨G, hG, hout⟩
    subst G
    refine ⟨grammarNeg, rfl, ?_⟩
    have hp := congrFun same_outcome_profile b
    exact hp.mpr hout

/-- No deterministic procedure receiving only the currently observable universe
    can reconstruct the exact hidden hypothesis universe in both worlds. -/
theorem no_current_consequence_reconstructor_recovers_both :
    ¬ ∃ infer : (Bool → Prop) → HypothesisUniverse,
      infer (ObservableUniverse universeNeg true) = universeNeg ∧
      infer (ObservableUniverse universeConst true) = universeConst := by
  rintro ⟨infer, hneg, hconst⟩
  apply hypothesis_universes_are_distinct
  calc
    universeNeg = infer (ObservableUniverse universeNeg true) := hneg.symm
    _ = infer (ObservableUniverse universeConst true) := by rw [same_current_observable_universe]
    _ = universeConst := hconst

/-- Main negative boundary: pointwise verifier consequence determines an
    operational image of the surviving hypothesis universe, not its exact hidden
    syntax/membership.  Therefore the exact hypothesis universe is not justified
    by this consequence alone. -/
theorem consequence_does_not_identify_exact_hypothesis_universe :
    universeNeg ≠ universeConst ∧
    ObservableUniverse universeNeg true = ObservableUniverse universeConst true ∧
    ¬ ∃ infer : (Bool → Prop) → HypothesisUniverse,
      infer (ObservableUniverse universeNeg true) = universeNeg ∧
      infer (ObservableUniverse universeConst true) = universeConst := by
  exact ⟨hypothesis_universes_are_distinct,
    same_current_observable_universe,
    no_current_consequence_reconstructor_recovers_both⟩

#check hypothesis_universes_are_distinct
#check same_current_observable_universe
#check no_current_consequence_reconstructor_recovers_both
#check consequence_does_not_identify_exact_hypothesis_universe

end VerifierOutcomeCannotIdentifyExactHypothesisUniverse
