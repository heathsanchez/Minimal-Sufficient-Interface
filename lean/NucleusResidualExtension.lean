import Std
import NucleusFunctor
import NucleusPresentedCategory

universe u v w x

namespace NucleusResidualExtension

open NucleusFunctor
open NucleusQuiver
open NucleusFreeCategory
open NucleusPresentedCategory

/-- Generators for adjoining one genuinely new arrow to an existing category:
    every old morphism is retained as a generator, plus one new seed. -/
inductive AdjoinEdge (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj) :
    C.Obj → C.Obj → Type (max u v)
  | old {X Y : C.Obj} : C.Hom X Y → AdjoinEdge C X₀ Y₀ X Y
  | seed : AdjoinEdge C X₀ Y₀ X₀ Y₀

def adjoinQuiver (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj) :
    NucleusQuiver.{u, max u v} where
  Obj := C.Obj
  Edge := AdjoinEdge C X₀ Y₀

/-- Equations saying that the old generators still obey exactly the old
    category's identity and composition laws. No equation constrains the seed. -/
inductive AdjoinEquation
    (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj) :
    {X Y : C.Obj} →
      Path (adjoinQuiver C X₀ Y₀) X Y →
      Path (adjoinQuiver C X₀ Y₀) X Y → Prop
  | id (Z : C.Obj) :
      AdjoinEquation C X₀ Y₀
        (Path.gen (AdjoinEdge.old (C.id Z)))
        (.nil Z)
  | comp {A B D : C.Obj} (g : C.Hom B D) (f : C.Hom A B) :
      AdjoinEquation C X₀ Y₀
        (Path.append
          (Path.gen (AdjoinEdge.old g))
          (Path.gen (AdjoinEdge.old f)))
        (Path.gen (AdjoinEdge.old (C.comp g f)))

def equations (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj) :
    Equations (adjoinQuiver C X₀ Y₀) :=
  fun p q => AdjoinEquation C X₀ Y₀ p q

/-- The free category obtained by adjoining exactly one new arrow X₀→Y₀
    to C, while quotienting by the old category laws. -/
def category (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj) :
    SmallCategory.{u, max u v} :=
  NucleusPresentedCategory.category (equations C X₀ Y₀)

/-- Canonical image of an old morphism in the free adjunction. -/
def oldMap (C : SmallCategory.{u, v}) {X₀ Y₀ : C.Obj}
    {A B : C.Obj} (f : C.Hom A B) :
    (category C X₀ Y₀).Hom A B :=
  project (Ω := equations C X₀ Y₀)
    (Path.gen (AdjoinEdge.old f))

/-- The newly adjoined residual arrow. -/
def seedMap (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj) :
    (category C X₀ Y₀).Hom X₀ Y₀ :=
  project (Ω := equations C X₀ Y₀)
    (Path.gen (AdjoinEdge.seed : AdjoinEdge C X₀ Y₀ X₀ Y₀))

theorem oldMap_id (C : SmallCategory.{u, v}) {X₀ Y₀ : C.Obj}
    (Z : C.Obj) :
    oldMap C (X₀ := X₀) (Y₀ := Y₀) (C.id Z) =
      (category C X₀ Y₀).id Z := by
  exact Quotient.sound
    (GeneratedCongruence.equation (AdjoinEquation.id C X₀ Y₀ Z))

theorem oldMap_comp (C : SmallCategory.{u, v}) {X₀ Y₀ : C.Obj}
    {A B D : C.Obj} (g : C.Hom B D) (f : C.Hom A B) :
    oldMap C (X₀ := X₀) (Y₀ := Y₀) (C.comp g f) =
      (category C X₀ Y₀).comp
        (oldMap C (X₀ := X₀) (Y₀ := Y₀) g)
        (oldMap C (X₀ := X₀) (Y₀ := Y₀) f) := by
  exact (Quotient.sound
    (GeneratedCongruence.equation
      (AdjoinEquation.comp C X₀ Y₀ g f))).symm

/-- Given an interpretation F of the old category and one candidate arrow
    a : F(X₀)→F(Y₀), interpret the generators of the free adjunction. -/
def interpretation
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀)) :
    Interpretation (adjoinQuiver C X₀ Y₀) D where
  obj := F.obj
  edge := by
    intro X Y e
    cases e with
    | old f => exact F.map f
    | seed => exact a

theorem interpretation_satisfies
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀)) :
    Satisfies (interpretation F a) (equations C X₀ Y₀) := by
  intro X Y p q h
  cases h with
  | id =>
      simpa [interpretation] using F.map_id _
  | comp g f =>
      rw [eval_append, eval_gen, eval_gen, eval_gen]
      exact (F.map_comp g f).symm

/-- The universal extension into D. -/
def lift
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀)) :
    Extension (interpretation F a) (equations C X₀ Y₀) :=
  descend (interpretation F a) (equations C X₀ Y₀)
    (interpretation_satisfies F a)

theorem lift_old
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ A B : C.Obj}
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀))
    (f : C.Hom A B) :
    (lift F a).mapQ (oldMap C (X₀ := X₀) (Y₀ := Y₀) f) =
      F.map f := by
  exact (lift F a).map_gen (AdjoinEdge.old f)

theorem lift_seed
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀)) :
    (lift F a).mapQ (seedMap C X₀ Y₀) = a := by
  exact (lift F a).map_gen
    (AdjoinEdge.seed : AdjoinEdge C X₀ Y₀ X₀ Y₀)

/-- Walking-arrow / pushout universal property in concrete form:
    every old functor F plus one arrow a : F(X₀)→F(Y₀) extends uniquely
    through the category freely adjoining that arrow. -/
theorem free_adjoin_universal
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀)) :
    ∃ E : Extension (interpretation F a) (equations C X₀ Y₀),
      (∀ {A B : C.Obj} (f : C.Hom A B),
        E.mapQ (oldMap C (X₀ := X₀) (Y₀ := Y₀) f) = F.map f) ∧
      E.mapQ (seedMap C X₀ Y₀) = a ∧
      ∀ E' : Extension (interpretation F a) (equations C X₀ Y₀),
        ∀ {A B : C.Obj} (q : (category C X₀ Y₀).Hom A B),
          E'.mapQ q = E.mapQ q := by
  refine ⟨lift F a, ?_, lift_seed F a, ?_⟩
  · intro A B f
    exact lift_old F a f
  · intro E' A B q
    refine Quotient.inductionOn q ?_
    intro p
    calc
      E'.mapQ (project (Ω := equations C X₀ Y₀) p) =
          eval (interpretation F a) p :=
        extension_on_path_unique E' p
      _ = (lift F a).mapQ
          (project (Ω := equations C X₀ Y₀) p) := rfl

end NucleusResidualExtension
