import Nucleus.Quiver

namespace Nucleus

open CategoryTheory

universe u v u' v'

abbrev FreeCategory (G : FiniteQuiver.{u, v}) :=
  CategoryTheory.Paths (Vertex G)

def freeNucleus_lift
    (G : FiniteQuiver.{u, v})
    {D : Type u'} [Category.{v'} D]
    (φ : Vertex G ⥤q D) :
    FreeCategory G ⥤ D :=
  CategoryTheory.Paths.lift φ

theorem freeNucleus_lift_unique
    (G : FiniteQuiver.{u, v})
    {D : Type u'} [Category.{v'} D]
    (φ : Vertex G ⥤q D)
    (F : FreeCategory G ⥤ D)
    (hF : CategoryTheory.Paths.of (Vertex G) ⋙q F.toPrefunctor = φ) :
    F = freeNucleus_lift G φ :=
  CategoryTheory.Paths.lift_unique φ F hF

def freeNucleus_equiv
    (G : FiniteQuiver.{u, v})
    {D : Type u'} [Category.{v'} D] :
    (FreeCategory G ⥤ D) ≃ (Vertex G ⥤q D) :=
  CategoryTheory.Quiv.pathsEquiv

end Nucleus
