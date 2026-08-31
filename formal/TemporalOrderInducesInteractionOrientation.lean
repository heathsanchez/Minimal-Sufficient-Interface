import SymmetricInteractionCannotInduceDirectionalRoles

namespace TemporalOrderInducesInteractionOrientation

open InteractionInducesMutualRoleQuotients
open SymmetricInteractionCannotInduceDirectionalRoles

/-- A role-free, symmetric encounter relation on one undifferentiated carrier. -/
def encounter : Node → Node → Bool
  | Node.a, Node.b => true
  | Node.b, Node.a => true
  | _, _ => false

/-- Temporal precedence is the only directional evidence. -/
def before : Node → Node → Bool
  | Node.a, Node.b => true
  | _, _ => false

/-- Reversing the observed temporal order. -/
def after : Node → Node → Bool := fun x y => before y x

/-- Direction is derived, not supplied as a participant role. -/
def oriented : Node → Node → Bool := fun x y => encounter x y && before x y

/-- The same symmetric encounter under reversed temporal evidence. -/
def reversed : Node → Node → Bool := fun x y => encounter x y && after x y

/-- Erasing temporal information leaves only the symmetric encounter. -/
def orderErased : Node → Node → Bool := encounter

theorem encounter_is_symmetric : Symmetric encounter := by
  intro x y
  cases x <;> cases y <;> rfl

theorem order_erasure_cannot_induce_directional_roles (x y : Node) :
    RowEquivalent orderErased x y ↔ ColEquivalent orderErased x y := by
  exact symmetric_forces_row_col_equivalence orderErased encounter_is_symmetric x y

/-- Forward time selects exactly the a→b direction from a symmetric encounter. -/
theorem temporal_order_orients_forward :
    oriented Node.a Node.b = true ∧ oriented Node.b Node.a = false := by
  decide

/-- Reversing time reverses the selected interaction direction. -/
theorem temporal_reversal_reverses_orientation :
    reversed Node.a Node.b = false ∧ reversed Node.b Node.a = true := by
  decide

/-- The temporally oriented interaction reproduces the earlier one-fact
    relation extensionally; the orientation has now been derived from symmetric
    encounter plus order rather than supplied as a role-labelled edge. -/
theorem oriented_is_one_fact_interaction : oriented = oneFactInteraction := by
  funext x y
  cases x <;> cases y <;> rfl

/-- Forward temporal evidence induces a first-coordinate-only distinction. -/
theorem temporal_order_induces_directional_role :
    ColEquivalent oriented Node.a Node.c ∧
    ¬ RowEquivalent oriented Node.a Node.c := by
  rw [oriented_is_one_fact_interaction]
  exact induced_roles_are_directionally_asymmetric

/-- Erasing order destroys that directional role split. -/
theorem erasing_order_erases_directional_role_split :
    ¬ (ColEquivalent orderErased Node.a Node.c ∧
       ¬ RowEquivalent orderErased Node.a Node.c) := by
  intro h
  have hRow : RowEquivalent orderErased Node.a Node.c :=
    (order_erasure_cannot_induce_directional_roles Node.a Node.c).2 h.1
  exact h.2 hRow

/-- The reverse orientation has the dual directional signature: b is now
    first-coordinate-distinct from c while remaining second-coordinate-equivalent. -/
theorem reversed_order_induces_reversed_directional_role :
    ColEquivalent reversed Node.b Node.c ∧
    ¬ RowEquivalent reversed Node.b Node.c := by
  constructor
  · intro z
    cases z <;> rfl
  · intro h
    have hab := h Node.a
    simp [reversed, after, before, encounter] at hab

/-- A supplied role partition is unnecessary in this witness.  Symmetric
    encounter plus temporal precedence is sufficient to derive orientation;
    erasing precedence removes the directional quotient split and reversing
    precedence reverses the oriented interaction. -/
theorem temporal_order_induces_interaction_orientation :
    Symmetric encounter ∧
    oriented Node.a Node.b = true ∧
    oriented Node.b Node.a = false ∧
    reversed Node.a Node.b = false ∧
    reversed Node.b Node.a = true ∧
    (ColEquivalent oriented Node.a Node.c ∧
      ¬ RowEquivalent oriented Node.a Node.c) ∧
    ¬ (ColEquivalent orderErased Node.a Node.c ∧
      ¬ RowEquivalent orderErased Node.a Node.c) := by
  exact ⟨
    encounter_is_symmetric,
    temporal_order_orients_forward.1,
    temporal_order_orients_forward.2,
    temporal_reversal_reverses_orientation.1,
    temporal_reversal_reverses_orientation.2,
    temporal_order_induces_directional_role,
    erasing_order_erases_directional_role_split⟩

#check encounter_is_symmetric
#check order_erasure_cannot_induce_directional_roles
#check temporal_order_orients_forward
#check temporal_reversal_reverses_orientation
#check oriented_is_one_fact_interaction
#check temporal_order_induces_directional_role
#check erasing_order_erases_directional_role_split
#check reversed_order_induces_reversed_directional_role
#check temporal_order_induces_interaction_orientation

end TemporalOrderInducesInteractionOrientation
