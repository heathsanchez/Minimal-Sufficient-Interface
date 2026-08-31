import StageAwareGeneratedFutureBasis

namespace StageAwareAutonomousPairSelection

open RequirementLandscapeCompletion
open CapabilityGeneratedFutureInterface
open CapabilityGeneratedFiniteFutureBasis
open FiniteExecutableDistinguishingFuture
open VerifierDoesNotDeterminePointwiseRequirement
open StageAwareGeneratedFutureBasis

/-- Consequential agreement at a developmental stage quantifies only over
    futures that the current completed capability state actually generates. -/
def StageEquivalent
    {I : Type} {Cap : I → Type}
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R₁ R₂ : Repair I) : Prop :=
  ∀ i, generatedReachableAfter Req.semantic i →
    E.predict R₁ i = E.predict R₂ i

/-- Search two repairs only on the regenerated, stage-reachable future list. -/
def firstStageDifference
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R₁ R₂ : Repair I) : Option I :=
  firstDifference (E.predict R₁) (E.predict R₂)
    (questionsAfter C A Req)

/-- A returned stage separator is both genuinely reachable at this stage and
    behaviorally distinguishing. -/
theorem firstStageDifference_sound
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R₁ R₂ : Repair I) {i : I}
    (h : firstStageDifference C A Req E R₁ R₂ = some i) :
    generatedReachableAfter Req.semantic i ∧
      E.predict R₁ i ≠ E.predict R₂ i := by
  have hs := firstDifference_sound
    (E.predict R₁) (E.predict R₂) (questionsAfter C A Req) i h
  exact ⟨(mem_questionsAfter_iff C A Req i).1 hs.1, hs.2⟩

/-- If stage-relative search returns none, the repairs agree on every future
    actually generated at that stage. No unavailable index is smuggled in. -/
theorem firstStageDifference_none_implies_equivalent
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R₁ R₂ : Repair I)
    (hnone : firstStageDifference C A Req E R₁ R₂ = none) :
    StageEquivalent Req E R₁ R₂ := by
  intro i hi
  cases h₁ : E.predict R₁ i <;> cases h₂ : E.predict R₂ i
  · rfl
  · have hdiff : E.predict R₁ i ≠ E.predict R₂ i := by simp [h₁, h₂]
    have hex : ∃ j,
        firstDifference (E.predict R₁) (E.predict R₂)
          (questionsAfter C A Req) = some j :=
      firstDifference_complete
        (E.predict R₁) (E.predict R₂) (questionsAfter C A Req)
        ⟨i, (mem_questionsAfter_iff C A Req i).2 hi, hdiff⟩
    rcases hex with ⟨j, hj⟩
    have : firstStageDifference C A Req E R₁ R₂ = some j := hj
    rw [hnone] at this
    cases this
  · have hdiff : E.predict R₁ i ≠ E.predict R₂ i := by simp [h₁, h₂]
    have hex : ∃ j,
        firstDifference (E.predict R₁) (E.predict R₂)
          (questionsAfter C A Req) = some j :=
      firstDifference_complete
        (E.predict R₁) (E.predict R₂) (questionsAfter C A Req)
        ⟨i, (mem_questionsAfter_iff C A Req i).2 hi, hdiff⟩
    rcases hex with ⟨j, hj⟩
    have : firstStageDifference C A Req E R₁ R₂ = some j := hj
    rw [hnone] at this
    cases this
  · rfl

/-- Search one repair against the rest of a finite version space using only the
    current regenerated future set. -/
def firstStageAgainst
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R : Repair I) : List (Repair I) → Option (Repair I × I)
  | [] => none
  | S :: ss =>
      match firstStageDifference C A Req E R S with
      | some i => some (S, i)
      | none => firstStageAgainst C A Req E R ss

/-- Returned alternatives come from the supplied finite version space tail and
    carry a reachable generated separator. -/
