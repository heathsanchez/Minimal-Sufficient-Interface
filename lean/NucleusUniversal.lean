import Std
import NucleusDevelopmental
import GeneratedStage

universe u v w x

namespace NucleusUniversal

open NucleusQuiver
open NucleusFreeCategory
open NucleusPresentedCategory
open NucleusResidualExtension
open NucleusDevelopmental
open NucleusFunctor
open DevelopmentalCategory
open GeneratedStage

/-- The Nucleus construction: freely generate all compositional paths from a
    quiver, then quotient by exactly the warranted path equations Ω. -/
def Nuc (G : NucleusQuiver.{u, v}) (Ω : Equations G) : SmallCategory :=
  NucleusPresentedCategory.category Ω

/-- A valid generator interpretation is one that satisfies all warranted
    equations. -/
def ValidGen
    (G : NucleusQuiver.{u, v})
    (Ω : Equations G)
    (C : SmallCategory.{w, x}) :=
  {I : Interpretation G C // Satisfies I Ω}

/-- Universal property of the Nucleus.

    Every valid interpretation of the primitive directed generators extends
    uniquely to the free warranted completion Nuc(G, Ω). -/
theorem nucleus_universal
    {G : NucleusQuiver.{u, v}}
    {C : SmallCategory.{w, x}}
    (Ω : Equations G)
    (I : Interpretation G C)
    (hΩ : Satisfies I Ω) :
    ∃ E : Extension I Ω,
      ∀ E' : Extension I Ω,
        ∀ {X Y : G.Obj} (q : (Nuc G Ω).Hom X Y),
          E'.mapQ q = E.mapQ q := by
  exact presented_universal I Ω hΩ

/-- The old generated-stage theorem is recovered as the ambient special case:
    when the residual arrow already exists in a fixed ambient category, closing
    the allowed stage under identities and composition is the least stage
    containing it. -/
theorem ambient_existing_arrow_least
    (C : SmallCategory)
    (S T : Stage C)
    {X Y : C.Obj}
    (seed : C.Hom X Y)
    (hST : Extends C S T)
    (hseed : T.allow seed) :
    Extends C (adjoinStage C S seed) T := by
  exact adjoin_least C S T seed hST hseed

/-- One verified developmental generation is the free extension by the
    residual-forced arrow followed by the warranted quotient. -/
theorem developmental_universal
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
  exact generation_universal W F a hW

end NucleusUniversal
