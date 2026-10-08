import DevelopmentalCategory

/-!
R7: canonical refinement of a typed, stage-invariant equivalence.
Reuses the exact Action, Stage, and quotient semantics of the pinned R6 core.
No Mathlib, axioms, sorry, or finite-model/game assumptions.
-/

universe u v w z

namespace CanonicalRefinement

open TypedBehaviouralCongruence
open DevelopmentalCategory

variable (C : SmallCategory) (A : Action C)
variable (D : C.Obj → Type z) (d : ∀ X, A.State X → D X)

/-- A relation on each state type, without coercing different objects together. -/
abbrev Relation : Type _ :=
  ∀ X : C.Obj, A.State X → A.State X → Prop

/-- Stage invariance: admitted actions preserve the existing relation. -/
def InvariantAt (S : Stage C) (E : Relation C A) : Prop :=
  ∀ {X Y : C.Obj} (f : C.Hom X Y), S.allow f →
    ∀ x y, E X x y → E Y (A.map f x) (A.map f y)

/-- Local compatibility with the newly protected observation. -/
def Compatible (E : Relation C A) : Prop :=
  ∀ X x y, E X x y → d X x = d X y

/-- The canonical refinement: retain E and preserve d after every admitted future.
    This is the pointwise, typed version of R6's Ref_S(E,d). -/
def RefS (S : Stage C) (E : Relation C A) : Relation C A :=
  fun X x y =>
    E X x y ∧
      ∀ (Y : C.Obj) (f : C.Hom X Y), S.allow f →
        d Y (A.map f x) = d Y (A.map f y)

/-- Refinement never merges a pair not merged by E. -/
theorem refS_sub (S : Stage C) (E : Relation C A) :
    ∀ X x y, RefS C A D d S E X x y → E X x y := by
  intro X x y h
  exact h.1

/-- The refinement protects the new observation at the identity action. -/
theorem refS_compatible (S : Stage C) (E : Relation C A) :
    Compatible C A D d (RefS C A D d S E) := by
  intro X x y h
  have hId := h.2 X (C.id X) (S.id_allow X)
  calc
    d X x = d X (A.map (C.id X) x) :=
      congrArg (d X) (A.map_id x).symm
    _ = d X (A.map (C.id X) y) := hId
    _ = d X y := congrArg (d X) (A.map_id y)

/-- E stage-invariant implies its canonical refinement is stage-invariant. -/
theorem refS_invariant (S : Stage C) (E : Relation C A)
    (hInv : InvariantAt C A S E) :
    InvariantAt C A S (RefS C A D d S E) := by
  intro X Y f hf x y hxy
  refine ⟨hInv f hf x y hxy.1, ?_⟩
  intro Z g hg
  have h := hxy.2 Z (C.comp g f) (S.comp_allow g f hg hf)
  calc
    d Z (A.map g (A.map f x)) =
        d Z (A.map (C.comp g f) x) :=
          congrArg (d Z) (A.map_comp g f x).symm
    _ = d Z (A.map (C.comp g f) y) := h
    _ = d Z (A.map g (A.map f y)) :=
          congrArg (d Z) (A.map_comp g f y)

/-- The canonical refinement is the greatest admissible-action-invariant
    subrelation of E that respects the newly protected local observation. -/
theorem refS_greatest (S : Stage C) (E R : Relation C A)
    (hRInv : InvariantAt C A S R)
    (hRE : ∀ X x y, R X x y → E X x y)
    (hRD : Compatible C A D d R) :
    ∀ X x y, R X x y → RefS C A D d S E X x y := by
  intro X x y hR
  refine ⟨hRE X x y hR, ?_⟩
  intro Y f hf
  exact hRD Y _ _ (hRInv f hf x y hR)

/-- An equivalence E remains an equivalence after canonical refinement. -/
theorem refS_equivalence (S : Stage C) (E : Relation C A)
    (hrefl : ∀ X x, E X x x)
    (hsymm : ∀ X x y, E X x y → E X y x)
    (htrans : ∀ X x y z, E X x y → E X y z → E X x z) :
    ∀ X, Equivalence (RefS C A D d S E X) := by
  intro X
  refine ⟨?_, ?_, ?_⟩
  · intro x
    exact ⟨hrefl X x, by intro Y f hf; rfl⟩
  · intro x y hxy
    refine ⟨hsymm X x y hxy.1, ?_⟩
    intro Y f hf
    exact (hxy.2 Y f hf).symm
  · intro x y z hxy hyz
    refine ⟨htrans X x y z hxy.1 hyz.1, ?_⟩
    intro Y f hf
    exact (hxy.2 Y f hf).trans (hyz.2 Y f hf)

end CanonicalRefinement
