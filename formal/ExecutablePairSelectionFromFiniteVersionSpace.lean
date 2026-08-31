import VerifiedVersionSpaceContraction

namespace ExecutablePairSelectionFromFiniteVersionSpace

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture
open VerifiedVersionSpaceContraction

/-- Boolean behavioral agreement induced by a certified finite future
    interface. This is the executable presentation of consequential equivalence. -/
def PredictEquivalent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R₁ R₂ : Repair I) : Prop :=
  ∀ f, B.predict R₁ f = B.predict R₂ f

/-- Faithfulness makes Boolean prediction equivalence exactly semantic repair
    equivalence. -/
theorem predictEquivalent_iff_repairEquivalent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R₁ R₂ : Repair I) :
    PredictEquivalent B R₁ R₂ ↔ RepairEquivalent futureOf R₁ R₂ := by
  constructor
  · intro hp f
    constructor
    · intro h₁
      have hb₁ : B.predict R₁ f = true := (B.faithful R₁ f).2 h₁
      have hb₂ : B.predict R₂ f = true := by
        rw [← hp f]
        exact hb₁
      exact (B.faithful R₂ f).1 hb₂
    · intro h₂
      have hb₂ : B.predict R₂ f = true := (B.faithful R₂ f).2 h₂
      have hb₁ : B.predict R₁ f = true := by
        rw [hp f]
        exact hb₂
      exact (B.faithful R₁ f).1 hb₁
  · intro hs f
    cases h₁ : B.predict R₁ f <;> cases h₂ : B.predict R₂ f
    · rfl
    · exfalso
      have hr₂ : RepairReachable futureOf R₂ f :=
        (B.faithful R₂ f).1 h₂
      have hr₁ : RepairReachable futureOf R₁ f := (hs f).2 hr₂
      have : B.predict R₁ f = true := (B.faithful R₁ f).2 hr₁
      simp [h₁] at this
    · exfalso
      have hr₁ : RepairReachable futureOf R₁ f :=
        (B.faithful R₁ f).1 h₁
      have hr₂ : RepairReachable futureOf R₂ f := (hs f).1 hr₁
      have : B.predict R₂ f = true := (B.faithful R₂ f).2 hr₂
      simp [h₂] at this
    · rfl

/-- Search one fixed repair against a list of alternatives. The returned pair
    is accompanied by a future on which the two predictions differ. -/
def firstAgainst
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R : Repair I) : List (Repair I) → Option (Repair I × F)
  | [] => none
  | S :: ss =>
      match firstDistinguishingFuture B R S with
      | some f => some (S, f)
      | none => firstAgainst B R ss

/-- If `firstAgainst` returns a repair/future pair, the repair came from the
    supplied candidate tail and the future really distinguishes it from R. -/
theorem firstAgainst_sound
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R : Repair I) :
    ∀ {ss : List (Repair I)} {S : Repair I} {f : F},
      firstAgainst B R ss = some (S, f) →
      S ∈ ss ∧ B.predict R f ≠ B.predict S f := by
  intro ss
  induction ss with
  | nil =>
      intro S f h
      simp [firstAgainst] at h
  | cons A as ih =>
      intro S f h
      cases hq : firstDistinguishingFuture B R A with
      | some q =>
          simp [firstAgainst, hq] at h
          rcases h with ⟨rfl, rfl⟩
          have hs := (firstDifference_sound
            (B.predict R) (B.predict A) B.questions q hq).2
          exact ⟨by simp, hs⟩
      | none =>
          simp [firstAgainst, hq] at h
          rcases ih h with ⟨hmem, hdiff⟩
          exact ⟨by simp [hmem], hdiff⟩

/-- Failure against a list means R agrees with every listed repair on every
    future in the certified complete basis. -/
