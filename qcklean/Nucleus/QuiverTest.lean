import Mathlib.Tactic.DeriveFintype
import Nucleus.Quiver

open CategoryTheory
open Nucleus

#check FiniteQuiver
#check Vertex
#check primitiveEdge

inductive V | a | b deriving DecidableEq, Fintype, Repr
inductive E | left | right deriving DecidableEq, Fintype, Repr

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
