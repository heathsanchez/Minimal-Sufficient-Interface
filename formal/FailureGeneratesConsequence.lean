import Std

namespace FailureGeneratesConsequence

universe u

abbrev Probe (Ω : Type u) := Ω → Bool

structure Failure (Ω : Type u) where
  left : Ω
  right : Ω
  distinct : left ≠ right

/-- Consequentiality is generated from the verifier-certified failure itself:
    a probe matters exactly when it distinguishes the failed pair. -/
def generatedCriterion {Ω : Type u} (r : Failure Ω) (p : Probe Ω) : Bool :=
  decide (p r.left ≠ p r.right)

/-- Generic residual-to-observation constructor.  No consequence language,
    primitive identity, or candidate index is supplied. -/
def generatedProbe {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) : Probe Ω :=
  fun z => decide (z = r.right)

def selectByConsequence {α : Type} (separates : α → Bool) : List α → Option α
  | [] => none
  | x :: xs =>
      if separates x = true then some x else selectByConsequence separates xs

def UniqueSeparator {α : Type} (separates : α → Bool) (seed : α) : Prop :=
  separates seed = true ∧ ∀ x, separates x = true → x = seed

theorem unique_separator_selected
    {α : Type} (separates : α → Bool) (pool : List α) (seed : α)
    (hmem : seed ∈ pool) (huniq : UniqueSeparator separates seed) :
    selectByConsequence separates pool = some seed := by
  induction pool with
  | nil => simp at hmem
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

theorem no_consequence_no_selection
    {α : Type} (pool : List α) :
    selectByConsequence (fun _ : α => false) pool = none := by
  induction pool with
  | nil => rfl
  | cons a rest ih => simp [selectByConsequence, ih]

theorem generatedProbe_separates
    {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) :
    generatedProbe r r.left = false ∧ generatedProbe r r.right = true := by
  constructor
  · simp [generatedProbe, r.distinct]
  · simp [generatedProbe]

theorem generatedCriterion_certifies_generatedProbe
    {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) :
    generatedCriterion r (generatedProbe r) = true := by
  simp [generatedCriterion, generatedProbe, r.distinct]

/-- No externally supplied consequence predicate occurs in the theorem
    signature.  The selector's criterion is computed solely from `r`. -/
theorem failure_generated_criterion_selects_unique
    {Ω : Type u} (r : Failure Ω)
    (pool : List (Probe Ω)) (seed : Probe Ω)
    (hmem : seed ∈ pool)
    (huniq : UniqueSeparator (generatedCriterion r) seed) :
    selectByConsequence (generatedCriterion r) pool = some seed := by
  exact unique_separator_selected (generatedCriterion r) pool seed hmem huniq

theorem failure_generated_selection_order_invariant
    {Ω : Type u} (r : Failure Ω)
    (seed : Probe Ω) (pool₁ pool₂ : List (Probe Ω))
    (huniq : UniqueSeparator (generatedCriterion r) seed)
    (hmem₁ : seed ∈ pool₁) (hmem₂ : seed ∈ pool₂) :
    selectByConsequence (generatedCriterion r) pool₁ =
      selectByConsequence (generatedCriterion r) pool₂ := by
  rw [failure_generated_criterion_selects_unique r pool₁ seed hmem₁ huniq]
  rw [failure_generated_criterion_selects_unique r pool₂ seed hmem₂ huniq]

theorem erase_failure_consequence_erases_selection
    {Ω : Type u} (pool : List (Probe Ω)) :
    selectByConsequence (fun _ : Probe Ω => false) pool = none := by
  exact no_consequence_no_selection pool

theorem changing_failure_changes_selected_identity
    {Ω : Type u} (r₁ r₂ : Failure Ω)
    (pool : List (Probe Ω)) (a b : Probe Ω)
    (hma : a ∈ pool) (hmb : b ∈ pool)
    (hA : UniqueSeparator (generatedCriterion r₁) a)
    (hB : UniqueSeparator (generatedCriterion r₂) b) :
    selectByConsequence (generatedCriterion r₁) pool = some a ∧
      selectByConsequence (generatedCriterion r₂) pool = some b := by
  exact ⟨failure_generated_criterion_selects_unique r₁ pool a hma hA,
    failure_generated_criterion_selects_unique r₂ pool b hmb hB⟩

/-- End-to-end local certificate: failure alone generates both a separating
    observation and the criterion that certifies that observation. -/
theorem failure_generates_consequence_certificate
    {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) :
    (generatedProbe r r.left = false ∧ generatedProbe r r.right = true) ∧
    generatedCriterion r (generatedProbe r) = true := by
  exact ⟨generatedProbe_separates r,
    generatedCriterion_certifies_generatedProbe r⟩

end FailureGeneratesConsequence

#check FailureGeneratesConsequence.generatedProbe_separates
#check FailureGeneratesConsequence.generatedCriterion_certifies_generatedProbe
#check FailureGeneratesConsequence.failure_generated_criterion_selects_unique
#check FailureGeneratesConsequence.failure_generated_selection_order_invariant
#check FailureGeneratesConsequence.erase_failure_consequence_erases_selection
#check FailureGeneratesConsequence.changing_failure_changes_selected_identity
#check FailureGeneratesConsequence.failure_generates_consequence_certificate
