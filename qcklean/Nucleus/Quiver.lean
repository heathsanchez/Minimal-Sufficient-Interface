import Mathlib.CategoryTheory.PathCategory.Basic
import Mathlib.CategoryTheory.Category.Quiv

namespace Nucleus

universe u v

structure FiniteQuiver where
  V : Type u
  E : Type v
  vFinite : Fintype V
  eFinite : Fintype E
  vDecEq : DecidableEq V
  eDecEq : DecidableEq E
  src : E → V
  tgt : E → V

attribute [instance] FiniteQuiver.vFinite FiniteQuiver.eFinite
  FiniteQuiver.vDecEq FiniteQuiver.eDecEq

def Vertex (G : FiniteQuiver) := G.V

instance (G : FiniteQuiver) : Fintype (Vertex G) := G.vFinite
instance (G : FiniteQuiver) : DecidableEq (Vertex G) := G.vDecEq

instance (G : FiniteQuiver) : Quiver (Vertex G) where
  Hom X Y := {e : G.E // G.src e = X ∧ G.tgt e = Y}

def primitiveEdge (G : FiniteQuiver) (e : G.E) :
    (show Vertex G from G.src e) ⟶ (show Vertex G from G.tgt e) :=
  ⟨e, rfl, rfl⟩

end Nucleus
