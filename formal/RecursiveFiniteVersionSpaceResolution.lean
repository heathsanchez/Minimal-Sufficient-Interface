import ExecutablePairSelectionFromFiniteVersionSpace

namespace RecursiveFiniteVersionSpaceResolution

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture
open VerifiedVersionSpaceContraction
open ExecutablePairSelectionFromFiniteVersionSpace

/-- Keep exactly the repairs whose prediction matches the verified truth on `f`. -/
def filterRepairs
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (f : F) : List (Repair I) → List (Repair I)
  | [] => []
  | R :: rs =>
      if B.predict R f = truth f then
        R :: filterRepairs B truth f rs
      else
        filterRepairs B truth f rs

/-- Filtering never increases the number of live repair candidates. -/
theorem filterRepairs_length_le
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (f : F) :
    ∀ rs : List (Repair I),
      (filterRepairs B truth f rs).length ≤ rs.length := by
  intro rs
  induction rs with
  | nil => simp [filterRepairs]
  | cons R tail ih =>
      by_cases h : B.predict R f = truth f
      · simp [filterRepairs, h, ih]
      · simp [filterRepairs, h]
        exact Nat.le_trans ih (Nat.le_succ _)

/-- If a live candidate disagrees with the verified outcome, filtering strictly
    decreases the finite version space. -/
theorem filterRepairs_length_lt_of_rejected
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (f : F) :
    ∀ {rs : List (Repair I)} {R : Repair I},
      R ∈ rs → B.predict R f ≠ truth f →
      (filterRepairs B truth f rs).length < rs.length := by
  intro rs R hmem hrejected
  induction rs with
  | nil => simp at hmem
  | cons A tail ih =>
      rcases List.mem_cons.mp hmem with hRA | htail
      · subst A
        simp [filterRepairs, hrejected]
        exact Nat.lt_succ_of_le (filterRepairs_length_le B truth f tail)
      · by_cases hA : B.predict A f = truth f
        · simp [filterRepairs, hA]
          exact ih htail
        · simp [filterRepairs, hA]
          exact Nat.lt_succ_of_le (filterRepairs_length_le B truth f tail)

/-- Every ambiguity returned by the autonomous scan has at least one live
    candidate rejected by the verified Boolean outcome. -/
theorem scan_step_strictly_decreases
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool)
    {rs : List (Repair I)} {R₁ R₂ : Repair I} {f : F}
    (hscan : firstUnresolvedPair B rs = some (R₁, R₂, f)) :
    (filterRepairs B truth f rs).length < rs.length := by
  rcases firstUnresolvedPair_sound B hscan with ⟨h₁, h₂, hdiff⟩
  by_cases hmatch : B.predict R₁ f = truth f
  · have hreject : B.predict R₂ f ≠ truth f := by
      intro h₂match
      exact hdiff (hmatch.trans h₂match.symm)
    exact filterRepairs_length_lt_of_rejected B truth f h₂ hreject
  · exact filterRepairs_length_lt_of_rejected B truth f h₁ hmatch

/-- Fuelled executable developmental resolution. The system itself selects the
    unresolved pair and future; the external verifier contributes only truth. -/
def resolveFuel
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) : Nat → List (Repair I) → List (Repair I)
  | 0, rs => rs
  | n + 1, rs =>
      match firstUnresolvedPair B rs with
      | none => rs
      | some (_, _, f) => resolveFuel B truth n (filterRepairs B truth f rs)

/-- If the available fuel dominates the current candidate count, the recursive
    resolver necessarily stops at a consequentially confluent version space. -/
theorem resolveFuel_reaches_confluence
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) :
    ∀ (n : Nat) (rs : List (Repair I)),
      rs.length ≤ n →
      firstUnresolvedPair B (resolveFuel B truth n rs) = none := by
  intro n
  induction n with
  | zero =>
      intro rs hlen
      have hempty : rs = [] := by
        cases rs with
        | nil => rfl
        | cons R tail => simp at hlen
      subst rs
      simp [resolveFuel, firstUnresolvedPair]
  | succ n ih =>
      intro rs hlen
      cases hscan : firstUnresolvedPair B rs with
      | none =>
          simp [resolveFuel, hscan]
      | some triple =>
          rcases triple with ⟨R₁, R₂, f⟩
          have hlt : (filterRepairs B truth f rs).length < rs.length :=
            scan_step_strictly_decreases B truth hscan
          have hle : (filterRepairs B truth f rs).length ≤ n := by
            exact Nat.le_of_lt_succ (Nat.lt_of_lt_of_le hlt hlen)
          simpa [resolveFuel, hscan] using ih (filterRepairs B truth f rs) hle

/-- The canonical finite resolver uses exactly the initial candidate count as
    fuel; no externally chosen iteration bound is required. -/
def resolve
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (rs : List (Repair I)) : List (Repair I) :=
  resolveFuel B truth rs.length rs

/-- Cycle 12: every finite version space reaches one consequential class under
    the same autonomous query/filter cycle. -/
theorem recursive_finite_resolution_terminates_at_confluence
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (rs : List (Repair I)) :
    firstUnresolvedPair B (resolve B truth rs) = none := by
  exact resolveFuel_reaches_confluence B truth rs.length rs (Nat.le_refl _)

/-- Therefore all repairs surviving the recursive cycle are behaviourally
    equivalent under the complete faithful future interface. -/
theorem recursive_survivors_are_consequentially_equivalent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (truth : F → Bool) (rs : List (Repair I)) :
    ∀ R₁, R₁ ∈ resolve B truth rs →
    ∀ R₂, R₂ ∈ resolve B truth rs →
      RepairEquivalent futureOf R₁ R₂ := by
  exact firstUnresolvedPair_none_implies_confluent B
    (recursive_finite_resolution_terminates_at_confluence B truth rs)

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness
open FiniteExecutableDistinguishingFuture.Witness

/-- The concrete two-repair ambiguity resolves to the verifier-consistent class. -/
def truth : Fut → Bool
  | .alpha => true
  | .beta => false

theorem recursive_resolution_keeps_left :
    resolve basis truth [leftRepair, rightRepair] = [leftRepair] := by
  classical
  simp [resolve, resolveFuel, firstUnresolvedPair, firstAgainst,
    FiniteExecutableDistinguishingFuture.Witness.computes_alpha,
    filterRepairs, truth,
    FiniteExecutableDistinguishingFuture.Witness.basis,
    leftRepair, rightRepair]

end Witness

#check filterRepairs
#check filterRepairs_length_le
#check filterRepairs_length_lt_of_rejected
#check scan_step_strictly_decreases
#check resolveFuel
#check resolveFuel_reaches_confluence
#check resolve
#check recursive_finite_resolution_terminates_at_confluence
#check recursive_survivors_are_consequentially_equivalent
#check Witness.recursive_resolution_keeps_left

end RecursiveFiniteVersionSpaceResolution
