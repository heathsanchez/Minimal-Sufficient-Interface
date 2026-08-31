import FailureGeneratedOmegaPlusOne
import BoundedDevelopmentalCapability

namespace PostLimitAttachedMinimalCapability

open FailureGeneratedOmegaPlusOne
open VerifiedConsequenceGenesis
open BoundedDevelopmentalCapability

abbrev Task := World × World

/-- The exact constraint certified by one residual: an admissible repair probe
    must distinguish the very pair that the current closure identifies. -/
def ResidualConstraint {C : Stage} (r : Failure C) (p : Probe) : Prop :=
  ¬ (p r.left ↔ p r.right)

/-- The residual-relative version space.  It deliberately retains every
    hypothesis satisfying the certified constraint rather than asserting that
    the residual uniquely determines a representation. -/
def VersionSpace {C : Stage} (r : Failure C) : Probe → Prop :=
  fun p => ResidualConstraint r p

/-- Retain exactly one proposed probe while preserving every old observation. -/
def adjoinProbe (C : Stage) (p : Probe) : Stage where
  coords := C.coords
  generated := fun q => C.generated q ∨ q = p

def Extends (C T : Stage) : Prop :=
  (∀ k, C.coords k → T.coords k) ∧
  (∀ p, C.generated p → T.generated p)

theorem old_extends_adjoin (C : Stage) (p : Probe) :
    Extends C (adjoinProbe C p) := by
  constructor
  · intro k hk
    exact hk
  · intro q hq
    exact Or.inl hq

/-- Leastness of the repair at the retained-language level: every extension
    containing the old stage and the selected probe contains this adjoin. -/
theorem adjoin_is_least_extension
    (C T : Stage) (p : Probe)
    (hCT : Extends C T) (hp : T.generated p) :
    Extends (adjoinProbe C p) T := by
  constructor
  · intro k hk
    exact hCT.1 k hk
  · intro q hq
    rcases hq with hold | rfl
    · exact hCT.2 q hold
    · exact hp

theorem observes_adjoin_iff (C : Stage) (p q : Probe) :
    observes (adjoinProbe C p) q ↔ observes C q ∨ q = p := by
  constructor
  · intro h
    rcases h with hcoord | hgen
    · exact Or.inl (Or.inl hcoord)
    · rcases hgen with hold | hqp
      · exact Or.inl (Or.inr hold)
      · exact Or.inr hqp
  · intro h
    rcases h with hold | hqp
    · rcases hold with hcoord | hgen
      · exact Or.inl hcoord
      · exact Or.inr (Or.inl hgen)
    · exact Or.inr (Or.inr hqp)

/-- Exact Golden Refinement at the semantic relation level: adjoining one
    consequence intersects the old observational identity with its kernel. -/
theorem agrees_adjoin_iff (C : Stage) (p : Probe) (x y : World) :
    agrees (adjoinProbe C p) x y ↔
      agrees C x y ∧ (p x ↔ p y) := by
  constructor
  · intro h
    constructor
    · intro q hq
      exact h q ((observes_adjoin_iff C p q).2 (Or.inl hq))
    · exact h p ((observes_adjoin_iff C p p).2 (Or.inr rfl))
  · rintro ⟨hold, hp⟩ q hq
    rcases (observes_adjoin_iff C p q).1 hq with hOld | rfl
    · exact hold q hOld
    · exact hp

/-- The failure-generated probe is a member of the exact residual-relative
    version space; no candidate name or pool position is used. -/
theorem generatedProbe_in_versionSpace {C : Stage} (r : Failure C) :
    VersionSpace r (generatedProbe r) := by
  simp [VersionSpace, ResidualConstraint, generatedProbe, r.distinct]

def Attached {C : Stage} (r : Failure C) (p : Probe) : Prop :=
  observes (adjoinProbe C p) p ∧ ResidualConstraint r p