theorem firstAgainst_none_implies_equivalent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (R : Repair I) :
    ∀ {ss : List (Repair I)},
      firstAgainst B R ss = none →
      ∀ S, S ∈ ss → PredictEquivalent B R S := by
  intro ss
  induction ss with
  | nil =>
      intro _ S hmem
      simp at hmem
  | cons A as ih =>
      intro hnone S hmem
      cases hq : firstDistinguishingFuture B R A with
      | some q => simp [firstAgainst, hq] at hnone
      | none =>
          have htail : firstAgainst B R as = none := by
            simpa [firstAgainst, hq] using hnone
          rcases List.mem_cons.mp hmem with rfl | hS
          · intro f
            by_contra hdiff
            have hsem : ¬ RepairEquivalent futureOf R A := by
              intro hEq
              have hp := (predictEquivalent_iff_repairEquivalent B R A).2 hEq
              exact hdiff (hp f)
            rcases executable_search_finds_separator B hsem with ⟨q, hfind, _⟩
            rw [hq] at hfind
            cases hfind
          · exact ih htail S hS

/-- Scan an entire finite repair list. No pair is supplied. -/
def firstUnresolvedPair
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf) :
    List (Repair I) → Option (Repair I × Repair I × F)
  | [] => none
  | R :: rs =>
      match firstAgainst B R rs with
      | some (S, f) => some (R, S, f)
      | none => firstUnresolvedPair B rs

/-- A returned triple consists solely of candidates from the finite version
    space, and the returned future genuinely separates them. -/
theorem firstUnresolvedPair_sound
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf) :
    ∀ {rs : List (Repair I)} {R₁ R₂ : Repair I} {f : F},
      firstUnresolvedPair B rs = some (R₁, R₂, f) →
      R₁ ∈ rs ∧ R₂ ∈ rs ∧ B.predict R₁ f ≠ B.predict R₂ f := by
  intro rs
  induction rs with
  | nil =>
      intro R₁ R₂ f h
      simp [firstUnresolvedPair] at h
  | cons R tail ih =>
      intro R₁ R₂ f h
      cases ha : firstAgainst B R tail with
      | some p =>
          rcases p with ⟨S, q⟩
          simp [firstUnresolvedPair, ha] at h
          rcases h with ⟨rfl, rfl, rfl⟩
          rcases firstAgainst_sound B R ha with ⟨hS, hdiff⟩
          exact ⟨by simp, by simp [hS], hdiff⟩
      | none =>
          simp [firstUnresolvedPair, ha] at h
          rcases ih h with ⟨h₁, h₂, hdiff⟩
          exact ⟨by simp [h₁], by simp [h₂], hdiff⟩

/-- If the scan returns none, every candidate in the finite version space is in
    the same consequential class. -/
theorem firstUnresolvedPair_none_implies_confluent
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf) :
    ∀ {rs : List (Repair I)},
      firstUnresolvedPair B rs = none →
      ∀ R₁, R₁ ∈ rs → ∀ R₂, R₂ ∈ rs →
        RepairEquivalent futureOf R₁ R₂ := by
  intro rs
  induction rs with
  | nil =>
      intro _ R₁ h₁
      simp at h₁
  | cons R tail ih =>
      intro hnone R₁ h₁ R₂ h₂
      cases ha : firstAgainst B R tail with
      | some p => simp [firstUnresolvedPair, ha] at hnone
      | none =>
          have hrec : firstUnresolvedPair B tail = none := by
            simpa [firstUnresolvedPair, ha] using hnone
          have hRtail := firstAgainst_none_implies_equivalent B R ha
          rcases List.mem_cons.mp h₁ with rfl | h₁t
          · rcases List.mem_cons.mp h₂ with rfl | h₂t
            · intro f; exact Iff.rfl
            · exact (predictEquivalent_iff_repairEquivalent B R R₂).1
                (hRtail R₂ h₂t)
          · rcases List.mem_cons.mp h₂ with rfl | h₂t
            · have hEq : RepairEquivalent futureOf R R₁ :=
                (predictEquivalent_iff_repairEquivalent B R R₁).1
                  (hRtail R₁ h₁t)
              intro f
              exact (hEq f).symm
            · exact ih hrec R₁ h₁t R₂ h₂t

/-- Therefore genuine multi-class ambiguity forces the executable scan to find
    its own pair and its own distinguishing future. -/
