import Std

universe u v w z

/-- A small category, kept explicit so the theorem depends only on Lean/Std. -/
structure SmallCategory where
  Obj : Type u
  Hom : Obj → Obj → Type v
  id : (X : Obj) → Hom X X
  comp : {X Y Z : Obj} → Hom Y Z → Hom X Y → Hom X Z
  id_comp : ∀ {X Y} (f : Hom X Y), comp (id Y) f = f
  comp_id : ∀ {X Y} (f : Hom X Y), comp f (id X) = f
  assoc : ∀ {W X Y Z} (h : Hom Y Z) (g : Hom X Y) (f : Hom W X),
    comp (comp h g) f = comp h (comp g f)

namespace TypedBehaviouralCongruence

variable (C : SmallCategory)

/-- A concrete action of the category on typed state spaces.  This is the
    lightweight functor-to-Type structure needed for MSI's typed continuation
    semantics. -/
structure Action where
  State : C.Obj → Type w
  map : {X Y : C.Obj} → C.Hom X Y → State X → State Y
  map_id : ∀ {X} (x : State X), map (C.id X) x = x
  map_comp : ∀ {X Y Z} (g : C.Hom Y Z) (f : C.Hom X Y) (x : State X),
    map (C.comp g f) x = map g (map f x)

variable (A : Action C)

/-- Each object has its own verifier-visible observation type. -/
variable (Obs : C.Obj → Type z)
variable (observe : ∀ X, A.State X → Obs X)

/-- Contextual behavioural equivalence at object X: two states are identical
    exactly when every typed continuation out of X yields the same protected
    observation at its destination. -/
def BehEq (X : C.Obj) (x y : A.State X) : Prop :=
  ∀ (Y : C.Obj) (f : C.Hom X Y),
    observe Y (A.map f x) = observe Y (A.map f y)

/-- A typed relation family is observation-compatible when it never merges a
    pair already separated by the local observation. -/
def ObsCompatible
    (R : ∀ X, A.State X → A.State X → Prop) : Prop :=
  ∀ X x y, R X x y → observe X x = observe X y

/-- A typed relation family is a categorical congruence when every morphism
    preserves it across source and target objects. -/
def Congruent
    (R : ∀ X, A.State X → A.State X → Prop) : Prop :=
  ∀ {X Y} (f : C.Hom X Y) x y,
    R X x y → R Y (A.map f x) (A.map f y)

/-- Contextual behavioural equivalence is reflexive. -/
theorem behEq_refl {X : C.Obj} (x : A.State X) :
    BehEq C A Obs observe X x x := by
  intro Y f
  rfl

/-- Contextual behavioural equivalence is symmetric. -/
theorem behEq_symm {X : C.Obj} {x y : A.State X}
    (h : BehEq C A Obs observe X x y) :
    BehEq C A Obs observe X y x := by
  intro Y f
  exact (h Y f).symm

/-- Contextual behavioural equivalence is transitive. -/
theorem behEq_trans {X : C.Obj} {x y z : A.State X}
    (hxy : BehEq C A Obs observe X x y)
    (hyz : BehEq C A Obs observe X y z) :
    BehEq C A Obs observe X x z := by
  intro Y f
  exact (hxy Y f).trans (hyz Y f)

/-- Behavioural equivalence is contained in the local observation kernel. -/
theorem behEq_obsCompatible :
    ObsCompatible C A Obs observe (BehEq C A Obs observe) := by
  intro X x y h
  simpa [A.map_id] using h X (C.id X)

/-- Behavioural equivalence is preserved by every typed morphism. -/
theorem behEq_congruent :
    Congruent C A (BehEq C A Obs observe) := by
  intro X Y f x y h Z g
  simpa [A.map_comp] using h Z (C.comp g f)

/-- Universal characterization: contextual behavioural equivalence is the
    greatest observation-compatible categorical congruence family.

    As in the monoid theorem, maximality is stronger than the equivalence-family
    formulation: R itself need not be assumed reflexive, symmetric, or transitive. -/