theorem generatedProbe_attaches {C : Stage} (r : Failure C) :
    Attached r (generatedProbe r) := by
  exact ⟨(observes_adjoin_iff C (generatedProbe r) (generatedProbe r)).2
      (Or.inr rfl),
    generatedProbe_in_versionSpace r⟩

/-- One-observation resource horizon.  A task is reachable exactly when one
    retained probe separates its endpoints. -/
def ReachableOne (C : Stage) (t : Task) : Prop :=
  ∃ p, observes C p ∧ ¬ (p t.1 ↔ p t.2)

def FutureOne (C : Stage) : Task → Prop := ReachableOne C

theorem future_monotone_adjoin (C : Stage) (p : Probe) (t : Task) :
    FutureOne C t → FutureOne (adjoinProbe C p) t := by
  rintro ⟨q, hq, hsep⟩
  exact ⟨q, (observes_adjoin_iff C p q).2 (Or.inl hq), hsep⟩

def postLimitResidual (w : World) : Failure omegaStage := omegaFailure w
def postLimitProbe (w : World) : Probe := generatedProbe (postLimitResidual w)
def postLimitRepair (w : World) : Stage :=
  adjoinProbe omegaStage (postLimitProbe w)
def postLimitTask (w : World) : Task := (toggle w, w)

theorem postLimit_task_unreachable_before (w : World) :
    ¬ ReachableOne omegaStage (postLimitTask w) := by
  rintro ⟨p, hp, hsep⟩
  rcases hp with ⟨k, _, rfl⟩ | h
  · apply hsep
    simp [postLimitTask, coord, toggle]
  · exact False.elim h

theorem postLimit_task_reachable_after (w : World) :
    ReachableOne (postLimitRepair w) (postLimitTask w) := by
  refine ⟨postLimitProbe w, ?_, ?_⟩
  · exact (observes_adjoin_iff omegaStage (postLimitProbe w)
      (postLimitProbe w)).2 (Or.inr rfl)
  · exact generatedProbe_in_versionSpace (postLimitResidual w)

/-- Fixed-horizon future capability strictly grows. -/
theorem postLimit_future_strictly_grows (w : World) :
    (∀ t, FutureOne omegaStage t → FutureOne (postLimitRepair w) t) ∧
    FutureOne (postLimitRepair w) (postLimitTask w) ∧
    ¬ FutureOne omegaStage (postLimitTask w) := by
  exact ⟨future_monotone_adjoin omegaStage (postLimitProbe w),
    postLimit_task_reachable_after w,
    postLimit_task_unreachable_before w⟩

/-- Exact repair ablation removes the capability. -/
theorem postLimit_repair_ablation (w : World) :
    ReachableOne (postLimitRepair w) (postLimitTask w) ∧
    ¬ ReachableOne omegaStage (postLimitTask w) :=
  ⟨postLimit_task_reachable_after w,
    postLimit_task_unreachable_before w⟩

/-- Behavioral retention quotient: syntax is identified by the induced
    agreement kernel, not by pointwise polarity or witness identity. -/
def SameBehavior (p q : Probe) : Prop :=
  ∀ x y, (p x ↔ p y) ↔ (q x ↔ q y)

def complement (p : Probe) : Probe := fun x => ¬ p x

theorem complement_same_behavior (p : Probe) :
    SameBehavior p (complement p) := by
  intro x y
  simp only [complement]
  tauto

theorem complement_is_also_in_versionSpace {C : Stage}
    (r : Failure C) (hp : VersionSpace r (generatedProbe r)) :
    VersionSpace r (complement (generatedProbe r)) := by
  intro h
  apply hp
  constructor
  · intro hl
    by_contra hn
    exact (h.mpr hn) hl
  · intro hr
    by_contra hn
    exact (h.mp hn) hr

/-- Retaining the generated probe is exactly language promotion. -/
theorem repair_language_eq_promotion (w : World) :
    (postLimitRepair w).generated =
      Promote omegaStage.generated (postLimitProbe w) := by
  funext q
  apply propext
  simp [postLimitRepair, adjoinProbe, Promote]

