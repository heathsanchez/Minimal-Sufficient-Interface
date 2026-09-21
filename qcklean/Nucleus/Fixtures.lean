import Nucleus.PathBehavior
import Mathlib.CategoryTheory.Types.Basic

namespace Nucleus.Fixtures

open CategoryTheory
open Nucleus

universe u v w z

def actionOfPrefunctor
    {G : FiniteQuiver.{u, v}}
    (φ : Vertex G ⥤q Type w) : PathAction G where
  State := fun X => φ.obj X
  map := fun p x => (CategoryTheory.Paths.lift φ).map p x
  map_id := by
    intro X x
    exact (CategoryTheory.Paths.lift φ).map_id_apply X x
  map_comp := by
    intro X Y Z p q x
    exact (CategoryTheory.Paths.lift φ).map_comp_apply p q x

def ImmediateObsEq
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : FreeCategory G → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : FreeCategory G} (p q : X ⟶ Y) : Prop :=
  ∀ x, observe Y (A.map p x) = observe Y (A.map q x)

def OneStateEq
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : FreeCategory G → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : FreeCategory G} (chosen : A.State X)
    (p q : X ⟶ Y) : Prop :=
  observe Y (A.map p chosen) = observe Y (A.map q chosen)

namespace FutureFixture

inductive V | x | y | z deriving DecidableEq, Repr
inductive E | p | q | r deriving DecidableEq, Repr

instance : Fintype V where
  elems := {.x, .y, .z}
  complete := by intro a; cases a <;> simp

instance : Fintype E where
  elems := {.p, .q, .r}
  complete := by intro a; cases a <;> simp

def G : FiniteQuiver where
  V := V
  E := E
  vFinite := inferInstance
  eFinite := inferInstance
  vDecEq := inferInstance
  eDecEq := inferInstance
  src := fun
    | .p | .q => .x
    | .r => .y
  tgt := fun
    | .p | .q => .y
    | .r => .z

def edgeFn : E → Bool → Bool
  | .p => fun _ => false
  | .q => fun _ => true
  | .r => fun b => b

def prefunctor : Vertex G ⥤q Type where
  obj := fun _ => Bool
  map := fun e => TypeCat.ofHom (edgeFn e.1)

def action : PathAction G := actionOfPrefunctor prefunctor

def Obs : FreeCategory G → Type := fun _ => Bool

def observe (X : FreeCategory G) (b : action.State X) : Obs X :=
  match (show V from X) with
  | .y => false
  | .x | .z => b

def p : (show FreeCategory G from V.x) ⟶ (show FreeCategory G from V.y) :=
  (primitiveEdge G E.p).toPath

def q : (show FreeCategory G from V.x) ⟶ (show FreeCategory G from V.y) :=
  (primitiveEdge G E.q).toPath

def r : (show FreeCategory G from V.y) ⟶ (show FreeCategory G from V.z) :=
  (primitiveEdge G E.r).toPath

@[simp] theorem map_p (b : Bool) : action.map p b = false := by
  have h := CategoryTheory.Paths.lift_toPath prefunctor
    (primitiveEdge G E.p)
  have h' := congrArg (fun f : Bool ⟶ Bool => f b) h
  simpa [prefunctor, edgeFn] using h'

@[simp] theorem map_q (b : Bool) : action.map q b = true := by
  have h := CategoryTheory.Paths.lift_toPath prefunctor
    (primitiveEdge G E.q)
  have h' := congrArg (fun f : Bool ⟶ Bool => f b) h
  simpa [prefunctor, edgeFn] using h'

@[simp] theorem map_r (b : Bool) : action.map r b = b := by
  have h := CategoryTheory.Paths.lift_toPath prefunctor
    (primitiveEdge G E.r)
  have h' := congrArg (fun f : Bool ⟶ Bool => f b) h
  simpa [prefunctor, edgeFn] using h'

theorem immediate : ImmediateObsEq action Obs observe p q := by
  intro b
  change false = false
  rfl

theorem not_pathBehEq : ¬ PathBehEq action Obs observe p q := by
  intro h
  have hh := h false V.z r
  rw [action.map_comp p r false, action.map_comp q r false] at hh
  rw [map_p, map_q, map_r, map_r] at hh
  change false = true at hh
  exact Bool.noConfusion hh