theorem greatest_congruence
    (R : ∀ X, A.State X → A.State X → Prop)
    (hCong : Congruent C A R)
    (hObs : ObsCompatible C A Obs observe R) :
    ∀ X x y, R X x y → BehEq C A Obs observe X x y := by
  intro X x y hxy Y f
  exact hObs Y (A.map f x) (A.map f y) (hCong f x y hxy)

/-- Setoid induced at each object by all typed future observations. -/
def behSetoid (X : C.Obj) : Setoid (A.State X) where
  r := BehEq C A Obs observe X
  iseqv := {
    refl := behEq_refl C A Obs observe
    symm := by intro x y; exact behEq_symm C A Obs observe
    trans := by intro x y z; exact behEq_trans C A Obs observe
  }

/-- The minimal sufficient interface carried by object X. -/
abbrev QuotState (X : C.Obj) := Quotient (behSetoid C A Obs observe X)

/-- Every typed morphism descends to the behavioural quotient. -/
def qmap {X Y : C.Obj} (f : C.Hom X Y) :
    QuotState C A Obs observe X → QuotState C A Obs observe Y :=
  Quotient.lift
    (fun x => Quotient.mk (behSetoid C A Obs observe Y) (A.map f x))
    (by
      intro x y hxy
      exact Quotient.sound (behEq_congruent C A Obs observe f x y hxy))

/-- The quotient map has the expected value on representatives. -/
theorem qmap_mk {X Y : C.Obj} (f : C.Hom X Y) (x : A.State X) :
    qmap C A Obs observe f (Quotient.mk (behSetoid C A Obs observe X) x) =
      Quotient.mk (behSetoid C A Obs observe Y) (A.map f x) := rfl

/-- Identity morphisms descend to identity maps. -/
theorem qmap_id {X : C.Obj} :
    ∀ q : QuotState C A Obs observe X,
      qmap C A Obs observe (C.id X) q = q := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [qmap_mk, A.map_id]

/-- Composition of typed morphisms survives quotienting exactly. -/
theorem qmap_comp {X Y Z : C.Obj}
    (g : C.Hom Y Z) (f : C.Hom X Y) :
    ∀ q : QuotState C A Obs observe X,
      qmap C A Obs observe (C.comp g f) q =
        qmap C A Obs observe g (qmap C A Obs observe f q) := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [qmap_mk, qmap_mk, qmap_mk, A.map_comp]

/-- Uniqueness of the descended typed map on quotient representatives. -/
theorem qmap_unique {X Y : C.Obj} (f : C.Hom X Y)
    (F : QuotState C A Obs observe X → QuotState C A Obs observe Y)
    (hF : ∀ x : A.State X,
      F (Quotient.mk (behSetoid C A Obs observe X) x) =
        Quotient.mk (behSetoid C A Obs observe Y) (A.map f x)) :
    ∀ q, F q = qmap C A Obs observe f q := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [qmap_mk]
  exact hF x

/-- The quotient construction therefore defines a functorial typed action:
    object X is sent to its behavioural quotient, and morphism f to qmap f. -/
structure QuotientAction where
  State : C.Obj → Type (max w z)
  map : {X Y : C.Obj} → C.Hom X Y → State X → State Y
  map_id : ∀ {X} (q : State X), map (C.id X) q = q
  map_comp : ∀ {X Y Z} (g : C.Hom Y Z) (f : C.Hom X Y) (q : State X),
    map (C.comp g f) q = map g (map f q)

/-- The behavioural quotient is itself a functorial action of C. -/
def quotientAction : QuotientAction C where
  State := QuotState C A Obs observe
  map := qmap C A Obs observe
  map_id := qmap_id C A Obs observe
  map_comp := qmap_comp C A Obs observe

end TypedBehaviouralCongruence
