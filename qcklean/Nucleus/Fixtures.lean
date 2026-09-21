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
    have h := congrArg (fun f : φ.obj X ⟶ φ.obj X => f x)
      ((CategoryTheory.Paths.lift φ).map_id X)
    simpa using h
  map_comp := by
    intro X Y Z p q x
    have h := congrArg (fun f : φ.obj X ⟶ φ.obj Z => f x)
      ((CategoryTheory.Paths.lift φ).map_comp p q)
    simpa using h

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

theorem immediate : ImmediateObsEq action Obs observe p q := by
  intro b
  rfl

theorem not_pathBehEq : ¬ PathBehEq action Obs observe p q := by
  intro h
  have hh := h false V.z r
  simp [action, actionOfPrefunctor, p, q, r, prefunctor, edgeFn, observe] at hh

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

def chosen : action.State (show FreeCategory G from V.x) := false

theorem chosen_equal : OneStateEq action Obs observe chosen p q := by
  rfl

theorem not_pathBehEq : ¬ PathBehEq action Obs observe p q := by
  intro h
  have hh := h true V.y (𝟙 V.y)
  simp [action, actionOfPrefunctor, p, q, prefunctor, edgeFn, observe] at hh

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
