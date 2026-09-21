import Nucleus.Free

open CategoryTheory
open Nucleus

#check FreeCategory
#check freeNucleus_lift
#check freeNucleus_lift_unique
#check freeNucleus_equiv
#check CategoryTheory.Paths.lift
#check CategoryTheory.Paths.lift_unique
#check CategoryTheory.Quiv.pathsEquiv

namespace FreeFixture

inductive V | a | b deriving DecidableEq, Repr
inductive E | left | right deriving DecidableEq, Repr

instance : Fintype V where
  elems := {.a, .b}
  complete := by intro x; cases x <;> simp

instance : Fintype E where
  elems := {.left, .right}
  complete := by intro x; cases x <;> simp

def G : FiniteQuiver where
  V := V
  E := E
  vFinite := inferInstance
  eFinite := inferInstance
  vDecEq := inferInstance
  eDecEq := inferInstance
  src := fun _ => V.a
  tgt := fun _ => V.b

example :
    (primitiveEdge G E.left).toPath ≠ (primitiveEdge G E.right).toPath := by
  intro h
  have he : primitiveEdge G E.left = primitiveEdge G E.right :=
    eq_of_heq (Quiver.Path.cons.inj h).2.2
  have hv : (primitiveEdge G E.left).val = (primitiveEdge G E.right).val :=
    congrArg Subtype.val he
  cases hv

end FreeFixture