theorem firstStageAgainst_sound
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R : Repair I) :
    ∀ {ss : List (Repair I)} {S : Repair I} {i : I},
      firstStageAgainst C A Req E R ss = some (S, i) →
      S ∈ ss ∧ generatedReachableAfter Req.semantic i ∧
        E.predict R i ≠ E.predict S i := by
  intro ss
  induction ss with
  | nil =>
      intro S i h
      simp [firstStageAgainst] at h
  | cons T ts ih =>
      intro S i h
      cases hd : firstStageDifference C A Req E R T with
      | some q =>
          simp [firstStageAgainst, hd] at h
          rcases h with ⟨rfl, rfl⟩
          rcases firstStageDifference_sound C A Req E R T hd with ⟨hreach, hsep⟩
          exact ⟨by simp, hreach, hsep⟩
      | none =>
          simp [firstStageAgainst, hd] at h
          rcases ih h with ⟨hmem, hreach, hsep⟩
          exact ⟨by simp [hmem], hreach, hsep⟩

/-- Failure against a tail means stage-relative agreement with every repair in
    that tail. -/
theorem firstStageAgainst_none_implies_equivalent
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (R : Repair I) :
    ∀ {ss : List (Repair I)},
      firstStageAgainst C A Req E R ss = none →
      ∀ S, S ∈ ss → StageEquivalent Req E R S := by
  intro ss
  induction ss with
  | nil =>
      intro _ S hmem
      simp at hmem
  | cons T ts ih =>
      intro hnone S hmem
      cases hd : firstStageDifference C A Req E R T with
      | some q =>
          simp [firstStageAgainst, hd] at hnone
      | none =>
          have htail : firstStageAgainst C A Req E R ts = none := by
            simpa [firstStageAgainst, hd] using hnone
          rcases List.mem_cons.mp hmem with hST | hS
          · subst S
            exact firstStageDifference_none_implies_equivalent C A Req E R T hd
          · exact ih htail S hS

/-- Scan the whole finite version space. No pair and no future are supplied. -/
def firstStageUnresolvedPair
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I) :
    List (Repair I) → Option (Repair I × Repair I × I)
  | [] => none
  | R :: rs =>
      match firstStageAgainst C A Req E R rs with
      | some (S, i) => some (R, S, i)
      | none => firstStageUnresolvedPair C A Req E rs

/-- A globally returned pair consists of candidates from the version space and
    a separator that is genuinely generated at this stage. -/
theorem firstStageUnresolvedPair_sound
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I) :
    ∀ {rs : List (Repair I)} {R₁ R₂ : Repair I} {i : I},
      firstStageUnresolvedPair C A Req E rs = some (R₁, R₂, i) →
      R₁ ∈ rs ∧ R₂ ∈ rs ∧ generatedReachableAfter Req.semantic i ∧
        E.predict R₁ i ≠ E.predict R₂ i := by
  intro rs
  induction rs with
  | nil =>
      intro R₁ R₂ i h
      simp [firstStageUnresolvedPair] at h
  | cons R tail ih =>
      intro R₁ R₂ i h
      cases ha : firstStageAgainst C A Req E R tail with
      | some p =>
          rcases p with ⟨S, q⟩
          simp [firstStageUnresolvedPair, ha] at h
          rcases h with ⟨rfl, rfl, rfl⟩
          rcases firstStageAgainst_sound C A Req E R ha with
            ⟨hS, hreach, hsep⟩
          exact ⟨by simp, by simp [hS], hreach, hsep⟩
      | none =>
          simp [firstStageUnresolvedPair, ha] at h
          rcases ih h with ⟨h₁, h₂, hreach, hsep⟩
          exact ⟨by simp [h₁], by simp [h₂], hreach, hsep⟩

/-- If the global scan returns none, all candidates are consequentially
    equivalent relative to exactly the generated futures of this stage. -/
