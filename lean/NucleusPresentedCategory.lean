import Std
import NucleusFreeCategory

universe u v w x

namespace NucleusPresentedCategory

open NucleusQuiver
open NucleusFreeCategory

/-- A family of warranted equations between parallel generated paths. -/
abbrev Equations (G : NucleusQuiver.{u, v}) :=
  {X Y : G.Obj} → Path G X Y → Path G X Y → Prop

/-- The least categorical congruence containing the warranted equations. -/
inductive GeneratedCongruence {G : NucleusQuiver.{u, v}}
    (Ω : Equations G) :
    {X Y : G.Obj} → Path G X Y → Path G X Y → Prop
  | equation {X Y} {p q : Path G X Y} :
      Ω p q → GeneratedCongruence Ω p q
  | refl {X Y} (p : Path G X Y) :
      GeneratedCongruence Ω p p
  | symm {X Y} {p q : Path G X Y} :
      GeneratedCongruence Ω p q → GeneratedCongruence Ω q p
  | trans {X Y} {p q r : Path G X Y} :
      GeneratedCongruence Ω p q →
      GeneratedCongruence Ω q r →
      GeneratedCongruence Ω p r
  | comp {X Y Z}
      {q q' : Path G Y Z} {p p' : Path G X Y} :
      GeneratedCongruence Ω q q' →
      GeneratedCongruence Ω p p' →
      GeneratedCongruence Ω (Path.append q p) (Path.append q' p')

def pathSetoid {G : NucleusQuiver.{u, v}} (Ω : Equations G)
    (X Y : G.Obj) : Setoid (Path G X Y) where
  r := GeneratedCongruence Ω
  iseqv := {
    refl := GeneratedCongruence.refl
    symm := GeneratedCongruence.symm
    trans := GeneratedCongruence.trans
  }

/-- The category presented by generators G and warranted equations Ω. -/
def category {G : NucleusQuiver.{u, v}} (Ω : Equations G) : SmallCategory where
  Obj := G.Obj
  Hom := fun X Y => Quotient (pathSetoid Ω X Y)
  id := fun X => Quotient.mk (pathSetoid Ω X X) (.nil X)
  comp := fun {X Y Z} q p =>
    Quotient.liftOn₂ q p
      (fun q' p' =>
        Quotient.mk (pathSetoid Ω X Z) (Path.append q' p'))
      (by
        intro q₁ p₁ q₂ p₂ hq hp
        exact Quotient.sound (GeneratedCongruence.comp hq hp))
  id_comp := by
    intro X Y f
    refine Quotient.inductionOn f ?_
    intro p
    rfl
  comp_id := by
    intro X Y f
    refine Quotient.inductionOn f ?_
    intro p
    change
      Quotient.mk (pathSetoid Ω X Y) (Path.append p (.nil X)) =
      Quotient.mk (pathSetoid Ω X Y) p
    rw [Path.append_nil_right]
  assoc := by
    intro W X Y Z h g f
    refine Quotient.inductionOn h ?_
    intro hp
    refine Quotient.inductionOn g ?_
    intro gp
    refine Quotient.inductionOn f ?_
    intro fp
    change
      Quotient.mk (pathSetoid Ω W Z)
          (Path.append (Path.append hp gp) fp) =
      Quotient.mk (pathSetoid Ω W Z)
          (Path.append hp (Path.append gp fp))
    rw [Path.append_assoc]

/-- Canonical projection from a free path to its warranted quotient class. -/
def project {G : NucleusQuiver.{u, v}} {Ω : Equations G}
    {X Y : G.Obj} (p : Path G X Y) :
    (category Ω).Hom X Y :=
  Quotient.mk (pathSetoid Ω X Y) p

/-- An interpretation satisfies Ω when every warranted equation is true
    after compositional evaluation in the target category. -/
def Satisfies {G : NucleusQuiver.{u, v}} {C : SmallCategory.{w, x}}
    (I : Interpretation G C) (Ω : Equations G) : Prop :=
  ∀ {X Y : G.Obj} {p q : Path G X Y},
    Ω p q → eval I p = eval I q

/-- Warranted equations generate no extra target equalities beyond closure
    under equality and categorical composition. -/