theorem multiclasse_ambiguity_forces_pair_selection
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (rs : List (Repair I))
    (hamb : ∃ R₁, R₁ ∈ rs ∧ ∃ R₂, R₂ ∈ rs ∧
      ¬ RepairEquivalent futureOf R₁ R₂) :
    ∃ R₁ R₂ f,
      firstUnresolvedPair B rs = some (R₁, R₂, f) ∧
      R₁ ∈ rs ∧ R₂ ∈ rs ∧
      B.predict R₁ f ≠ B.predict R₂ f := by
  cases hscan : firstUnresolvedPair B rs with
  | some triple =>
      rcases triple with ⟨R₁, R₂, f⟩
      rcases firstUnresolvedPair_sound B hscan with ⟨h₁, h₂, hdiff⟩
      exact ⟨R₁, R₂, f, hscan, h₁, h₂, hdiff⟩
  | none =>
      exfalso
      rcases hamb with ⟨R₁, h₁, R₂, h₂, hneq⟩
      exact hneq (firstUnresolvedPair_none_implies_confluent B hscan R₁ h₁ R₂ h₂)

/-- The selected triple immediately drives strict contraction of the finite
    version space under every external verifier outcome. -/
theorem autonomous_finite_ambiguity_step
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (rs : List (Repair I))
    {R₁ R₂ : Repair I} {f : F}
    (hscan : firstUnresolvedPair B rs = some (R₁, R₂, f)) :
    ∀ outcome : Bool,
      StrictContraction
        (FilterAt B (fun R => R ∈ rs) f outcome)
        (fun R => R ∈ rs) := by
  intro outcome
  rcases firstUnresolvedPair_sound B hscan with ⟨h₁, h₂, hdiff⟩
  constructor
  · intro R hR
    exact hR.1
  · rcases unequal_predictions_exactly_one_matches hdiff with hleft | hright
    · by_cases hout : B.predict R₁ f = outcome
      · have hnot : B.predict R₂ f ≠ outcome := by
          intro h₂out
          exact hleft.2 (h₂out.trans hout.symm)
        exact ⟨R₂, h₂, by
          intro hs
          exact hnot hs.2⟩
      · exact ⟨R₁, h₁, by
          intro hs
          exact hout hs.2⟩
    · by_cases hout : B.predict R₂ f = outcome
      · have hnot : B.predict R₁ f ≠ outcome := by
          intro h₁out
          exact hright.2 (h₁out.trans hout.symm)
        exact ⟨R₁, h₁, by
          intro hs
          exact hnot hs.2⟩
      · exact ⟨R₂, h₂, by
          intro hs
          exact hout hs.2⟩

/-- Cycle-11 conclusion: in a finite version space with a certified finite
    future interface, no pair selector is needed. Either the scan returns none,
    certifying one consequential class, or it autonomously returns a conflicting
    pair and a distinguishing future whose verified outcome strictly contracts
    the version space. -/
theorem finite_version_space_self_selects_its_next_experiment
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (rs : List (Repair I)) :
    (firstUnresolvedPair B rs = none ∧
      ∀ R₁, R₁ ∈ rs → ∀ R₂, R₂ ∈ rs →
        RepairEquivalent futureOf R₁ R₂) ∨
    (∃ R₁ R₂ f,
      firstUnresolvedPair B rs = some (R₁, R₂, f) ∧
      ∀ outcome : Bool,
        StrictContraction
          (FilterAt B (fun R => R ∈ rs) f outcome)
          (fun R => R ∈ rs)) := by
  cases hscan : firstUnresolvedPair B rs with
  | none =>
      left
      exact ⟨hscan, firstUnresolvedPair_none_implies_confluent B hscan⟩
  | some triple =>
      right
      rcases triple with ⟨R₁, R₂, f⟩
      exact ⟨R₁, R₂, f, hscan, autonomous_finite_ambiguity_step B rs hscan⟩

#check PredictEquivalent
#check predictEquivalent_iff_repairEquivalent
#check firstAgainst
#check firstAgainst_sound
#check firstAgainst_none_implies_equivalent
#check firstUnresolvedPair
#check firstUnresolvedPair_sound
#check firstUnresolvedPair_none_implies_confluent
#check multiclasse_ambiguity_forces_pair_selection
#check autonomous_finite_ambiguity_step
#check finite_version_space_self_selects_its_next_experiment

end ExecutablePairSelectionFromFiniteVersionSpace