def acceptsPostLimitDescendant (w : World) : Expr Probe → Prop :=
  fun e => e = .op (.atom (postLimitProbe w))

/-- The same one-query controller and verifier fail before retention and
    succeed after it.  The resource horizon is unchanged. -/
theorem postLimit_changes_one_query_capability (w : World) :
    oneQueryController (postLimitRepair w).generated
        (postLimitProbe w) (acceptsPostLimitDescendant w) =
          some (.op (.atom (postLimitProbe w))) ∧
    oneQueryController omegaStage.generated
        (postLimitProbe w) (acceptsPostLimitDescendant w) = none := by
  have hmissing : ¬ omegaStage.generated (postLimitProbe w) := by
    simp [omegaStage]
  have hverify : acceptsPostLimitDescendant w
      (.op (.atom (postLimitProbe w))) := rfl
  have h := promotion_changes_one_query_controller
    omegaStage.generated (postLimitProbe w)
    (acceptsPostLimitDescendant w) hmissing hverify
  rw [repair_language_eq_promotion w]
  exact h

/-- Parametric source-distinct transfer: the same failure-to-probe-to-repair
    law closes the full attached bounded-capability cycle for any two runtime
    sources, with no shared endpoint witness required. -/
theorem source_distinct_transfer (w₁ w₂ : World) (hne : w₁ ≠ w₂) :
    (ReachableOne (postLimitRepair w₁) (postLimitTask w₁) ∧
      ¬ ReachableOne omegaStage (postLimitTask w₁)) ∧
    (ReachableOne (postLimitRepair w₂) (postLimitTask w₂) ∧
      ¬ ReachableOne omegaStage (postLimitTask w₂)) := by
  exact ⟨postLimit_repair_ablation w₁, postLimit_repair_ablation w₂⟩

/-- Integrated post-limit developmental certificate. -/
theorem exact_residual_forces_attached_minimal_bounded_capability (w : World) :
    let r := postLimitResidual w
    let p := postLimitProbe w
    let R := postLimitRepair w
    VersionSpace r p ∧
    Attached r p ∧
    (∀ T, Extends omegaStage T → T.generated p → Extends R T) ∧
    (∀ x y, agrees R x y ↔ agrees omegaStage x y ∧ (p x ↔ p y)) ∧
    (ReachableOne R (postLimitTask w) ∧
      ¬ ReachableOne omegaStage (postLimitTask w)) ∧
    ((∀ t, FutureOne omegaStage t → FutureOne R t) ∧
      FutureOne R (postLimitTask w) ∧
      ¬ FutureOne omegaStage (postLimitTask w)) ∧
    oneQueryController R.generated p (acceptsPostLimitDescendant w) =
        some (.op (.atom p)) ∧
    oneQueryController omegaStage.generated p
        (acceptsPostLimitDescendant w) = none := by
  dsimp
  refine ⟨generatedProbe_in_versionSpace (postLimitResidual w),
    generatedProbe_attaches (postLimitResidual w), ?_, ?_,
    postLimit_repair_ablation w, postLimit_future_strictly_grows w,
    postLimit_changes_one_query_capability w⟩
  · intro T hExt hp
    exact adjoin_is_least_extension omegaStage T (postLimitProbe w) hExt hp
  · intro x y
    exact agrees_adjoin_iff omegaStage (postLimitProbe w) x y

#check generatedProbe_in_versionSpace
#check adjoin_is_least_extension
#check agrees_adjoin_iff
#check generatedProbe_attaches
#check postLimit_future_strictly_grows
#check postLimit_repair_ablation
#check complement_same_behavior
#check postLimit_changes_one_query_capability
#check source_distinct_transfer
#check exact_residual_forces_attached_minimal_bounded_capability

end PostLimitAttachedMinimalCapability
