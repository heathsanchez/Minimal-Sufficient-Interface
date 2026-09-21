import Std
import TypedBehaviouralCongruence

universe u v w

/-- A directed multigraph with no composition, identities, or categorical laws. -/
structure NucleusQuiver where
  Obj : Type u
  Edge : Obj → Obj → Type v

namespace NucleusQuiver

/-- The underlying quiver of a small category. -/
def ofCategory (C : SmallCategory) : NucleusQuiver where
  Obj := C.Obj
  Edge := C.Hom

/-- A map of raw directed generators into the underlying quiver of a category. -/
structure Interpretation (G : NucleusQuiver) (C : SmallCategory) where
  obj : G.Obj → C.Obj
  edge : {X Y : G.Obj} → G.Edge X Y → C.Hom (obj X) (obj Y)

end NucleusQuiver
