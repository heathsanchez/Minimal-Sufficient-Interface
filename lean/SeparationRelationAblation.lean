import Std
import IdentityCompositionConsequence

namespace MinimalSufficientInterface.SeparationRelationAblation

universe u v

/-!
One-shot primitive foundation tournament.

This file pushes below the previous action/composition calculus in one pass:

  raw separation
    -> exact laws needed for identity
    -> all/no-distinction and complete-distinction extremes
    -> action as independent dynamic structure
    -> action invariance as an extra law
    -> compositional closure as an extra law
    -> reconstruction of the existing identity/composition/consequence calculus

Every claimed dependency is paired with a finite countermodel when the assumption is removed.
-/

structure Separation (X : Type u) where
  sep : X → X → Prop

def Same (S : Separation X) (x y : X) : Prop := ¬ S.sep x y

def Refines (S T : Separation X) : Prop := ∀ x y, S.sep x y → T.sep x y

theorem relation_extension_refines_identity
    (S T : Separation X) (hST : Refines S T) {x y : X}
    (hT : Same T x y) : Same S x y := by
  intro hS
  exact hT (hST x y hS)

theorem separation_forces_split
    (S : Separation X) {x y : X} (h : S.sep x y) : ¬ Same S x y := by
  intro hs
  exact hs h

theorem strict_change_is_separation
    (S T : Separation X) {x y : X}
    (_hOld : Same S x y) (hNew : ¬ Same T x y) : T.sep x y := by
  simpa [Same] using hNew

def emptySeparation (X : Type u) : Separation X := ⟨fun _ _ => False⟩

theorem empty_separation_collapses_all (x y : X) :
    Same (emptySeparation X) x y := by
  simp [Same, emptySeparation]

theorem reflexivity_not_derivable :
    ∃ (S : Separation Bool) (x : Bool), ¬ Same S x x := by
  let S : Separation Bool := ⟨fun _ _ => True⟩
  exact ⟨S, false, by simp [Same, S]⟩

theorem symmetry_not_derivable :
    ∃ (S : Separation Bool) (x y : Bool), Same S x y ∧ ¬ Same S y x := by
  let S : Separation Bool := ⟨fun x y => x = true ∧ y = false⟩
  exact ⟨S, false, true, by simp [Same, S], by simp [Same, S]⟩

theorem transitivity_not_derivable :
    ∃ (S : Separation (Fin 3)) (x y z : Fin 3),
      Same S x y ∧ Same S y z ∧ ¬ Same S x z := by
  let S : Separation (Fin 3) := ⟨fun x y => x = 0 ∧ y = 2⟩
  exact ⟨S, 0, 1, 2, by simp [Same, S], by simp [Same, S], by simp [Same, S]⟩

structure LawfulSeparation (X : Type u) extends Separation X where
  irrefl : ∀ x, ¬ sep x x
  symm : ∀ {x y}, sep x y → sep y x
  cotrans : ∀ {x z}, sep x z → ∀ y, sep x y ∨ sep y z

theorem lawful_same_refl (S : LawfulSeparation X) (x : X) : Same S.toSeparation x x := by
  exact S.irrefl x

theorem lawful_same_symm (S : LawfulSeparation X) {x y : X}
    (h : Same S.toSeparation x y) : Same S.toSeparation y x := by
  intro hyx
  exact h (S.symm hyx)

theorem lawful_same_trans (S : LawfulSeparation X) {x y z : X}
    (hxy : Same S.toSeparation x y) (hyz : Same S.toSeparation y z) :
    Same S.toSeparation x z := by
  intro hxz
  rcases S.cotrans hxz y with hxySep | hyzSep
  · exact hxy hxySep
  · exact hyz hyzSep

theorem irrefl_is_independently_needed :
    ∃ (S : Separation Bool),
      (∀ {x y}, S.sep x y → S.sep y x) ∧
      (∀ {x z}, S.sep x z → ∀ y, S.sep x y ∨ S.sep y z) ∧
      (∃ x, ¬ Same S x x) := by
  let S : Separation Bool := ⟨fun _ _ => True⟩
  refine ⟨S, ?_, ?_, false, ?_⟩
  · intro x y h; trivial
  · intro x z hxz y; exact Or.inl trivial
  · simp [Same, S]

theorem symmetry_is_independently_needed :
    ∃ (S : Separation Bool),
      (∀ x, ¬ S.sep x x) ∧
      (∀ {x z}, S.sep x z → ∀ y, S.sep x y ∨ S.sep y z) ∧
      (∃ x y, Same S x y ∧ ¬ Same S y x) := by
  let S : Separation Bool := ⟨fun x y => x = true ∧ y = false⟩
  refine ⟨S, ?_, ?_, false, true, ?_, ?_⟩
  · intro x
    cases x <;> simp [S]
  · intro x z hxz y
    rcases hxz with ⟨rfl, rfl⟩
    cases y <;> simp [S]
  · simp [Same, S]
  · simp [Same, S]

