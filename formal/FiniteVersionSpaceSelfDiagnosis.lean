import VerifiedVersionSpaceContraction

namespace FiniteVersionSpaceSelfDiagnosis

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture

/-- Scan one candidate against the remaining finite version space. -/
def firstSeparatorAgainst
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) (c : C) : List C → Option (C × F)
  | [] => none
  | d :: ds =>
      match firstDistinguishingFuture B (repairOf c) (repairOf d) with
      | some f => some (d, f)
      | none => firstSeparatorAgainst B repairOf c ds

/-- Scan the version space itself. No repair pair is supplied to this program. -/
def firstVersionSeparator
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) : List C → Option (C × C × F)
  | [] => none
  | c :: cs =>
      match firstSeparatorAgainst B repairOf c cs with
      | some (d, f) => some (c, d, f)
      | none => firstVersionSeparator B repairOf cs

/-- Behavioural equivalence forces equal executable predictions. -/
theorem prediction_equal_of_equivalent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    {R₁ R₂ : Repair I}
    (heq : RepairEquivalent futureOf R₁ R₂) (f : F) :
    B.predict R₁ f = B.predict R₂ f := by
  cases h₁ : B.predict R₁ f <;> cases h₂ : B.predict R₂ f
  · rfl
  · have hr₂ : RepairReachable futureOf R₂ f := (B.faithful R₂ f).1 h₂
    have hr₁ : RepairReachable futureOf R₁ f := (heq f).2 hr₂
    have ht : B.predict R₁ f = true := (B.faithful R₁ f).2 hr₁
    rw [h₁] at ht
    contradiction
  · have hr₁ : RepairReachable futureOf R₁ f := (B.faithful R₁ f).1 h₁
    have hr₂ : RepairReachable futureOf R₂ f := (heq f).1 hr₁
    have ht : B.predict R₂ f = true := (B.faithful R₂ f).2 hr₂
    rw [h₂] at ht
    contradiction
  · rfl

/-- If two predictors agree on every member of a finite question list, the
    executable first-difference scan returns no witness. -/
theorem firstDifference_none_of_agreement
    {F : Type} (left right : F → Bool) :
    ∀ qs : List F,
      (∀ f, f ∈ qs → left f = right f) →
      firstDifference left right qs = none := by
  intro qs hagree
  induction qs with
  | nil => rfl
  | cons a rest ih =>
      have ha : left a = right a := hagree a List.mem_cons_self
      simp [firstDifference, ha]
      apply ih
      intro f hf
      exact hagree f (List.mem_cons_of_mem a hf)

/-- On a complete faithful finite interface, search returns `none` exactly when
    the two repairs are consequentially equivalent. -/
theorem no_distinguishing_future_iff_equivalent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R₁ R₂ : Repair I) :
    firstDistinguishingFuture B R₁ R₂ = none ↔
      RepairEquivalent futureOf R₁ R₂ := by
  constructor
  · intro hnone
    by_cases heq : RepairEquivalent futureOf R₁ R₂
    · exact heq
    · rcases executable_search_finds_separator B heq with ⟨f, hfind, _⟩
      rw [hnone] at hfind
      contradiction
  · intro heq
    unfold firstDistinguishingFuture
    apply firstDifference_none_of_agreement
    intro f _
    exact prediction_equal_of_equivalent B heq f

/-- Failure to find anything against one candidate certifies equivalence to every
    remaining candidate, rather than mere search exhaustion. -/
theorem firstSeparatorAgainst_none_iff
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) (c : C) :
    ∀ cs : List C,
      firstSeparatorAgainst B repairOf c cs = none ↔
      ∀ d, d ∈ cs → RepairEquivalent futureOf (repairOf c) (repairOf d) := by
  intro cs
  induction cs with
  | nil => simp [firstSeparatorAgainst]
  | cons d ds ih =>
      cases hfd : firstDistinguishingFuture B (repairOf c) (repairOf d) with
      | none =>
          have hed : RepairEquivalent futureOf (repairOf c) (repairOf d) :=
            (no_distinguishing_future_iff_equivalent B _ _).1 hfd
          simp [firstSeparatorAgainst, hfd, ih, hed]
      | some f =>
          have hneq : ¬ RepairEquivalent futureOf (repairOf c) (repairOf d) := by
            intro heq
            have hp := prediction_equal_of_equivalent B heq f
            have hs := (firstDifference_sound
              (B.predict (repairOf c)) (B.predict (repairOf d))
              B.questions f hfd).2
            exact hs hp
          simp [firstSeparatorAgainst, hfd, hneq]

/-- Any successful one-against-rest scan returns a genuine executable
    disagreement with the fixed candidate. -/
