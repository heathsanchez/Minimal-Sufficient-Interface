import Std
import TypedBehaviouralCongruence

universe u v w z

namespace DevelopmentalCategory

open TypedBehaviouralCongruence

variable (C : SmallCategory)
variable (A : Action C)
variable (Obs : C.Obj → Type z)
variable (observe : ∀ X, A.State X → Obs X)

/-- A developmental stage is a composition-closed family of currently
    accessible typed continuations inside a fixed ambient category. -/
structure Stage where
  allow : {X Y : C.Obj} → C.Hom X Y → Prop
  id_allow : ∀ X, allow (C.id X)
  comp_allow : ∀ {X Y Z} (g : C.Hom Y Z) (f : C.Hom X Y),
    allow g → allow f → allow (C.comp g f)

/-- Stage inclusion: every continuation accessible before remains accessible
    after development. -/
def Extends (S T : Stage C) : Prop :=
  ∀ {X Y} (f : C.Hom X Y), S.allow f → T.allow f

/-- Behavioural equivalence relative to the continuations accessible at one
    developmental stage. -/
def BehEqAt (S : Stage C) (X : C.Obj) (x y : A.State X) : Prop :=
  ∀ (Y : C.Obj) (f : C.Hom X Y), S.allow f →
    observe Y (A.map f x) = observe Y (A.map f y)

/-- Stage-relative behavioural equivalence is reflexive. -/
theorem behEqAt_refl (S : Stage C) {X : C.Obj} (x : A.State X) :
    BehEqAt C A Obs observe S X x x := by
  intro Y f hf
  rfl

/-- Stage-relative behavioural equivalence is symmetric. -/
theorem behEqAt_symm (S : Stage C) {X : C.Obj} {x y : A.State X}
    (h : BehEqAt C A Obs observe S X x y) :
    BehEqAt C A Obs observe S X y x := by
  intro Y f hf
  exact (h Y f hf).symm

/-- Stage-relative behavioural equivalence is transitive. -/
theorem behEqAt_trans (S : Stage C) {X : C.Obj} {x y z : A.State X}
    (hxy : BehEqAt C A Obs observe S X x y)
    (hyz : BehEqAt C A Obs observe S X y z) :
    BehEqAt C A Obs observe S X x z := by
  intro Y f hf
  exact (hxy Y f hf).trans (hyz Y f hf)

/-- Every currently accessible morphism preserves the current behavioural
    equivalence, because the stage is closed under post-composition. -/
theorem behEqAt_congruent (S : Stage C) {X Y : C.Obj}
    (f : C.Hom X Y) (hf : S.allow f) {x y : A.State X}
    (hxy : BehEqAt C A Obs observe S X x y) :
    BehEqAt C A Obs observe S Y (A.map f x) (A.map f y) := by
  intro Z g hg
  have h := hxy Z (C.comp g f) (S.comp_allow g f hg hf)
  rw [A.map_comp g f x, A.map_comp g f y] at h
  exact h

/-- Growing the continuation category can only refine behavioural identity. -/
theorem extension_refines {S T : Stage C}
    (hST : Extends C S T) :
    ∀ X x y,
      BehEqAt C A Obs observe T X x y →
      BehEqAt C A Obs observe S X x y := by
  intro X x y hT Y f hf
  exact hT Y f (hST f hf)

/-- A newly accessible continuation that separates an old equivalence class
    forces a strict developmental split. -/
theorem new_separator_forces_split {S T : Stage C}
    (_hST : Extends C S T)
    {X Y : C.Obj} {x y : A.State X} (f : C.Hom X Y)
    (hold : BehEqAt C A Obs observe S X x y)
    (hnew : T.allow f)
    (hsep : observe Y (A.map f x) ≠ observe Y (A.map f y)) :
    BehEqAt C A Obs observe S X x y ∧
      ¬ BehEqAt C A Obs observe T X x y := by
  constructor
  · exact hold
  · intro hT
    exact hsep (hT Y f hnew)

/-- Setoid carried by object X at stage S. -/
def stageSetoid (S : Stage C) (X : C.Obj) : Setoid (A.State X) where
  r := BehEqAt C A Obs observe S X
  iseqv := {
    refl := behEqAt_refl C A Obs observe S
    symm := by intro x y; exact behEqAt_symm C A Obs observe S
    trans := by intro x y z; exact behEqAt_trans C A Obs observe S
  }

abbrev StageQuot (S : Stage C) (X : C.Obj) :=
  Quotient (stageSetoid C A Obs observe S X)

/-- Every currently accessible morphism descends to the current MSI quotient. -/
def stageMap (S : Stage C) {X Y : C.Obj}
    (f : C.Hom X Y) (hf : S.allow f) :
    StageQuot C A Obs observe S X → StageQuot C A Obs observe S Y :=
  Quotient.lift
    (fun x => Quotient.mk (stageSetoid C A Obs observe S Y) (A.map f x))
    (by
      intro x y hxy
      exact Quotient.sound (behEqAt_congruent C A Obs observe S f hf hxy))

/-- The stage quotient map has the expected value on representatives. -/
theorem stageMap_mk (S : Stage C) {X Y : C.Obj}
    (f : C.Hom X Y) (hf : S.allow f) (x : A.State X) :
    stageMap C A Obs observe S f hf
      (Quotient.mk (stageSetoid C A Obs observe S X) x) =
      Quotient.mk (stageSetoid C A Obs observe S Y) (A.map f x) := rfl

/-- Accessible identities act identically after quotienting. -/
theorem stageMap_id (S : Stage C) {X : C.Obj} :
    ∀ q : StageQuot C A Obs observe S X,
      stageMap C A Obs observe S (C.id X) (S.id_allow X) q = q := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [stageMap_mk, A.map_id]

/-- Accessible composition is preserved by the current quotient. -/
theorem stageMap_comp (S : Stage C) {X Y Z : C.Obj}
    (g : C.Hom Y Z) (f : C.Hom X Y)
    (hg : S.allow g) (hf : S.allow f) :
    ∀ q : StageQuot C A Obs observe S X,
      stageMap C A Obs observe S (C.comp g f) (S.comp_allow g f hg hf) q =
        stageMap C A Obs observe S g hg
          (stageMap C A Obs observe S f hf q) := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [stageMap_mk, stageMap_mk, stageMap_mk, A.map_comp]

/-- Development induces a canonical map from the finer new interface back to
    the coarser old interface.  It simply forgets distinctions introduced by
    newly accessible continuations. -/
def forgetGrowth {S T : Stage C} (hST : Extends C S T) (X : C.Obj) :
    StageQuot C A Obs observe T X → StageQuot C A Obs observe S X :=
  Quotient.lift
    (fun x => Quotient.mk (stageSetoid C A Obs observe S X) x)
    (by
      intro x y hxy
      exact Quotient.sound (extension_refines C A Obs observe hST X x y hxy))

/-- The ambient stage contains every morphism. -/
def ambientStage : Stage C where
  allow := fun _ => True
  id_allow := by intro X; trivial
  comp_allow := by intro X Y Z g f hg hf; trivial

/-- At the ambient stage, stage-relative equivalence is exactly the full typed
    behavioural congruence from `TypedBehaviouralCongruence`. -/
theorem ambient_eq_full (X : C.Obj) (x y : A.State X) :
    BehEqAt C A Obs observe (ambientStage C) X x y ↔
      BehEq C A Obs observe X x y := by
  constructor
  · intro h Y f
    exact h Y f trivial
  · intro h Y f hf
    exact h Y f

end DevelopmentalCategory
