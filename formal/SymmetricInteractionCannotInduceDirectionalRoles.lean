import InteractionInducesMutualRoleQuotients

namespace SymmetricInteractionCannotInduceDirectionalRoles

open InteractionInducesMutualRoleQuotients

universe u

abbrev GenericInteraction (α : Type u) := α → α → Bool

/-- Symmetry means the bare interaction contains no verifier-visible orientation
    between its two coordinates. -/
def Symmetric {α : Type u} (R : GenericInteraction α) : Prop :=
  ∀ x y, R x y = R y x

/-- First-coordinate observational equivalence for an arbitrary carrier. -/
def RowEquivalent {α : Type u} (R : GenericInteraction α) (x y : α) : Prop :=
  ∀ z, R x z = R y z

/-- Second-coordinate observational equivalence for an arbitrary carrier. -/
def ColEquivalent {α : Type u} (R : GenericInteraction α) (x y : α) : Prop :=
  ∀ z, R z x = R z y

/-- If interaction is symmetric, the two consequence-induced role quotients are
    extensionally identical. -/
theorem symmetric_forces_row_col_equivalence
    {α : Type u} (R : GenericInteraction α)
    (hSymm : Symmetric R) (x y : α) :
    RowEquivalent R x y ↔ ColEquivalent R x y := by
  constructor
  · intro hRow z
    calc
      R z x = R x z := hSymm z x
      _ = R y z := hRow z
      _ = R z y := (hSymm z y).symm
  · intro hCol z
    calc
      R x z = R z x := hSymm x z
      _ = R z y := hCol z
      _ = R y z := (hSymm y z).symm

/-- Consequently a symmetric interaction cannot distinguish two nodes in only
    the first-coordinate role while leaving them equivalent in the second. -/
theorem symmetric_blocks_row_only_role
    {α : Type u} (R : GenericInteraction α)
    (hSymm : Symmetric R) (x y : α) :
    ¬ (¬ RowEquivalent R x y ∧ ColEquivalent R x y) := by
  intro h
  exact h.1 ((symmetric_forces_row_col_equivalence R hSymm x y).2 h.2)

/-- Nor can it distinguish two nodes only in the second-coordinate role. -/
theorem symmetric_blocks_col_only_role
    {α : Type u} (R : GenericInteraction α)
    (hSymm : Symmetric R) (x y : α) :
    ¬ (RowEquivalent R x y ∧ ¬ ColEquivalent R x y) := by
  intro h
  exact h.2 ((symmetric_forces_row_col_equivalence R hSymm x y).1 h.1)

/-- Bridge the generic definitions to the previous single-carrier witness. -/
theorem witness_row_equivalent_iff :
    RowEquivalent oneFactInteraction Node.a Node.c ↔
      RowEq oneFactInteraction Node.a Node.c := by
  rfl

theorem witness_col_equivalent_iff :
    ColEquivalent oneFactInteraction Node.a Node.c ↔
      ColEq oneFactInteraction Node.a Node.c := by
  rfl

/-- The previously verified directional role asymmetry therefore certifies that
    some orientation is genuinely present in the interaction evidence; it could
    not have been recovered from a symmetric/unoriented observation alone. -/
theorem witnessed_directional_roles_force_interaction_asymmetry :
    ¬ Symmetric oneFactInteraction := by
  intro hSymm
  have hCol : ColEquivalent oneFactInteraction Node.a Node.c := by
    exact witness_col_equivalent_iff.mpr induced_roles_are_directionally_asymmetric.1
  have hRow : RowEquivalent oneFactInteraction Node.a Node.c :=
    (symmetric_forces_row_col_equivalence oneFactInteraction hSymm Node.a Node.c).2 hCol
  have hNotRow : ¬ RowEquivalent oneFactInteraction Node.a Node.c := by
    intro h
    exact induced_roles_are_directionally_asymmetric.2 (witness_row_equivalent_iff.mp h)
  exact hNotRow hRow

/-- Information-theoretic boundary: consequence may induce directional roles
    without a supplied role partition, but not from fully permutation-symmetric
    interaction evidence.  Some verifier-visible asymmetry must enter somewhere. -/
theorem symmetric_interaction_cannot_induce_directional_roles :
    (∀ {α : Type u} (R : GenericInteraction α),
      Symmetric R → ∀ x y, RowEquivalent R x y ↔ ColEquivalent R x y) ∧
    ¬ Symmetric oneFactInteraction := by
  constructor
  · intro α R h x y
    exact symmetric_forces_row_col_equivalence R h x y
  · exact witnessed_directional_roles_force_interaction_asymmetry

#check symmetric_forces_row_col_equivalence
#check symmetric_blocks_row_only_role
#check symmetric_blocks_col_only_role
#check witnessed_directional_roles_force_interaction_asymmetry
#check symmetric_interaction_cannot_induce_directional_roles

end SymmetricInteractionCannotInduceDirectionalRoles
