import Std
import NucleusResidualExtension

universe u v w x

namespace NucleusDevelopmental

open NucleusFunctor
open NucleusQuiver
open NucleusFreeCategory
open NucleusPresentedCategory
open NucleusResidualExtension

/-- One developmental generation starts from an old category C, freely
    adjoins one residual-forced arrow X₀→Y₀, and then adds exactly the
    verifier-earned equations W between generated paths. -/
def generationEquations
    (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj)
    (W : Equations (adjoinQuiver C X₀ Y₀)) :
    Equations (adjoinQuiver C X₀ Y₀) :=
  fun p q =>
    AdjoinEquation C X₀ Y₀ p q ∨ W p q

/-- The next developmental category: free minimal extension followed by the
    warranted quotient. -/
def generationCategory
    (C : SmallCategory.{u, v}) (X₀ Y₀ : C.Obj)
    (W : Equations (adjoinQuiver C X₀ Y₀)) :
    SmallCategory :=
  NucleusPresentedCategory.category (generationEquations C X₀ Y₀ W)

/-- If F interprets the old category, a interprets the residual arrow, and
    all verifier-earned equations W hold, then the whole combined presentation
    is satisfied. -/
theorem interpretation_satisfies_generation
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (W : Equations (adjoinQuiver C X₀ Y₀))
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀))
    (hW : Satisfies (interpretation F a) W) :
    Satisfies (interpretation F a)
      (generationEquations C X₀ Y₀ W) := by
  intro A B p q h
  cases h with
  | inl hold =>
      exact interpretation_satisfies F a hold
  | inr hw =>
      exact hW hw

/-- Canonical interpretation of one warranted developmental generation. -/
def lift
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (W : Equations (adjoinQuiver C X₀ Y₀))
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀))
    (hW : Satisfies (interpretation F a) W) :
    Extension (interpretation F a)
      (generationEquations C X₀ Y₀ W) :=
  descend (interpretation F a)
    (generationEquations C X₀ Y₀ W)
    (interpretation_satisfies_generation W F a hW)

/-- The old morphisms still map exactly as F under the developmental lift. -/
theorem lift_old
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ A B : C.Obj}
    (W : Equations (adjoinQuiver C X₀ Y₀))
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀))
    (hW : Satisfies (interpretation F a) W)
    (f : C.Hom A B) :
    (lift W F a hW).mapQ
      (project (Ω := generationEquations C X₀ Y₀ W)
        (Path.gen (AdjoinEdge.old f))) =
      F.map f := by
  exact (lift W F a hW).map_gen (AdjoinEdge.old f)

/-- The residual-forced generator maps exactly to the supplied candidate a. -/
theorem lift_seed
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (W : Equations (adjoinQuiver C X₀ Y₀))
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀))
    (hW : Satisfies (interpretation F a) W) :
    (lift W F a hW).mapQ
      (project (Ω := generationEquations C X₀ Y₀ W)
        (Path.gen
          (AdjoinEdge.seed : AdjoinEdge C X₀ Y₀ X₀ Y₀))) =
      a := by
  exact (lift W F a hW).map_gen
    (AdjoinEdge.seed : AdjoinEdge C X₀ Y₀ X₀ Y₀)

/-- Universal property of one developmental generation.

    Given:
      * an interpretation F of all old structure,
      * exactly one residual-forced arrow a,
      * and a proof that the new warrant equations hold,

    there is one unique functorial interpretation of the entire generated and
    quotiented developmental category. This makes "add no more than the
    residual forces; identify exactly what warrant forces" literal. -/
theorem generation_universal
    {C : SmallCategory.{u, v}} {D : SmallCategory.{w, x}}
    {X₀ Y₀ : C.Obj}
    (W : Equations (adjoinQuiver C X₀ Y₀))
    (F : SmallFunctor C D)
    (a : D.Hom (F.obj X₀) (F.obj Y₀))
    (hW : Satisfies (interpretation F a) W) :
    ∃ E : Extension (interpretation F a)
        (generationEquations C X₀ Y₀ W),
      (∀ {A B : C.Obj} (f : C.Hom A B),
        E.mapQ
          (project (Ω := generationEquations C X₀ Y₀ W)
            (Path.gen (AdjoinEdge.old f))) =
          F.map f) ∧
      E.mapQ
        (project (Ω := generationEquations C X₀ Y₀ W)
          (Path.gen
            (AdjoinEdge.seed : AdjoinEdge C X₀ Y₀ X₀ Y₀))) =
        a ∧
      ∀ E' : Extension (interpretation F a)
          (generationEquations C X₀ Y₀ W),
        ∀ {A B : C.Obj}
          (q : (generationCategory C X₀ Y₀ W).Hom A B),
          E'.mapQ q = E.mapQ q := by
  refine ⟨lift W F a hW, ?_, lift_seed W F a hW, ?_⟩
  · intro A B f
    exact lift_old W F a hW f
  · intro E' A B q
    refine Quotient.inductionOn q ?_
    intro p
    calc
      E'.mapQ
          (project (Ω := generationEquations C X₀ Y₀ W) p) =
          eval (interpretation F a) p :=
        extension_on_path_unique E' p
      _ = (lift W F a hW).mapQ
          (project (Ω := generationEquations C X₀ Y₀ W) p) := rfl

end NucleusDevelopmental
