import Std

/-! # PROSPECTIVE prediction 2 — frozen BEFORE Target 5

  Search policy has now become explicit state (SearchPolicy.lean), with a frozen selector
  `SelectPolicy : SearchConstraint → SearchPolicy`.  The question: after this control-parametric
  repair, what is the NEXT hidden-concreteness locus?

  The dependency stack now extends one step:
      representation → residualLocalization → candidateGrammar → searchPolicy → featureExtractor → verifier

  Status at this freeze point (after search-policy-as-state):
      representation         repaired
      residualLocalization   repaired  (anti-unification `diff`)
      candidateGrammar       repaired  (bounded typed closure)
      searchPolicy           repaired  (explicit state + frozen selector)
      featureExtractor       concrete  (the fixed {requiredDepth, safeArity} feature set that reads
                                        a residual into a SearchConstraint)
      verifier               stable    (external Lean kernel)

  THE PROSPECTIVE PREDICTION:
  after the search policy becomes state, the next component likely to fail is the RESIDUAL-FEATURE
  EXTRACTOR / policy selector — the fixed feature set {requiredDepth, safeArity} that maps a
  residual to a search constraint.  It is still hard-coded: "reading a residual" means computing
  depth and arity.  A new target whose residual limits continuation along a DIFFERENT search
  dimension (e.g. which sort to focus expansion on, or relevance weighting) would not be
  expressible in this feature set, and the frozen selector would pick a policy that misses it.

  Predicted failure signature: the residual demands a search-policy choice that the fixed feature
  set {requiredDepth, safeArity} cannot express — the selector produces a policy from the wrong
  (too narrow) features, so search fails even though the invariant is representable, localizable,
  generatable, and the policy dimension IS available (it just was not selected).

  Explicit alternative loci (if any of these fails instead, the prediction is FALSE):
    representation, residualLocalization, candidateGrammar, searchPolicy, verifier.
-/

namespace ProspectivePrediction2

inductive Component where
  | representation | residualLocalization | candidateGrammar | searchPolicy | featureExtractor | verifier
  deriving DecidableEq, Repr, Inhabited

inductive Status where
  | repaired | falsified | concrete | stable
  deriving DecidableEq, Repr, Inhabited

def dependencyOrder : List Component :=
  [.representation, .residualLocalization, .candidateGrammar, .searchPolicy, .featureExtractor, .verifier]

def currentStatus : Component → Status
  | .representation       => .repaired
  | .residualLocalization => .repaired
  | .candidateGrammar     => .repaired
  | .searchPolicy         => .repaired
  | .featureExtractor     => .concrete
  | .verifier             => .stable

/- THE PREDICTION: `featureExtractor` is the unique still-concrete component. -/
theorem feature_extractor_is_only_concrete :
    (dependencyOrder.filter (fun c => currentStatus c = .concrete)) = [.featureExtractor] := by
  native_decide

theorem feature_extractor_downstream_of_search :
    (dependencyOrder.filter (fun c => c == .searchPolicy || c == .featureExtractor))
      = [.searchPolicy, .featureExtractor] := by
  native_decide

/- Explicit falsifiers (any one ⇒ the prediction is FALSE): -/
def falsifiers : List String := [
  "representation fails on the target (E1)",
  "residual localization / diff fails (E2)",
  "candidate grammar cannot express the repair (C1)",
  "search policy itself fails rather than the feature extractor",
  "the verifier fails (D)"
]

end ProspectivePrediction2
