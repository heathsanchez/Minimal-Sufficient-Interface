import BoundedDevelopmentalCapability

universe u

namespace MultiCandidateDevelopmentalSearch

open VerifiedConsequenceGenesis

/-- Search a supplied candidate list left-to-right with a fixed verifier budget.
    Candidates that are not expressible in the current language are rejected
    locally and consume no verifier call. Expressible candidates consume one
    verifier call until the budget is exhausted. -/
noncomputable def boundedSearch
    {A : Type u}
    (L : Lang A) (verify : Expr A → Prop) : Nat → List (Expr A) → Option (Expr A)
  | 0, _ => none
  | _, [] => none
  | budget + 1, candidate :: rest => by
      classical
      exact if Expressible L candidate then
        if verify candidate then some candidate
        else boundedSearch L verify budget rest
      else boundedSearch L verify (budget + 1) rest

/-- A promoted ancestor can change the outcome of a genuine multi-candidate
    search without handing the controller the winning descendant as its only
    proposal.  The frozen candidate list contains a verifier-rejected decoy
    followed by the descendant.  Cold search locally rejects the descendant;
    warm search spends one call on the decoy and its second call verifies the
    descendant. -/
theorem promotion_changes_two_candidate_search
    {A : Type u}
    (L : Lang A) (seed decoy : A) (verify : Expr A → Prop)
    (hseedMissing : ¬ L seed)
    (hdecoyPresent : L decoy)
    (hdecoyReject : ¬ verify (.atom decoy))
    (hdescAccept : verify (.op (.atom seed))) :
    let descendant : Expr A := .op (.atom seed)
    let candidates : List (Expr A) := [.atom decoy, descendant]
    boundedSearch (Promote L seed) verify 2 candidates = some descendant ∧
    boundedSearch L verify 2 candidates = none := by
  dsimp
  have hdecoyWarm : Expressible (Promote L seed) (.atom decoy) := by
    exact Expressible.atom (Or.inl hdecoyPresent)
  have hdecoyCold : Expressible L (.atom decoy) := by
    exact Expressible.atom hdecoyPresent
  have hdescWarm : Expressible (Promote L seed) (.op (.atom seed)) :=
    promotion_enables_descendant L seed
  have hdescCold : ¬ Expressible L (.op (.atom seed)) :=
    ancestral_ablation_blocks_descendant L seed hseedMissing
  constructor
  · simp [boundedSearch, hdecoyWarm, hdecoyReject, hdescWarm, hdescAccept]
  · simp [boundedSearch, hdecoyCold, hdecoyReject, hdescCold]

/-- Exact matched-budget causal statement: the verifier, candidate ordering,
    budget, and search algorithm are identical cold and warm.  Only promotion
    of the verified ancestor changes the language filter, which changes the
    returned search result. -/
theorem verified_promotion_changes_frozen_multicandidate_capability
    {A : Type u}
    (L : Lang A) (seed decoy : A) (verify : Expr A → Prop)
    (hseedMissing : ¬ L seed)
    (hdecoyPresent : L decoy)
    (hdecoyReject : ¬ verify (.atom decoy))
    (hdescAccept : verify (.op (.atom seed))) :
    boundedSearch (Promote L seed) verify 2
        [.atom decoy, .op (.atom seed)] = some (.op (.atom seed)) ∧
    boundedSearch L verify 2
        [.atom decoy, .op (.atom seed)] = none := by
  exact promotion_changes_two_candidate_search
    L seed decoy verify hseedMissing hdecoyPresent hdecoyReject hdescAccept

end MultiCandidateDevelopmentalSearch

#check MultiCandidateDevelopmentalSearch.boundedSearch
#check MultiCandidateDevelopmentalSearch.promotion_changes_two_candidate_search
#check MultiCandidateDevelopmentalSearch.verified_promotion_changes_frozen_multicandidate_capability
