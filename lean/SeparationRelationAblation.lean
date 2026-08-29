import Std

namespace MinimalSufficientInterface.SeparationRelationAblation

universe u

/-!
One-shot primitive foundation tournament.

This file deliberately pushes below the previous action/composition calculus in one pass:

  raw separation
    -> exact laws needed for identity
    -> all/no-distinction and complete-distinction extremes
    -> action as independent dynamic structure
    -> action invariance as an extra law
    -> compositional closure as an extra law

Every claimed dependency is paired with a finite countermodel when the assumption is removed.
-/

/-- Raw verified distinction. No states are assumed to be objects in any richer algebra. -/
structure Separation (X : Type u) where
  sep : X → X → Prop

/-- Consequential identity is non-separation. -/
def Same (S : Separation X) (x y : X) : Prop := ¬ S.sep x y

/-- Adding verified distinctions refines identity. -/
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

/-- No verified distinctions: maximal consequential identification. -/
def emptySeparation (X : Type u) : Separation X := ⟨fun _ _ => False⟩

theorem empty_separation_collapses_all (x y : X) :
    Same (emptySeparation X) x y := by
  simp [Same, emptySeparation]

/-- Raw separation alone does not force reflexive identity. -/
theorem reflexivity_not_derivable :
    ∃ (S : Separation Bool) (x : Bool), ¬ Same S x x := by
  let S : Separation Bool := ⟨fun _ _ => True⟩
  exact ⟨S, false, by simp [Same, S]⟩

/-- Raw separation alone does not force symmetric identity. -/
theorem symmetry_not_derivable :
    ∃ (S : Separation Bool) (x y : Bool), Same S x y ∧ ¬ Same S y x := by
  let S : Separation Bool := ⟨fun x y => x = true ∧ y = false⟩
  exact ⟨S, false, true, by simp [Same, S], by simp [Same, S]⟩

/-- Raw separation alone does not force transitive identity. -/
theorem transitivity_not_derivable :
    ∃ (S : Separation (Fin 3)) (x y z : Fin 3),
      Same S x y ∧ Same S y z ∧ ¬ Same S x z := by
  let S : Separation (Fin 3) := ⟨fun x y => x = 0 ∧ y = 2⟩
  exact ⟨S, 0, 1, 2, by simp [Same, S], by simp [Same, S], by simp [Same, S]⟩

/-- The exact relation laws that make non-separation an equivalence relation. -/
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

/-- Irreflexivity is independently necessary: symmetry+cotransitivity do not rescue reflexivity. -/
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

/-- Symmetry is independently necessary: irrefl+cotransitivity do not rescue symmetry. -/
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

/-- Cotransitivity is independently necessary: irrefl+symmetry do not rescue transitivity. -/
theorem cotrans_is_independently_needed :
    ∃ (S : Separation (Fin 3)),
      (∀ x, ¬ S.sep x x) ∧
      (∀ {x y}, S.sep x y → S.sep y x) ∧
      (∃ x y z, Same S x y ∧ Same S y z ∧ ¬ Same S x z) := by
  let S : Separation (Fin 3) :=
    ⟨fun x y => (x = 0 ∧ y = 2) ∨ (x = 2 ∧ y = 0)⟩
  refine ⟨S, ?_, ?_, 0, 1, 2, ?_, ?_, ?_⟩
  · intro x
    fin_cases x <;> simp [S]
  · intro x y h
    rcases h with h | h
    · exact Or.inr ⟨h.2, h.1⟩
    · exact Or.inl ⟨h.2, h.1⟩
  · simp [Same, S]
  · simp [Same, S]
  · simp [Same, S]

/-- Complete verified distinction: every unequal pair is separated. -/
def neqSeparation (X : Type u) : Separation X := ⟨fun x y => x ≠ y⟩

theorem neq_same_iff_eq (x y : X) : Same (neqSeparation X) x y ↔ x = y := by
  constructor
  · intro h
    by_cases hxy : x = y
    · exact hxy
    · exact False.elim (h hxy)
  · intro hxy hsep
    exact hsep hxy

/-- Complete distinction is lawful: its induced identity is ordinary equality. -/
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

/-- No-distinction and no-states are not the same notion: an inhabited world can have no separators. -/
theorem no_distinction_does_not_mean_no_states :
    Nonempty Bool ∧ (∀ x y : Bool, Same (emptySeparation Bool) x y) := by
  exact ⟨⟨false⟩, fun x y => empty_separation_collapses_all x y⟩

/-- Dynamics is additional structure, not reconstructible from the static separation relation. -/
structure Action (M : Type u) (X : Type u) where
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
    simp [inducedSep, a1, a2]
    constructor <;> intro h
    · exact ⟨true, h⟩
    · exact ⟨false, h⟩
  · decide

/-- Static identity does not make arbitrary future action identity-respecting. -/
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
      · left; exact Or.inr ⟨hxz.1 ▸ by decide, hy⟩
    · by_cases hy : y = 2
      · left; exact Or.inl ⟨hy, hxz.1⟩
      · right; exact Or.inr ⟨hy, hxz.2⟩

def badDynamic : Action Bool (Fin 3) :=
  ⟨fun m x => if m then (if x = 1 then 2 else x) else x⟩

theorem lawful_static_identity_does_not_force_dynamic_invariance :
    Same twoClassSeparation.toSeparation 0 1 ∧
    ¬ Same twoClassSeparation.toSeparation (badDynamic.act true 0) (badDynamic.act true 1) := by
  constructor
  · simp [Same, twoClassSeparation]
  · simp [Same, twoClassSeparation, badDynamic]

/-- The exact extra bridge from static identity to lawful dynamics. -/
def RespectsSame {M X : Type u} (S : Separation X) (A : Action M X) : Prop :=
  ∀ m x y, Same S x y → Same S (A.act m x) (A.act m y)

/-- Sequential compositional closure is another independent layer. -/
def HasComposition {M X : Type u} (A : Action M X) : Prop :=
  ∃ comp : M → M → M, ∀ f g x, A.act (comp f g) x = A.act f (A.act g x)

/-- A finite action family can fail to contain its own sequential composites. -/
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

/-- Final one-shot dependency result: the static core is strictly weaker than dynamics,
and dynamics is strictly weaker than compositional closure. -/
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