theorem congruence_sound
    {G : NucleusQuiver.{u, v}} {C : SmallCategory.{w, x}}
    {I : Interpretation G C} {Ω : Equations G}
    (hSat : Satisfies I Ω)
    {X Y : G.Obj} {p q : Path G X Y}
    (h : GeneratedCongruence Ω p q) :
    eval I p = eval I q := by
  induction h with
  | equation hΩ =>
      exact hSat hΩ
  | refl p =>
      rfl
  | symm h ih =>
      exact ih.symm
  | trans h₁ h₂ ih₁ ih₂ =>
      exact ih₁.trans ih₂
  | @comp X Y Z q q' p p' hq hp ihq ihp =>
      rw [eval_append, eval_append, ihq, ihp]

/-- A functorial interpretation of the presented category, with object map
    fixed by the original generator interpretation. -/
structure Extension
    {G : NucleusQuiver.{u, v}} {C : SmallCategory.{w, x}}
    (I : Interpretation G C) (Ω : Equations G) where
  mapQ : {X Y : G.Obj} → (category Ω).Hom X Y →
    C.Hom (I.obj X) (I.obj Y)
  map_id : ∀ X, mapQ ((category Ω).id X) = C.id (I.obj X)
  map_comp : ∀ {X Y Z} (q : (category Ω).Hom Y Z)
      (p : (category Ω).Hom X Y),
    mapQ ((category Ω).comp q p) = C.comp (mapQ q) (mapQ p)
  map_gen : ∀ {X Y} (e : G.Edge X Y),
    mapQ (project (Ω := Ω) (Path.gen e)) = I.edge e

/-- Quotient evaluation induced by a warranted interpretation. -/
def descend
    {G : NucleusQuiver.{u, v}} {C : SmallCategory.{w, x}}
    (I : Interpretation G C) (Ω : Equations G)
    (hSat : Satisfies I Ω) : Extension I Ω where
  mapQ := fun {X Y} q =>
    Quotient.liftOn q (eval I)
      (by
        intro p r hpr
        exact congruence_sound hSat hpr)
  map_id := by
    intro X
    rfl
  map_comp := by
    intro X Y Z q p
    refine Quotient.inductionOn q ?_
    intro qp
    refine Quotient.inductionOn p ?_
    intro pp
    exact eval_append I qp pp
  map_gen := by
    intro X Y e
    exact eval_gen I e

/-- Every extension agrees with free compositional evaluation on every
    projected path. -/
theorem extension_on_path_unique
    {G : NucleusQuiver.{u, v}} {C : SmallCategory.{w, x}}
    {I : Interpretation G C} {Ω : Equations G}
    (E : Extension I Ω) :
    ∀ {X Y : G.Obj} (p : Path G X Y),
      E.mapQ (project (Ω := Ω) p) = eval I p := by
  intro X Y p
  induction p with
  | nil X =>
      exact E.map_id X
  | @snoc X Y Z p e ih =>
      calc
        E.mapQ (project (Ω := Ω) (.snoc p e)) =
            E.mapQ ((category Ω).comp
              (project (Ω := Ω) (Path.gen e))
              (project (Ω := Ω) p)) := rfl
        _ = C.comp
              (E.mapQ (project (Ω := Ω) (Path.gen e)))
              (E.mapQ (project (Ω := Ω) p)) :=
            E.map_comp
              (project (Ω := Ω) (Path.gen e))
              (project (Ω := Ω) p)
        _ = C.comp (I.edge e) (eval I p) := by
            rw [E.map_gen e, ih]
        _ = eval I (.snoc p e) := rfl

/-- Presented-category universal property: an interpretation satisfying the
    warranted equations descends uniquely to the quotient category. -/
theorem presented_universal
    {G : NucleusQuiver.{u, v}} {C : SmallCategory.{w, x}}
    (I : Interpretation G C) (Ω : Equations G)
    (hSat : Satisfies I Ω) :
    ∃ E : Extension I Ω,
      ∀ E' : Extension I Ω,
        ∀ {X Y : G.Obj} (q : (category Ω).Hom X Y),
          E'.mapQ q = E.mapQ q := by
  refine ⟨descend I Ω hSat, ?_⟩
  intro E' X Y q
  refine Quotient.inductionOn q ?_
  intro p
  rw [extension_on_path_unique E']
  rfl

end NucleusPresentedCategory