end FutureFixture

abbrev futureFixtureAction := FutureFixture.action
abbrev futureFixtureObs := FutureFixture.Obs
abbrev futureObserve := FutureFixture.observe
abbrev futureP := FutureFixture.p
abbrev futureQ := FutureFixture.q

theorem futureImmediateWeakness :
    ImmediateObsEq futureFixtureAction futureFixtureObs futureObserve
        futureP futureQ ∧
      ¬ PathBehEq futureFixtureAction futureFixtureObs futureObserve
        futureP futureQ :=
  ⟨FutureFixture.immediate, FutureFixture.not_pathBehEq⟩

namespace SourceFixture

inductive V | x | y deriving DecidableEq, Repr
inductive E | p | q deriving DecidableEq, Repr

instance : Fintype V where
  elems := {.x, .y}
  complete := by intro a; cases a <;> simp

instance : Fintype E where
  elems := {.p, .q}
  complete := by intro a; cases a <;> simp

def G : FiniteQuiver where
  V := V
  E := E
  vFinite := inferInstance
  eFinite := inferInstance
  vDecEq := inferInstance
  eDecEq := inferInstance
  src := fun _ => .x
  tgt := fun _ => .y

def edgeFn : E → Bool → Bool
  | .p => fun b => b
  | .q => fun _ => false

def prefunctor : Vertex G ⥤q Type where
  obj := fun _ => Bool
  map := fun e => TypeCat.ofHom (edgeFn e.1)

def action : PathAction G := actionOfPrefunctor prefunctor

def Obs : FreeCategory G → Type := fun _ => Bool
def observe (_ : FreeCategory G) (b : Bool) : Bool := b

def p : (show FreeCategory G from V.x) ⟶ (show FreeCategory G from V.y) :=
  (primitiveEdge G E.p).toPath

def q : (show FreeCategory G from V.x) ⟶ (show FreeCategory G from V.y) :=
  (primitiveEdge G E.q).toPath

@[simp] theorem map_p (b : Bool) : action.map p b = b := by
  have h := CategoryTheory.Paths.lift_toPath prefunctor
    (primitiveEdge G E.p)
  have h' := congrArg (fun f : Bool ⟶ Bool => f b) h
  simpa [prefunctor, edgeFn] using h'

@[simp] theorem map_q (b : Bool) : action.map q b = false := by
  have h := CategoryTheory.Paths.lift_toPath prefunctor
    (primitiveEdge G E.q)
  have h' := congrArg (fun f : Bool ⟶ Bool => f b) h
  simpa [prefunctor, edgeFn] using h'

def chosen : action.State (show FreeCategory G from V.x) := false

theorem chosen_equal : OneStateEq action Obs observe chosen p q := by
  change false = false
  rfl

theorem not_pathBehEq : ¬ PathBehEq action Obs observe p q := by
  intro h
  have hh := h true V.y (𝟙 (show FreeCategory G from V.y))
  have hp : p ≫ 𝟙 (show FreeCategory G from V.y) = p := Category.comp_id p
  have hq : q ≫ 𝟙 (show FreeCategory G from V.y) = q := Category.comp_id q
  rw [hp, hq, map_p, map_q] at hh
  change true = false at hh
  exact Bool.noConfusion hh

end SourceFixture

abbrev sourceFixtureAction := SourceFixture.action
abbrev sourceFixtureObs := SourceFixture.Obs
abbrev sourceObserve := SourceFixture.observe
abbrev sourceChosen := SourceFixture.chosen
abbrev sourceP := SourceFixture.p
abbrev sourceQ := SourceFixture.q

theorem sourceStateWeakness :
    OneStateEq sourceFixtureAction sourceFixtureObs sourceObserve
        sourceChosen sourceP sourceQ ∧
      ¬ PathBehEq sourceFixtureAction sourceFixtureObs sourceObserve
        sourceP sourceQ :=
  ⟨SourceFixture.chosen_equal, SourceFixture.not_pathBehEq⟩

end Nucleus.Fixtures
