import Std

/-! # PROSPECTIVE meta-prediction — frozen BEFORE the Target-3 grammar repair

  This file records the next predicted hidden-concreteness locus *before* the candidate-grammar
  seam (Target 3, outcome C1) is repaired.  It makes the meta-method prospective, not a
  retrospective summary of a recurring repair pattern.

  The dependency stack, downstream order:
      representation → residualLocalization → candidateGrammar → searchPolicy → verifier

  Status at this freeze point (before the grammar repair):
      representation         repaired  (signature-generic, d54c07b)
      residualLocalization   repaired  (anti-unification `diff`, targets 2 & 3)
      candidateGrammar       falsified (Target 3, C1 — no construction operator)
      searchPolicy           concrete  (bounded enumeration + cost/ranking, never yet falsified)
      verifier               stable    (external Lean kernel — never the failing component)

  THE PROSPECTIVE PREDICTION:
  after the candidate grammar is made signature-parametric, the next component likely to fail is
      search policy / candidate cost / ranking
  — NOT representation, residual extraction, anti-unification, parameter generalization, grammar
  expressivity, or verification.  Predicted failure signature (C2-like):
      the required repair is representable AND generatable, but is not reached / ranked within
      the frozen bounded search.
-/

namespace ProspectivePrediction

inductive Component where
  | representation | residualLocalization | candidateGrammar | searchPolicy | verifier
  deriving DecidableEq, Repr, Inhabited

inductive Status where
  | repaired | falsified | concrete | stable
  deriving DecidableEq, Repr, Inhabited

/- downstream dependency order. -/
def dependencyOrder : List Component :=
  [.representation, .residualLocalization, .candidateGrammar, .searchPolicy, .verifier]

/- current status BEFORE the grammar repair. -/
def currentStatus : Component → Status
  | .representation       => .repaired
  | .residualLocalization => .repaired
  | .candidateGrammar     => .falsified
  | .searchPolicy         => .concrete
  | .verifier             => .stable

/- THE PREDICTION: `searchPolicy` is the unique still-concrete component (the next to fail),
   and it sits strictly downstream of the currently-falsified `candidateGrammar`. -/
theorem search_is_the_only_concrete_component :
    (dependencyOrder.filter (fun c => currentStatus c = .concrete)) = [.searchPolicy] := by
  native_decide

theorem search_is_downstream_of_grammar :
    (dependencyOrder.filter (fun c => c == .candidateGrammar || c == .searchPolicy))
      = [.candidateGrammar, .searchPolicy] := by
  native_decide

/- Predicted failure signature (C2-like): repair ∈ V_B but search/ranking does not reach it. -/
def predictedFailureSignature : String :=
  "representable ∧ generatable ∧ (not reached/ranked within frozen bounded search)"

/- Explicit FALSIFIERS — if any of these holds for Target 4, the prediction is FALSE: -/
def falsifiers : List String := [
  "representation cannot encode the target proof state (E1)",
  "diff / residual extraction fails to localize the dependency (E2)",
  "generalized candidate grammar cannot express the repair (C1)",
  "the candidate is reached but Lean cannot prove it (D)",
  "Target 4 succeeds with no search/ranking bottleneck"
]

end ProspectivePrediction