theorem cotrans_is_independently_needed :
    ∃ (S : Separation (Fin 3)),
      (∀ x, ¬ S.sep x x) ∧
      (∀ {x y}, S.sep x y → S.sep y x) ∧
      (∃ x y z, Same S x y ∧ Same S y z ∧ ¬ Same S x z) := by
  let S : Separation (Fin 3) :=
    ⟨fun x y => (x = 0 ∧ y = 2) ∨ (x = 2 ∧ y = 0)⟩
  refine ⟨S, ?_, ?_, 0, 1, 2, ?_, ?_, ?_⟩
  · intro x h
    rcases h with h | h
    · have h02 : (0 : Fin 3) ≠ 2 := by decide
      exact h02 (h.1.symm.trans h.2)
    · have h20 : (2 : Fin 3) ≠ 0 := by decide
      exact h20 (h.1.symm.trans h.2)
  · intro x y h
    rcases h with h | h
    · exact Or.inr ⟨h.2, h.1⟩
    · exact Or.inl ⟨h.2, h.1⟩
  · intro h
    simp [S] at h
  · intro h
    simp [S] at h
  · intro h
    exact h (Or.inl ⟨rfl, rfl⟩)

def neqSeparation (X : Type u) : Separation X := ⟨fun x y => x ≠ y⟩

theorem neq_same_iff_eq (x y : X) : Same (neqSeparation X) x y ↔ x = y := by
  constructor
  · intro h
    by_cases hxy : x = y
    · exact hxy
    · exact False.elim (h hxy)
  · intro hxy hsep
    exact hsep hxy

def lawfulNeqSeparation (X : Type u) : LawfulSeparation X where
  sep := fun x y => x ≠ y
  irrefl := by intro x h; exact h rfl
  symm := by
    intro x y hxy hyx
    exact hxy hyx.symm
  cotrans := by
    intro x z hxz y
    by_cases hxy : x = y
    · right
      intro hyz
      exact hxz (hxy.trans hyz)
    · exact Or.inl hxy

theorem no_distinction_does_not_mean_no_states :
    Nonempty Bool ∧ (∀ x y : Bool, Same (emptySeparation Bool) x y) := by
  exact ⟨⟨false⟩, fun x y => empty_separation_collapses_all x y⟩

structure Action (M : Type u) (X : Type v) where
  act : M → X → X

def a1 : Action Bool Bool := ⟨fun m x => if m then x else !x⟩
def a2 : Action Bool Bool := ⟨fun m x => if m then !x else x⟩

def inducedSep (A : Action Bool Bool) : Separation Bool :=
  ⟨fun x y => ∃ m, A.act m x ≠ A.act m y⟩

theorem same_separation_incompatible_actions :
    (∀ x y, (inducedSep a1).sep x y ↔ (inducedSep a2).sep x y) ∧
    a1.act true false ≠ a2.act true false := by
  constructor
  · intro x y
    cases x <;> cases y <;> simp [inducedSep, a1, a2]
  · simp [a1, a2]

def twoClassSeparation : LawfulSeparation (Fin 3) where
  sep := fun x y => (x = 2 ∧ y ≠ 2) ∨ (x ≠ 2 ∧ y = 2)
  irrefl := by
    intro x h
    rcases h with h | h
    · exact h.2 h.1
    · exact h.1 h.2
  symm := by
    intro x y h
    rcases h with h | h
    · exact Or.inr ⟨h.2, h.1⟩
    · exact Or.inl ⟨h.2, h.1⟩
  cotrans := by
    intro x z hxz y
    rcases hxz with hxz | hxz
    · by_cases hy : y = 2
      · right; exact Or.inl ⟨hy, hxz.2⟩
      · left; exact Or.inl ⟨hxz.1, hy⟩
    · by_cases hy : y = 2
      · left; exact Or.inr ⟨hxz.1, hy⟩
      · right; exact Or.inr ⟨hy, hxz.2⟩

def badDynamic : Action Bool (Fin 3) :=
  ⟨fun m x => if m then (if x = 1 then 2 else x) else x⟩

theorem lawful_static_identity_does_not_force_dynamic_invariance :
    Same twoClassSeparation.toSeparation 0 1 ∧
    ¬ Same twoClassSeparation.toSeparation (badDynamic.act true 0) (badDynamic.act true 1) := by
  constructor
  · simp [Same, twoClassSeparation]
  · simp [Same, twoClassSeparation, badDynamic]

