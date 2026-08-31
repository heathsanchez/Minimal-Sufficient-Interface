import StageAwareAutonomousPairSelection

namespace StageAwareAutonomousResolution

open RequirementLandscapeCompletion
open CapabilityGeneratedFutureInterface
open CapabilityGeneratedFiniteFutureBasis
open VerifierDoesNotDeterminePointwiseRequirement
open StageAwareGeneratedFutureBasis
open StageAwareAutonomousPairSelection

/-- Keep exactly the live repairs whose prediction on the generated separator
    matches the externally verified Boolean outcome. No static future basis is
    involved in filtering. -/
def filterStageRepairs
    {I : Type}
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) (i : I) : List (Repair I) → List (Repair I)
  | [] => []
  | R :: rs =>
      if E.predict R i = truth i then
        R :: filterStageRepairs E truth i rs
      else
        filterStageRepairs E truth i rs

/-- Stage filtering never increases the live finite version space. -/
theorem filterStageRepairs_length_le
    {I : Type}
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) (i : I) :
    ∀ rs : List (Repair I),
      (filterStageRepairs E truth i rs).length ≤ rs.length := by
  intro rs
  induction rs with
  | nil => simp [filterStageRepairs]
  | cons R tail ih =>
      by_cases h : E.predict R i = truth i
      · simp [filterStageRepairs, h, ih]
      · simp [filterStageRepairs, h]
        exact Nat.le_trans ih (Nat.le_succ _)

/-- Any live repair rejected by verifier truth makes the list strictly smaller. -/
theorem filterStageRepairs_length_lt_of_rejected
    {I : Type}
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) (i : I) :
    ∀ {rs : List (Repair I)} {R : Repair I},
      R ∈ rs → E.predict R i ≠ truth i →
      (filterStageRepairs E truth i rs).length < rs.length := by
  intro rs R hmem hrejected
  induction rs with
  | nil => simp at hmem
  | cons A tail ih =>
      rcases List.mem_cons.mp hmem with hRA | htail
      · subst A
        simp [filterStageRepairs, hrejected]
        exact Nat.lt_succ_of_le (filterStageRepairs_length_le E truth i tail)
      · by_cases hA : E.predict A i = truth i
        · simp only [filterStageRepairs, hA, if_pos, List.length_cons,
            Nat.succ_lt_succ_iff]
          exact ih htail
        · simp only [filterStageRepairs, hA, if_neg, List.length_cons]
          exact Nat.lt_succ_of_le (filterStageRepairs_length_le E truth i tail)

/-- Every pair/future returned by the stage-aware global scan strictly contracts
    the finite version space for either possible verified Boolean outcome. -/
theorem stage_scan_step_strictly_decreases
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool)
    {rs : List (Repair I)} {R₁ R₂ : Repair I} {i : I}
    (hscan : firstStageUnresolvedPair C A Req E rs = some (R₁, R₂, i)) :
    (filterStageRepairs E truth i rs).length < rs.length := by
  rcases firstStageUnresolvedPair_sound C A Req E hscan with
    ⟨h₁, h₂, _, hdiff⟩
  by_cases hmatch : E.predict R₁ i = truth i
  · have hreject : E.predict R₂ i ≠ truth i := by
      intro h₂match
      exact hdiff (hmatch.trans h₂match.symm)
    exact filterStageRepairs_length_lt_of_rejected E truth i h₂ hreject
  · exact filterStageRepairs_length_lt_of_rejected E truth i h₁ hmatch

/-- Fuelled recursive developmental resolution. At every step the current
    generated future set is rescanned globally; the verifier supplies only
    Boolean truth for the autonomously selected reachable future. -/
def resolveStageFuel
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) : Nat → List (Repair I) → List (Repair I)
  | 0, rs => rs
  | n + 1, rs =>
      match firstStageUnresolvedPair C A Req E rs with
      | none => rs
      | some (_, _, i) =>
          resolveStageFuel C A Req E truth n
            (filterStageRepairs E truth i rs)

/-- Candidate-count fuel is sufficient because every nonterminal stage scan
    causes a strict list-length decrease. -/
theorem resolveStageFuel_reaches_confluence
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) :
    ∀ (n : Nat) (rs : List (Repair I)),
      rs.length ≤ n →
      firstStageUnresolvedPair C A Req E
        (resolveStageFuel C A Req E truth n rs) = none := by
  intro n
  induction n with
  | zero =>
      intro rs hlen
      have hempty : rs = [] := by
        cases rs with
        | nil => rfl
        | cons R tail => simp at hlen
      subst rs
      simp [resolveStageFuel, firstStageUnresolvedPair]
  | succ n ih =>
      intro rs hlen
      cases hscan : firstStageUnresolvedPair C A Req E rs with
      | none =>
          simp [resolveStageFuel, hscan]
      | some triple =>
          rcases triple with ⟨R₁, R₂, i⟩
          have hlt : (filterStageRepairs E truth i rs).length < rs.length :=
            stage_scan_step_strictly_decreases C A Req E truth hscan
          have hle : (filterStageRepairs E truth i rs).length ≤ n := by
            exact Nat.le_of_lt_succ (Nat.lt_of_lt_of_le hlt hlen)
          unfold resolveStageFuel
          rw [hscan]
          exact ih (filterStageRepairs E truth i rs) hle

