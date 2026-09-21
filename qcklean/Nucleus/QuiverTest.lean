import Nucleus.Quiver

open CategoryTheory
open Nucleus

#check FiniteQuiver
#check Vertex
#check primitiveEdge

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

example : primitiveEdge G E.left ≠ primitiveEdge G E.right := by
  intro h
  have hv : (primitiveEdge G E.left).val = (primitiveEdge G E.right).val :=
    congrArg Subtype.val h
  cases hv