def RespectsSame {M : Type u} {X : Type v} (S : Separation X) (A : Action M X) : Prop :=
  ∀ m x y, Same S x y → Same S (A.act m x) (A.act m y)

def HasComposition {M : Type u} {X : Type v} (A : Action M X) : Prop :=
  ∃ comp : M → M → M, ∀ f g x, A.act (comp f g) x = A.act f (A.act g x)

def rotate3 : Fin 3 → Fin 3
  | 0 => 1
  | 1 => 2
  | 2 => 0

def nonClosedAction : Action Bool (Fin 3) :=
  ⟨fun m x => if m then rotate3 x else x⟩

theorem action_does_not_imply_compositional_closure : ¬ HasComposition nonClosedAction := by
  intro h
  rcases h with ⟨comp, hcomp⟩
  have h0 := hcomp true true 0
  have h1 := hcomp true true 1
  cases hc : comp true true <;> simp [nonClosedAction, rotate3, hc] at h0 h1

/-- First lawful dynamic layer: action is supplied, but it must preserve the identity
induced by lawful separation. This is not derivable from separation alone. -/
structure LawfulDynamic (M : Type u) (X : Type v) (S : LawfulSeparation X)
    extends Action M X where
  respects : RespectsSame S.toSeparation toAction

/-- Second dynamic layer: identity action and exact sequential composition are supplied.
No associativity or unit equations on `comp` are assumed. -/
structure ClosedDynamic (M : Type u) (X : Type v) (S : LawfulSeparation X)
    extends LawfulDynamic M X S where
  one : M
  comp : M → M → M
  one_act : ∀ x, act one x = x
  comp_act : ∀ f g x, act (comp f g) x = act f (act g x)

/-- Once lawful dynamics and compositional closure are present, the previous
identity/composition/consequence calculus is recovered exactly, with no extra
associativity or unit axioms. -/
def ClosedDynamic.toCalculus {M : Type u} {X : Type v} {S : LawfulSeparation X}
    (D : ClosedDynamic M X S) :
    IdentityCompositionConsequence.Calculus M X where
  one := D.one
  comp := D.comp
  act := D.act
  one_act := D.one_act
  comp_act := D.comp_act

/-- Reconstruction is semantic, not merely structural: the recovered calculus has
exactly the same action as the bottom-layer dynamic system. -/
theorem reconstructed_action_is_original
    {M : Type u} {X : Type v} {S : LawfulSeparation X}
    (D : ClosedDynamic M X S) (m : M) (x : X) :
    D.toCalculus.act m x = D.act m x := rfl

/-- The bottom-up dependency boundary is exact in the tested finite witnesses:
separation alone does not determine dynamics, and action alone does not determine
compositional closure; but adding those two independently necessary layers
reconstructs the existing calculus. -/
theorem bottom_up_reconstruction_boundary :
    (∃ (A B : Action Bool Bool),
      (∀ x y, (inducedSep A).sep x y ↔ (inducedSep B).sep x y) ∧
      A.act true false ≠ B.act true false) ∧
    (∃ (A : Action Bool (Fin 3)), ¬ HasComposition A) := by
  exact ⟨⟨a1, a2, same_separation_incompatible_actions.1,
      same_separation_incompatible_actions.2⟩,
    ⟨nonClosedAction, action_does_not_imply_compositional_closure⟩⟩

/-- Full one-shot dependency result. The first component certifies lawful identity;
the second certifies that lawful static identity does not force dynamic invariance;
the third certifies that action does not force closure. -/
theorem primitive_foundation_dependency_chain :
    (∀ x : Bool, Same (lawfulNeqSeparation Bool).toSeparation x x) ∧
    (∃ (S : LawfulSeparation (Fin 3)) (A : Action Bool (Fin 3)) (x y : Fin 3),
      Same S.toSeparation x y ∧
      ¬ Same S.toSeparation (A.act true x) (A.act true y)) ∧
    (∃ (A : Action Bool (Fin 3)), ¬ HasComposition A) := by
  refine ⟨?_, ?_, ?_⟩
  · intro x
    exact lawful_same_refl (lawfulNeqSeparation Bool) x
  · exact ⟨twoClassSeparation, badDynamic, 0, 1,
      lawful_static_identity_does_not_force_dynamic_invariance.1,
      lawful_static_identity_does_not_force_dynamic_invariance.2⟩
  · exact ⟨nonClosedAction, action_does_not_imply_compositional_closure⟩

end MinimalSufficientInterface.SeparationRelationAblation
