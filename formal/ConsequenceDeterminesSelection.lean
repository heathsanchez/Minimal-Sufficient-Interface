import Std

namespace ConsequenceDeterminesSelection

/-- A frozen selector with no distinguished candidate identity.  It inspects
    candidates only through the externally supplied consequence predicate and
    returns the first verified separator. -/
def selectByConsequence {α : Type} (separates : α → Bool) : List α → Option α
  | [] => none
  | x :: xs =>
      if separates x = true then some x else selectByConsequence separates xs

/-- Exactly one candidate has the verified separating consequence. -/
def UniqueSeparator {α : Type} (separates : α → Bool) (seed : α) : Prop :=
  separates seed = true ∧ ∀ x, separates x = true → x = seed

/-- If a pool contains the unique verified separator, the frozen selector
    recovers it.  The theorem is polymorphic in the candidate type and in the
    identity of the separator: no candidate name is privileged by the rule. -/
theorem unique_separator_selected
    {α : Type} (separates : α → Bool) (pool : List α) (seed : α)
    (hmem : seed ∈ pool)
    (huniq : UniqueSeparator separates seed) :
    selectByConsequence separates pool = some seed := by
  induction pool with
  | nil =>
      simp at hmem
  | cons a rest ih =>
      simp only [selectByConsequence]
      by_cases ha : separates a = true
      · have haseed : a = seed := huniq.2 a ha
        subst a
        simp [huniq.1]
      · have hmemrest : seed ∈ rest := by
          rcases List.mem_cons.mp hmem with haseed | hrest
          · subst a
            exact False.elim (ha huniq.1)
          · exact hrest
        simp [ha, ih hmemrest]

/-- Candidate ordering cannot affect the answer when consequence supplies a
    unique separator.  This is stronger than invariance under a particular
    permutation: *any* two pool orders containing the separator agree. -/
theorem order_invariant_under_unique_consequence
    {α : Type} (separates : α → Bool) (seed : α)
    (pool₁ pool₂ : List α)
    (huniq : UniqueSeparator separates seed)
    (hmem₁ : seed ∈ pool₁) (hmem₂ : seed ∈ pool₂) :
    selectByConsequence separates pool₁ =
      selectByConsequence separates pool₂ := by
  rw [unique_separator_selected separates pool₁ seed hmem₁ huniq]
  rw [unique_separator_selected separates pool₂ seed hmem₂ huniq]

/-- If verified consequence is ablated entirely, the same frozen selector
    selects nothing. -/
theorem no_consequence_no_selection
    {α : Type} (pool : List α) :
    selectByConsequence (fun _ : α => false) pool = none := by
  induction pool with
  | nil => rfl
  | cons a rest ih =>
      simp [selectByConsequence, ih]

/-- The retained primitive is exactly the output of consequence-based
    selection; there is no separate identity parameter in this definition. -/
def RetainedBySelection {α : Type}
    (separates : α → Bool) (pool : List α) (x : α) : Prop :=
  selectByConsequence separates pool = some x

/-- Under a unique verified consequence, the retained primitive is exactly the
    unique separator. -/
theorem retained_iff_unique_separator
    {α : Type} (separates : α → Bool) (pool : List α) (seed x : α)
    (hmem : seed ∈ pool)
    (huniq : UniqueSeparator separates seed) :
    RetainedBySelection separates pool x ↔ x = seed := by
  unfold RetainedBySelection
  rw [unique_separator_selected separates pool seed hmem huniq]
  simp

/-- If the verified consequence changes which anonymous candidate is uniquely
    separating, the same frozen selector changes which primitive it retains. -/
theorem changing_consequence_changes_selected_identity
    {α : Type} (pool : List α) (a b : α)
    (sepA sepB : α → Bool)
    (hma : a ∈ pool) (hmb : b ∈ pool)
    (hA : UniqueSeparator sepA a)
    (hB : UniqueSeparator sepB b) :
    selectByConsequence sepA pool = some a ∧
      selectByConsequence sepB pool = some b := by
  exact ⟨unique_separator_selected sepA pool a hma hA,
    unique_separator_selected sepB pool b hmb hB⟩

/-- Exact formal criterion used here for "identity blind": for every candidate
    type, every consequence predicate, every possible candidate identity and
    every pool containing the unique separator, selection follows consequence;
    if consequence is removed, selection disappears. -/
def IdentityBlindConsequenceCriterion : Prop :=
  (∀ (α : Type) (separates : α → Bool) (pool : List α) (seed : α),
      seed ∈ pool → UniqueSeparator separates seed →
        selectByConsequence separates pool = some seed) ∧
  (∀ (α : Type) (pool : List α),
      selectByConsequence (fun _ : α => false) pool = none)

/-- The frozen selector satisfies the identity-blind consequence criterion. -/
theorem selection_is_consequence_determined_not_identity_encoded :
    IdentityBlindConsequenceCriterion := by
  constructor
  · intro α separates pool seed hmem huniq
    exact unique_separator_selected separates pool seed hmem huniq
  · intro α pool
    exact no_consequence_no_selection pool

end ConsequenceDeterminesSelection

#check ConsequenceDeterminesSelection.unique_separator_selected
#check ConsequenceDeterminesSelection.order_invariant_under_unique_consequence
#check ConsequenceDeterminesSelection.no_consequence_no_selection
#check ConsequenceDeterminesSelection.retained_iff_unique_separator
#check ConsequenceDeterminesSelection.changing_consequence_changes_selected_identity
#check ConsequenceDeterminesSelection.selection_is_consequence_determined_not_identity_encoded