theorem firstStageUnresolvedPair_none_implies_confluent
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I) :
    ∀ {rs : List (Repair I)},
      firstStageUnresolvedPair C A Req E rs = none →
      ∀ R₁, R₁ ∈ rs → ∀ R₂, R₂ ∈ rs → StageEquivalent Req E R₁ R₂ := by
  intro rs
  induction rs with
  | nil =>
      intro _ R₁ h₁
      simp at h₁
  | cons R tail ih =>
      intro hnone R₁ h₁ R₂ h₂
      cases ha : firstStageAgainst C A Req E R tail with
      | some p =>
          simp [firstStageUnresolvedPair, ha] at hnone
      | none =>
          have hrec : firstStageUnresolvedPair C A Req E tail = none := by
            simpa [firstStageUnresolvedPair, ha] using hnone
          have hRtail := firstStageAgainst_none_implies_equivalent C A Req E R ha
          rcases List.mem_cons.mp h₁ with hR₁R | h₁t
          · subst R₁
            rcases List.mem_cons.mp h₂ with hR₂R | h₂t
            · subst R₂
              intro i _
              rfl
            · exact hRtail R₂ h₂t
          · rcases List.mem_cons.mp h₂ with hR₂R | h₂t
            · subst R₂
              have hEq : StageEquivalent Req E R R₁ := hRtail R₁ h₁t
              intro i hi
              exact (hEq i hi).symm
            · exact ih hrec R₁ h₁t R₂ h₂t

namespace Witness

open StageAwareGeneratedFutureBasis.Witness

abbrev BeforeReq : ExecutableRequirementLandscape Idx Cap :=
  erasedExecutableRequirements

abbrev candidates : List (Repair Idx) := [leftRepair, rightRepair]

private theorem before_pair_difference_none :
    firstStageDifference C A BeforeReq E leftRepair rightRepair = none := by
  unfold firstStageDifference
  rw [ablation_preserves_question_list]
  exact old_scan_sees_no_difference

private theorem after_pair_difference_fresh :
    firstStageDifference C A R E leftRepair rightRepair = some .fresh := by
  exact regenerated_scan_finds_fresh

/-- Before capability completion, the global scan sees one consequential class. -/
theorem before_global_scan_none :
    firstStageUnresolvedPair C A BeforeReq E candidates = none := by
  simp [candidates, firstStageUnresolvedPair, firstStageAgainst,
    before_pair_difference_none]

/-- After verified residual completion regenerates the future basis, the same
    global scan autonomously finds the previously invisible pair and the new
    residual-generated future. -/
theorem regenerated_global_scan_finds_fresh :
    firstStageUnresolvedPair C A R E candidates =
      some (leftRepair, rightRepair, Idx.fresh) := by
  simp [candidates, firstStageUnresolvedPair, firstStageAgainst,
    after_pair_difference_fresh]

/-- The returned generated future is certified reachable and distinguishing. -/
theorem regenerated_global_scan_certificate :
    generatedReachableAfter R.semantic Idx.fresh ∧
      E.predict leftRepair Idx.fresh ≠ E.predict rightRepair Idx.fresh := by
  have hs := firstStageUnresolvedPair_sound C A R E
    regenerated_global_scan_finds_fresh
  exact ⟨hs.2.2.1, hs.2.2.2⟩

/-- Ablating the verifier requirement restores the pre-completion confluence
    certificate instead of leaving the new separator available. -/
theorem ablation_restores_global_confluence :
    ∀ R₁, R₁ ∈ candidates → ∀ R₂, R₂ ∈ candidates →
      StageEquivalent BeforeReq E R₁ R₂ := by
  exact firstStageUnresolvedPair_none_implies_confluent C A BeforeReq E
    before_global_scan_none

end Witness

#check StageEquivalent
#check firstStageDifference
#check firstStageDifference_sound
#check firstStageDifference_none_implies_equivalent
#check firstStageAgainst
#check firstStageAgainst_sound
#check firstStageUnresolvedPair
#check firstStageUnresolvedPair_sound
#check firstStageUnresolvedPair_none_implies_confluent
#check Witness.before_global_scan_none
#check Witness.regenerated_global_scan_finds_fresh
#check Witness.regenerated_global_scan_certificate
#check Witness.ablation_restores_global_confluence

end StageAwareAutonomousPairSelection