/-- Canonical stage resolver: initial candidate count is the complete fuel
    budget, so no supplied iteration bound remains. -/
def resolveStage
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) (rs : List (Repair I)) : List (Repair I) :=
  resolveStageFuel C A Req E truth rs.length rs

/-- Every finite stage-aware developmental resolution terminates with no
    unresolved pair among the futures generated at that stage. -/
theorem recursive_stage_resolution_terminates_at_confluence
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) (rs : List (Repair I)) :
    firstStageUnresolvedPair C A Req E
      (resolveStage C A Req E truth rs) = none := by
  exact resolveStageFuel_reaches_confluence
    C A Req E truth rs.length rs (Nat.le_refl _)

/-- Hence every two surviving repairs agree on every future actually generated
    by the current verified capability state. -/
theorem recursive_stage_survivors_are_equivalent
    {I : Type} {Cap : I → Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (A : ExecutableCapabilityAvailability I Cap)
    (Req : ExecutableRequirementLandscape I Cap)
    (E : ExecutableCapabilitySemantics I)
    (truth : I → Bool) (rs : List (Repair I)) :
    ∀ R₁, R₁ ∈ resolveStage C A Req E truth rs →
    ∀ R₂, R₂ ∈ resolveStage C A Req E truth rs →
      StageEquivalent Req E R₁ R₂ := by
  exact firstStageUnresolvedPair_none_implies_confluent C A Req E
    (recursive_stage_resolution_terminates_at_confluence C A Req E truth rs)

namespace Witness

open StageAwareGeneratedFutureBasis.Witness
open StageAwareAutonomousPairSelection.Witness

def truth : Idx → Bool
  | .old => true
  | .fresh => true
  | .unrelated => false

/-- Before completion there is no generated separator, so recursive resolution
    leaves the two candidates untouched and immediately certifies confluence. -/
theorem before_resolution_is_terminal :
    resolveStage C A BeforeReq E truth candidates = candidates := by
  unfold resolveStage
  simp only [candidates, List.length_cons, List.length_nil]
  unfold resolveStageFuel
  rw [before_global_scan_none]

/-- After the residual-generated future appears, verifier truth on that
    autonomously selected future removes exactly the inconsistent right repair. -/
theorem fresh_filter_keeps_left :
    filterStageRepairs E truth .fresh candidates = [leftRepair] := by
  unfold candidates
  simp [filterStageRepairs, truth, E, leftRepair, rightRepair]

/-- The remaining singleton has no unresolved generated-future pair. -/
theorem singleton_stage_scan_none :
    firstStageUnresolvedPair C A R E [leftRepair] = none := by
  simp [firstStageUnresolvedPair, firstStageAgainst]

/-- The full post-completion stage-aware recursive resolver reconverges to the
    verifier-consistent surviving class. -/
theorem regenerated_resolution_reconverges :
    resolveStage C A R E truth candidates = [leftRepair] := by
  unfold resolveStage
  simp only [candidates, List.length_cons, List.length_nil]
  unfold resolveStageFuel
  rw [regenerated_global_scan_finds_fresh]
  rw [fresh_filter_keeps_left]
  unfold resolveStageFuel
  rw [singleton_stage_scan_none]

/-- Ablation suppresses reopening completely: the resolver again terminates
    without contracting the pre-completion candidate set. -/
theorem ablated_resolution_skips_reopening :
    resolveStage C A BeforeReq E truth candidates = candidates :=
  before_resolution_is_terminal

end Witness

#check filterStageRepairs
#check filterStageRepairs_length_le
#check filterStageRepairs_length_lt_of_rejected
#check stage_scan_step_strictly_decreases
#check resolveStageFuel
#check resolveStageFuel_reaches_confluence
#check resolveStage
#check recursive_stage_resolution_terminates_at_confluence
#check recursive_stage_survivors_are_equivalent
#check Witness.before_resolution_is_terminal
#check Witness.fresh_filter_keeps_left
#check Witness.singleton_stage_scan_none
#check Witness.regenerated_resolution_reconverges
#check Witness.ablated_resolution_skips_reopening

end StageAwareAutonomousResolution
