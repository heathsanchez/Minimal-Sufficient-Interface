import Std
import TypedBehaviouralCongruence

universe u v w x

namespace NucleusFunctor

/-- A lightweight functor between the repo's explicit small categories. -/
structure SmallFunctor (C : SmallCategory.{u, v}) (D : SmallCategory.{w, x}) where
  obj : C.Obj → D.Obj
  map : {X Y : C.Obj} → C.Hom X Y → D.Hom (obj X) (obj Y)
  map_id : ∀ X, map (C.id X) = D.id (obj X)
  map_comp : ∀ {X Y Z} (g : C.Hom Y Z) (f : C.Hom X Y),
    map (C.comp g f) = D.comp (map g) (map f)

end NucleusFunctor