theorem firstSeparatorAgainst_sound
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) (c : C) :
    ∀ {cs : List C} {d : C} {f : F},
      firstSeparatorAgainst B repairOf c cs = some (d, f) →
      B.predict (repairOf c) f ≠ B.predict (repairOf d) f := by
  intro cs
  induction cs with
  | nil =>
      intro d f h
      simp [firstSeparatorAgainst] at h
  | cons a rest ih =>
      intro d f h
      cases hfd : firstDistinguishingFuture B (repairOf c) (repairOf a) with
      | none =>
          simp [firstSeparatorAgainst, hfd] at h
          exact ih h
      | some g =>
          have hpair : (a, g) = (d, f) := by
            exact Option.some.inj (by simpa [firstSeparatorAgainst, hfd] using h)
          cases hpair
          exact (firstDifference_sound
            (B.predict (repairOf c)) (B.predict (repairOf a))
            B.questions g hfd).2

/-- Pairwise consequential confluence of a finite candidate list. -/
def PairwiseEquivalent
    {I F C : Type} {futureOf : I → F}
    (repairOf : C → Repair I) : List C → Prop
  | [] => True
  | c :: cs =>
      (∀ d, d ∈ cs → RepairEquivalent futureOf (repairOf c) (repairOf d)) ∧
      PairwiseEquivalent (futureOf := futureOf) repairOf cs

/-- The self-scan has an exact interpretation: `none` is a certificate that the
    entire finite version space has already collapsed to one consequential class. -/
theorem firstVersionSeparator_none_iff_pairwise
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) :
    ∀ cs : List C,
      firstVersionSeparator B repairOf cs = none ↔
      PairwiseEquivalent (futureOf := futureOf) repairOf cs := by
  intro cs
  induction cs with
  | nil => simp [firstVersionSeparator, PairwiseEquivalent]
  | cons c rest ih =>
      cases hscan : firstSeparatorAgainst B repairOf c rest with
      | none =>
          have hall := (firstSeparatorAgainst_none_iff B repairOf c rest).1 hscan
          simp [firstVersionSeparator, hscan, PairwiseEquivalent, ih, hall]
      | some df =>
          rcases df with ⟨d, f⟩
          have hnot : ¬ (∀ d, d ∈ rest → RepairEquivalent futureOf (repairOf c) (repairOf d)) := by
            intro hall
            have hnone := (firstSeparatorAgainst_none_iff B repairOf c rest).2 hall
            rw [hscan] at hnone
            contradiction
          simp [firstVersionSeparator, hscan, PairwiseEquivalent, hnot]

/-- Any separator returned by self-diagnosis is an actual executable
    consequential disagreement between two candidates from the scanned space. -/
theorem firstVersionSeparator_sound
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) :
    ∀ {cs : List C} {c d : C} {f : F},
      firstVersionSeparator B repairOf cs = some (c, d, f) →
      B.predict (repairOf c) f ≠ B.predict (repairOf d) f := by
  intro cs
  induction cs with
  | nil =>
      intro c d f h
      simp [firstVersionSeparator] at h
  | cons a rest ih =>
      intro c d f h
      cases hs : firstSeparatorAgainst B repairOf a rest with
      | none =>
          simp [firstVersionSeparator, hs] at h
          exact ih h
      | some df =>
          rcases df with ⟨b, g⟩
          have htriple : (a, b, g) = (c, d, f) := by
            exact Option.some.inj (by simpa [firstVersionSeparator, hs] using h)
          cases htriple
          exact firstSeparatorAgainst_sound B repairOf a hs

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness
open FiniteExecutableDistinguishingFuture.Witness

inductive Candidate where | left | right

def repairOf : Candidate → Repair Idx
  | .left => leftRepair
  | .right => rightRepair

def candidates : List Candidate := [.left, .right]

theorem self_scan_finds_alpha :
    firstVersionSeparator basis repairOf candidates =
      some (.left, .right, Fut.alpha) := by
  simp [candidates, firstVersionSeparator, firstSeparatorAgainst, repairOf,
    FiniteExecutableDistinguishingFuture.Witness.computes_alpha]

end Witness

/-- Cycle 11: a finite version space no longer requires an externally exhibited
    divergent pair. It scans itself. Either it returns a certified executable
    disagreement, or `none` certifies consequential confluence of the whole list. -/
theorem finite_version_space_self_diagnoses
    {I F C : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (repairOf : C → Repair I) (cs : List C) :
    (firstVersionSeparator B repairOf cs = none ↔
      PairwiseEquivalent (futureOf := futureOf) repairOf cs) := by
  exact firstVersionSeparator_none_iff_pairwise B repairOf cs

#check firstSeparatorAgainst
#check firstVersionSeparator
#check no_distinguishing_future_iff_equivalent
#check firstSeparatorAgainst_none_iff
#check firstSeparatorAgainst_sound
#check firstVersionSeparator_none_iff_pairwise
#check firstVersionSeparator_sound
#check Witness.self_scan_finds_alpha
#check finite_version_space_self_diagnoses

end FiniteVersionSpaceSelfDiagnosis
