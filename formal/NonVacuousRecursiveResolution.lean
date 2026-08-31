import RecursiveFiniteVersionSpaceResolution

namespace NonVacuousRecursiveResolution

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture
open ExecutablePairSelectionFromFiniteVersionSpace
open RecursiveFiniteVersionSpaceResolution

/-- A repair is globally realizable relative to verifier truth when it predicts
    the verified outcome at every future in the certified complete interface. -/
def TruthConsistent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (R : Repair I) : Prop :=
  ∀ f, B.predict R f = truth f

/-- A truth-consistent repair is never removed by filtering at one generated
    experiment. -/
theorem filterRepairs_preserves_truth_consistent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (f : F)
    {R : Repair I} :
    ∀ {rs : List (Repair I)},
      R ∈ rs → TruthConsistent B truth R →
      R ∈ filterRepairs B truth f rs := by
  intro rs hmem htruth
  induction rs with
  | nil => simp at hmem
  | cons A tail ih =>
      rcases List.mem_cons.mp hmem with hRA | htail
      · subst A
        simp [filterRepairs, htruth f]
      · by_cases hA : B.predict A f = truth f
        · simp [filterRepairs, hA]
          exact Or.inr (ih htail)
        · simp [filterRepairs, hA]
          exact ih htail

/-- The recursive resolver preserves every globally truth-consistent live
    repair, independent of which ambiguous pair/question it selects. -/
theorem resolveFuel_preserves_truth_consistent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    {R : Repair I} (htruth : TruthConsistent B truth R) :
    ∀ (n : Nat) {rs : List (Repair I)},
      R ∈ rs → R ∈ resolveFuel B truth n rs := by
  intro n
  induction n with
  | zero =>
      intro rs hmem
      simpa [resolveFuel] using hmem
  | succ n ih =>
      intro rs hmem
      cases hscan : firstUnresolvedPair B rs with
      | none =>
          simpa [resolveFuel, hscan] using hmem
      | some triple =>
          rcases triple with ⟨R₁, R₂, f⟩
          have hfiltered : R ∈ filterRepairs B truth f rs :=
            filterRepairs_preserves_truth_consistent B truth f hmem htruth
          simpa [resolveFuel, hscan] using ih hfiltered

/-- Therefore the canonical candidate-count-bounded resolver preserves every
    initially live repair consistent with verifier truth. -/
theorem resolve_preserves_truth_consistent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    (rs : List (Repair I)) {R : Repair I}
    (hmem : R ∈ rs) (htruth : TruthConsistent B truth R) :
    R ∈ resolve B truth rs := by
  exact resolveFuel_preserves_truth_consistent B truth htruth rs.length hmem

/-- Realizability of verifier truth inside the initial version space prevents
    the recursive process from converging vacuously to the empty version space. -/
theorem realizability_implies_nonempty_terminal_space
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    (rs : List (Repair I))
    (hreal : ∃ R, R ∈ rs ∧ TruthConsistent B truth R) :
    ∃ R, R ∈ resolve B truth rs := by
  rcases hreal with ⟨R, hmem, htruth⟩
  exact ⟨R, resolve_preserves_truth_consistent B truth rs hmem htruth⟩

/-- Cycle 13: under the minimal realizability assumption that verifier truth is
    represented by at least one initial candidate, autonomous recursive
    resolution terminates at a nonempty consequential class. -/
theorem recursive_resolution_reaches_nonempty_consequential_class
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    (rs : List (Repair I))
    (hreal : ∃ R, R ∈ rs ∧ TruthConsistent B truth R) :
    (∃ R, R ∈ resolve B truth rs) ∧
    (∀ R₁, R₁ ∈ resolve B truth rs →
      ∀ R₂, R₂ ∈ resolve B truth rs →
        RepairEquivalent futureOf R₁ R₂) := by
  constructor
  · exact realizability_implies_nonempty_terminal_space B truth rs hreal
  · exact recursive_survivors_are_consequentially_equivalent B truth rs

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness
open FiniteExecutableDistinguishingFuture.Witness
open RecursiveFiniteVersionSpaceResolution.Witness

/-- The concrete surviving left repair is globally consistent with the supplied
    verifier truth. -/
theorem left_truth_consistent : TruthConsistent basis truth leftRepair := by
  intro f
  cases f <;>
    simp [truth, basis, leftRepair]

/-- Hence the concrete Cycle-12 resolution is nonvacuous for the same structural
    reason as the generic theorem, not merely by direct computation. -/
theorem left_survives_by_invariant :
    leftRepair ∈ resolve basis truth [leftRepair, rightRepair] := by
  exact resolve_preserves_truth_consistent basis truth
    [leftRepair, rightRepair] (by simp) left_truth_consistent

end Witness

#check TruthConsistent
#check filterRepairs_preserves_truth_consistent
#check resolveFuel_preserves_truth_consistent
#check resolve_preserves_truth_consistent
#check realizability_implies_nonempty_terminal_space
#check recursive_resolution_reaches_nonempty_consequential_class
#check Witness.left_truth_consistent
#check Witness.left_survives_by_invariant

end NonVacuousRecursiveResolution
