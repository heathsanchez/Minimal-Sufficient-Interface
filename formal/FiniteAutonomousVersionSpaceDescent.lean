import RecursiveFiniteVersionSpaceResolution

namespace FiniteAutonomousVersionSpaceDescent

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture
open VerifiedVersionSpaceContraction
open ExecutablePairSelectionFromFiniteVersionSpace

/-- Executable filtering of a finite repair version space by one verified
    Boolean future outcome. This is the same certified recursive filter used by
    the preceding finite-resolution theorem, specialized to a constant outcome
    at the selected future. -/
def filterRepairs
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (f : F) (outcome : Bool) (rs : List (Repair I)) : List (Repair I) :=
  RecursiveFiniteVersionSpaceResolution.filterRepairs B (fun _ => outcome) f rs

/-- Filtering never invents repairs. -/
theorem mem_filterRepairs_implies_mem
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (f : F) (outcome : Bool) :
    ∀ (rs : List (Repair I)) {R : Repair I},
      R ∈ filterRepairs B f outcome rs → R ∈ rs := by
  intro rs
  induction rs with
  | nil =>
      intro R h
      simp [filterRepairs, RecursiveFiniteVersionSpaceResolution.filterRepairs] at h
  | cons A tail ih =>
      intro R h
      by_cases hA : B.predict A f = outcome
      · simp only [filterRepairs,
          RecursiveFiniteVersionSpaceResolution.filterRepairs, hA, if_pos,
          List.mem_cons] at h
        rcases h with hRA | htail
        · exact Or.inl hRA
        · exact Or.inr (ih htail)
      · simp only [filterRepairs,
          RecursiveFiniteVersionSpaceResolution.filterRepairs, hA, if_neg] at h
        exact Or.inr (ih h)

/-- If one listed repair disagrees with the verified outcome, filtering strictly
    shortens the finite version space. This is the well-founded measure. -/
theorem filterRepairs_length_lt_of_eliminated
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (f : F) (outcome : Bool) (rs : List (Repair I))
    {R : Repair I}
    (hmem : R ∈ rs) (hbad : B.predict R f ≠ outcome) :
    (filterRepairs B f outcome rs).length < rs.length := by
  simpa [filterRepairs] using
    (RecursiveFiniteVersionSpaceResolution.filterRepairs_length_lt_of_rejected
      B (fun _ => outcome) f hmem hbad)

/-- A pair of unequal Boolean predictions guarantees that every external outcome
    eliminates at least one of the two repairs. -/
theorem one_of_separated_pair_is_eliminated
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    {R₁ R₂ : Repair I} {f : F}
    (hdiff : B.predict R₁ f ≠ B.predict R₂ f)
    (outcome : Bool) :
    (B.predict R₁ f ≠ outcome) ∨ (B.predict R₂ f ≠ outcome) := by
  rcases unequal_predictions_exactly_one_matches hdiff with h | h
  · exact Or.inr h.2
  · exact Or.inl h.2

/-- Therefore every nonterminal self-selected experiment strictly decreases the
    finite candidate-list length, regardless of which Boolean outcome the
    external verifier returns. -/
theorem self_selected_experiment_strictly_decreases_length
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (rs : List (Repair I))
    {R₁ R₂ : Repair I} {f : F}
    (hscan : firstUnresolvedPair B rs = some (R₁, R₂, f))
    (outcome : Bool) :
    (filterRepairs B f outcome rs).length < rs.length := by
  rcases firstUnresolvedPair_sound B hscan with ⟨h₁, h₂, hdiff⟩
  rcases one_of_separated_pair_is_eliminated B hdiff outcome with hbad | hbad
  · exact filterRepairs_length_lt_of_eliminated B f outcome rs h₁ hbad
  · exact filterRepairs_length_lt_of_eliminated B f outcome rs h₂ hbad

/-- The actual autonomous finite step: the version space selects its own pair and
    question; the external world contributes only the Boolean result for that
    question. -/
def autonomousStep
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    (rs : List (Repair I)) : List (Repair I) :=
  match firstUnresolvedPair B rs with
  | none => rs
  | some (_, _, f) => filterRepairs B f (truth f) rs

/-- Nonterminal autonomous steps strictly descend on list length. -/
theorem autonomousStep_strict_descent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    (rs : List (Repair I))
    {R₁ R₂ : Repair I} {f : F}
    (hscan : firstUnresolvedPair B rs = some (R₁, R₂, f)) :
    (autonomousStep B truth rs).length < rs.length := by
  simp [autonomousStep, hscan]
  exact self_selected_experiment_strictly_decreases_length
    B rs hscan (truth f)

/-- Terminality has semantic content: a self-scan returning none certifies that
    every surviving repair lies in one future-behavioural class. -/
theorem autonomous_terminal_is_consequentially_confluent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (rs : List (Repair I))
    (hscan : firstUnresolvedPair B rs = none) :
    ∀ R₁, R₁ ∈ rs → ∀ R₂, R₂ ∈ rs →
      RepairEquivalent futureOf R₁ R₂ := by
  exact firstUnresolvedPair_none_implies_confluent B hscan

/-- Every finite state is either already one consequential class, or the system
    computes an experiment whose verified outcome strictly decreases the
    natural-number measure `length`. Hence there can be no infinite sequence of
    nonterminal autonomous steps on a finite version space. -/
theorem finite_autonomous_descent_or_confluence
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    (rs : List (Repair I)) :
    (firstUnresolvedPair B rs = none ∧
      ∀ R₁, R₁ ∈ rs → ∀ R₂, R₂ ∈ rs →
        RepairEquivalent futureOf R₁ R₂) ∨
    (∃ R₁ R₂ f,
      firstUnresolvedPair B rs = some (R₁, R₂, f) ∧
      (autonomousStep B truth rs).length < rs.length) := by
  cases hscan : firstUnresolvedPair B rs with
  | none =>
      left
      exact ⟨rfl, autonomous_terminal_is_consequentially_confluent B rs hscan⟩
  | some triple =>
      right
      rcases triple with ⟨R₁, R₂, f⟩
      exact ⟨R₁, R₂, f, rfl, autonomousStep_strict_descent B truth rs hscan⟩

#check filterRepairs
#check mem_filterRepairs_implies_mem
#check filterRepairs_length_lt_of_eliminated
#check one_of_separated_pair_is_eliminated
#check self_selected_experiment_strictly_decreases_length
#check autonomousStep
#check autonomousStep_strict_descent
#check autonomous_terminal_is_consequentially_confluent
#check finite_autonomous_descent_or_confluence

end FiniteAutonomousVersionSpaceDescent
