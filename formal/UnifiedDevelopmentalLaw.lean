import Kernel
import MinimalRepair
import TypedBehaviouralCongruence
import DevelopmentalCategory
import GeneratedStage
import VerifiedConsequenceGenesis

universe u v w z

namespace UnifiedDevelopmentalLaw

open MeetKernel
open MinimalRepair
open TypedBehaviouralCongruence
open DevelopmentalCategory
open GeneratedStage
open VerifiedConsequenceGenesis

/-- Binary relations ordered by refinement form the concrete meet kernel in
which adding a consequential distinction is intersection of kernels. -/
def relationMeetKernel (X : Type u) : MeetKernel (X → X → Prop) where
  meet := fun R S x y => R x y ∧ S x y
  idem := by
    intro R
    funext x y
    apply propext
    constructor
    · intro h; exact h.1
    · intro h; exact ⟨h, h⟩
  comm := by
    intro R S
    funext x y
    apply propext
    constructor
    · intro h; exact ⟨h.2, h.1⟩
    · intro h; exact ⟨h.2, h.1⟩
  assoc := by
    intro R S T
    funext x y
    apply propext
    constructor
    · intro h; exact ⟨h.1.1, h.1.2, h.2⟩
    · intro h; exact ⟨⟨h.1, h.2.1⟩, h.2.2⟩

/-- Equality induced by a concrete representation. -/
def EqRel {X : Type u} {R : Type v} (q : X → R) : X → X → Prop :=
  fun x y => q x = q y

/-- Kernel relation of one consequence. -/
def ConsequenceKernel {X : Type u} {Y : Type v} (c : X → Y) : X → X → Prop :=
  fun x y => c x = c y

/-- Equality induced by the canonical factorization repair. -/
def RefinedEqRel {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) : X → X → Prop :=
  EqRel (RefineWith q c)

/-- The product repair `(q,c)` and the meet/intersection repair are literally
    the same refinement at the level of state identifications. This is the
    bridge between the factorization theorem and the abstract MSI meet law. -/
theorem canonical_refinement_eq_meet
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) :
    RefinedEqRel q c =
      (relationMeetKernel X).meet (EqRel q) (ConsequenceKernel c) := by
  funext x y
  apply propext
  constructor
  · intro h
    exact ⟨congrArg Prod.fst h, congrArg Prod.snd h⟩
  · rintro ⟨hq, hc⟩
    exact Prod.ext hq hc

/-- Therefore the factorization repair inherits the abstract unique
    least-change meet universal property: it refines the old representation
    and the new consequence kernel, and every competing common refinement is
    at least as fine. -/
theorem canonical_factorization_repair_is_minimal_meet
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) :
    let K := relationMeetKernel X
    K.Le (RefinedEqRel q c) (EqRel q) ∧
    K.Le (RefinedEqRel q c) (ConsequenceKernel c) ∧
    ∀ T, K.Le T (EqRel q) → K.Le T (ConsequenceKernel c) →
      K.Le T (RefinedEqRel q c) := by
  dsimp
  rw [canonical_refinement_eq_meet q c]
  exact minimal_justified_repair (relationMeetKernel X) (EqRel q) (ConsequenceKernel c)

/-- The representation naturally carried by a developmental stage: quotient a
    state by all currently accessible typed future consequences. -/
def stageRepresentation
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    (S : Stage C) (X : C.Obj) :
    A.State X → StageQuot C A Obs observe S X :=
  fun x => Quotient.mk (stageSetoid C A Obs observe S X) x

/-- The concrete consequence exposed by one newly licensed continuation. -/
def seedConsequence
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (seed : C.Hom X Y) :
    A.State X → Obs Y :=
  fun x => observe Y (A.map seed x)

/-- A stage-relative behavioural identification is exactly a collapse in its
    quotient representation. -/
theorem stage_equivalence_collapses_representation
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    (S : Stage C) {X : C.Obj} {x y : A.State X}
    (h : BehEqAt C A Obs observe S X x y) :
    stageRepresentation C A Obs observe S X x =
      stageRepresentation C A Obs observe S X y := by
  exact Quotient.sound h

/-- Unified developmental step.

The *same* newly licensed continuation supplies the consequence that:
1. separates a pair currently identified by the stage quotient;
2. therefore cannot factor through the current representation;
3. is restored by the canonical least consequential repair;
4. generates the least composition-closed stage extension containing it; and
5. forces a strict behavioural split in that minimally extended regime.

This packages the factorization, meet-refinement, and generated-category views
as one verifier-governed developmental mechanism. -/
theorem verified_separator_forces_least_developmental_step
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    (S : Stage C)
    {X Y : C.Obj} {x y : A.State X}
    (seed : C.Hom X Y)
    (hold : BehEqAt C A Obs observe S X x y)
    (hsep : observe Y (A.map seed x) ≠ observe Y (A.map seed y)) :
    let q := stageRepresentation C A Obs observe S X
    let c := seedConsequence C A Obs observe seed
    (¬ FactorsThrough q c) ∧
    FactorsThrough (RefineWith q c) c ∧
    (RefinedEqRel q c =
      (relationMeetKernel (A.State X)).meet (EqRel q) (ConsequenceKernel c)) ∧
    Extends C S (adjoinStage C S seed) ∧
    (∀ T : Stage C, Extends C S T → T.allow seed →
      Extends C (adjoinStage C S seed) T) ∧
    (BehEqAt C A Obs observe S X x y ∧
      ¬ BehEqAt C A Obs observe (adjoinStage C S seed) X x y) := by
  dsimp
  have hcollapse :
      stageRepresentation C A Obs observe S X x =
        stageRepresentation C A Obs observe S X y :=
    stage_equivalence_collapses_representation C A Obs observe S hold
  constructor
  · exact separator_implies_nonfactorization
      (stageRepresentation C A Obs observe S X)
      (seedConsequence C A Obs observe seed)
      hcollapse hsep
  constructor
  · exact consequence_factors_through_refinement
      (stageRepresentation C A Obs observe S X)
      (seedConsequence C A Obs observe seed)
  constructor
  · exact canonical_refinement_eq_meet
      (stageRepresentation C A Obs observe S X)
      (seedConsequence C A Obs observe seed)
  constructor
  · exact old_extends_adjoin C S seed
  constructor
  · intro T hST hseed
    exact adjoin_least C S T seed hST hseed
  · exact generated_separator_forces_minimal_split
      C A Obs observe S seed hold hsep

end UnifiedDevelopmentalLaw

#check UnifiedDevelopmentalLaw.canonical_refinement_eq_meet
#check UnifiedDevelopmentalLaw.canonical_factorization_repair_is_minimal_meet
#check UnifiedDevelopmentalLaw.stage_equivalence_collapses_representation
#check UnifiedDevelopmentalLaw.verified_separator_forces_least_developmental_step
