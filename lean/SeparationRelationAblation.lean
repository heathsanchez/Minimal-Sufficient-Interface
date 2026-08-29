import Std

namespace MinimalSufficientInterface.SeparationRelationAblation

universe u

/-- Relation-only substrate: `sep x y` says a verified consequence distinguishes x and y.
No transformations, observations, or action map are assumed. -/
structure Separation (X : Type u) where
  sep : X → X → Prop

/-- Identity induced by failure of verified separation. -/
def Same (S : Separation X) (x y : X) : Prop := ¬ S.sep x y

/-- Adding verified separations can only refine induced identity. -/
def Refines (S T : Separation X) : Prop := ∀ x y, S.sep x y → T.sep x y

theorem relation_extension_refines_identity
    (S T : Separation X) (hST : Refines S T) {x y : X}
    (hT : Same T x y) : Same S x y := by
  intro hS
  exact hT (hST x y hS)

/-- A verified separation directly forces a split. -/
theorem separation_forces_split
    (S : Separation X) {x y : X} (h : S.sep x y) : ¬ Same S x y := by
  intro hs
  exact hs h

/-- If identity changes from same to split, the relation itself contains the separator. -/
theorem strict_change_is_separation
    (S T : Separation X) {x y : X}
    (hOld : Same S x y) (hNew : ¬ Same T x y) : T.sep x y := by
  classical
  by_contra h
  exact hNew h

/-- Empty separation is the operational NOTHING case: all states collapse. -/
def emptySeparation (X : Type u) : Separation X := ⟨fun _ _ => False⟩

theorem empty_separation_collapses_all (x y : X) :
    Same (emptySeparation X) x y := by
  simp [Same, emptySeparation]

/-- A relation-only substrate does not force identity to be reflexive. -/
theorem reflexivity_not_derivable :
    ∃ (S : Separation Bool) (x : Bool), ¬ Same S x x := by
  let S : Separation Bool := ⟨fun _ _ => True⟩
  exact ⟨S, false, by simp [Same, S]⟩

/-- Nor does it force induced identity to be symmetric. -/
theorem symmetry_not_derivable :
    ∃ (S : Separation Bool) (x y : Bool), Same S x y ∧ ¬ Same S y x := by
  let S : Separation Bool := ⟨fun x y => x = true ∧ y = false⟩
  refine ⟨S, false, true, ?_, ?_⟩
  · simp [Same, S]
  · simp [Same, S]

/-- Nor does it force transitivity. -/
theorem transitivity_not_derivable :
    ∃ (S : Separation (Fin 3)) (x y z : Fin 3),
      Same S x y ∧ Same S y z ∧ ¬ Same S x z := by
  let S : Separation (Fin 3) := ⟨fun x y => x = 0 ∧ y = 2⟩
  refine ⟨S, 0, 1, 2, ?_, ?_, ?_⟩ <;> simp [Same, S]

/-- Two incompatible action semantics can induce exactly the same verified separation
relation. Hence a separation relation cannot reconstruct action semantics. -/
structure Action (X : Type u) where
  act : Bool → X → X

def a1 : Action Bool := ⟨fun m x => if m then x else !x⟩
def a2 : Action Bool := ⟨fun m x => if m then !x else x⟩

def inducedSep (A : Action Bool) : Separation Bool :=
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

/-- Decision boundary: relation-only distinction is sufficient for bare split/refinement,
but insufficient to derive equivalence laws or reconstruct transformations. -/
theorem relation_core_summary
    (S T : Separation X) (hST : Refines S T) {x y : X}
    (hT : Same T x y) : Same S x y :=
  relation_extension_refines_identity S T hST hT

end MinimalSufficientInterface.SeparationRelationAblation
