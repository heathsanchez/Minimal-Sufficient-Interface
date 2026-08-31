import TemporalOrderInducesInteractionOrientation

namespace HistoryInducesTemporalOrientation

open InteractionInducesMutualRoleQuotients
open SymmetricInteractionCannotInduceDirectionalRoles
open TemporalOrderInducesInteractionOrientation

/-- An ordered observation history.  It names no participant roles and carries
    no separately supplied `before` relation. -/
structure TwoEventHistory where
  first : Node
  second : Node

/-- Precedence is read directly from the order of retained events. -/
def historyBefore (h : TwoEventHistory) (x y : Node) : Bool :=
  if x = h.first ∧ y = h.second then true else false

/-- A history and its temporal reversal contain the same two participants. -/
def forwardHistory : TwoEventHistory := ⟨Node.a, Node.b⟩
def reverseHistory : TwoEventHistory := ⟨Node.b, Node.a⟩

/-- Symmetric encounter is oriented only by the ordering present in history. -/
def orientFromHistory (h : TwoEventHistory) : Node → Node → Bool :=
  fun x y => encounter x y && historyBefore h x y

/-- Forgetting event order leaves only the symmetric encounter relation. -/
def historyOrderErased : Node → Node → Bool := encounter

theorem same_unordered_participants_opposite_order :
    forwardHistory.first = reverseHistory.second ∧
    forwardHistory.second = reverseHistory.first := by
  constructor <;> rfl

/-- The static forward orientation from the preceding theorem is exactly what
    is reconstructed from the forward event history. -/
theorem forward_history_recovers_orientation :
    orientFromHistory forwardHistory = oriented := by
  funext x y
  cases x <;> cases y <;> rfl

/-- Reversing only history order reconstructs the reverse orientation. -/
theorem reverse_history_recovers_reversed_orientation :
    orientFromHistory reverseHistory = reversed := by
  funext x y
  cases x <;> cases y <;> rfl

/-- The ordered history therefore induces the previously certified
    first-coordinate directional role without a primitive role partition. -/
theorem forward_history_induces_directional_role :
    ColEquivalent (orientFromHistory forwardHistory) Node.a Node.c ∧
    ¬ RowEquivalent (orientFromHistory forwardHistory) Node.a Node.c := by
  rw [forward_history_recovers_orientation]
  exact temporal_order_induces_directional_role

/-- Reversing the event order reverses the selected interaction. -/
theorem reversing_history_reverses_orientation :
    orientFromHistory reverseHistory Node.a Node.b = false ∧
    orientFromHistory reverseHistory Node.b Node.a = true := by
  rw [reverse_history_recovers_reversed_orientation]
  exact temporal_reversal_reverses_orientation

/-- The reversed history induces the dual directional role signature. -/
theorem reverse_history_induces_reversed_directional_role :
    ColEquivalent (orientFromHistory reverseHistory) Node.b Node.c ∧
    ¬ RowEquivalent (orientFromHistory reverseHistory) Node.b Node.c := by
  rw [reverse_history_recovers_reversed_orientation]
  exact reversed_order_induces_reversed_directional_role

/-- If only the unordered encounter is retained, the symmetry obstruction
    returns and a directional role split cannot be sustained. -/
theorem forgetting_history_order_erases_directional_role :
    ¬ (ColEquivalent historyOrderErased Node.a Node.c ∧
       ¬ RowEquivalent historyOrderErased Node.a Node.c) := by
  exact erasing_order_erases_directional_role_split

/-- The explicit `before` relation is eliminable in this witness: the order of
    verifier-visible events itself derives orientation, its reversal reverses
    orientation, and erasing the order erases the directional role distinction. -/
theorem history_order_induces_interaction_orientation :
    Symmetric encounter ∧
    orientFromHistory forwardHistory Node.a Node.b = true ∧
    orientFromHistory forwardHistory Node.b Node.a = false ∧
    orientFromHistory reverseHistory Node.a Node.b = false ∧
    orientFromHistory reverseHistory Node.b Node.a = true ∧
    (ColEquivalent (orientFromHistory forwardHistory) Node.a Node.c ∧
      ¬ RowEquivalent (orientFromHistory forwardHistory) Node.a Node.c) ∧
    ¬ (ColEquivalent historyOrderErased Node.a Node.c ∧
      ¬ RowEquivalent historyOrderErased Node.a Node.c) := by
  rw [forward_history_recovers_orientation, reverse_history_recovers_reversed_orientation]
  exact temporal_order_induces_interaction_orientation

#check same_unordered_participants_opposite_order
#check forward_history_recovers_orientation
#check reverse_history_recovers_reversed_orientation
#check forward_history_induces_directional_role
#check reversing_history_reverses_orientation
#check reverse_history_induces_reversed_directional_role
#check forgetting_history_order_erases_directional_role
#check history_order_induces_interaction_orientation

end HistoryInducesTemporalOrientation
