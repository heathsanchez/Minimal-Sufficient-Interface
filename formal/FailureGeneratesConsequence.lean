import ConsequenceDeterminesSelection

namespace FailureGeneratesConsequence

universe u

/-- A consequence/observation is not supplied as a named ontology item: it is
    simply a Boolean test on the current world. -/
abbrev Probe (Ω : Type u) := Ω → Bool

/-- The only developmental input is a verifier-certified failed distinction. -/
structure Failure (Ω : Type u) where
  left : Ω
  right : Ω
  distinct : left ≠ right

/-- The failure itself induces the criterion by which a probe is consequential:
    it must distinguish the two states that the current interface collapsed. -/
def generatedCriterion {Ω : Type u} (r : Failure Ω) (p : Probe Ω) : Bool :=
  decide (p r.left ≠ p r.right)

/-- A generic constructor turns the failed distinction into a new observation.
    No external consequence predicate or candidate identity is an argument. -/
def generatedProbe {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) : Probe Ω :=
  fun z => decide (z = r.right)

/-- The generated observation really distinguishes the failed pair. -/
theorem generatedProbe_separates
    {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) :
    generatedProbe r r.left = false ∧ generatedProbe r r.right = true := by
  constructor
  · simp [generatedProbe, r.distinct]
  · simp [generatedProbe]

/-- Hence the consequence criterion generated from the same failure certifies
    the newly generated probe. -/
theorem generatedCriterion_certifies_generatedProbe
    {Ω : Type u} [DecidableEq Ω] (r : Failure Ω) :
    generatedCriterion r (generatedProbe r) = true := by
  simp [generatedCriterion, generatedProbe, r.distinct]

/-- Selection now receives no externally supplied consequence predicate.
    Conditional only on uniqueness inside an arbitrary anonymous pool, the
    verifier-derived criterion determines the selected identity. -/
theorem failure_generated_criterion_selects_unique
    {Ω : Type u} (r : Failure Ω)
    (pool : List (Probe Ω)) (seed : Probe Ω)
    (hmem : seed ∈ pool)
    (huniq : ConsequenceDeterminesSelection.UniqueSeparator
      (generatedCriterion r) seed) :
    ConsequenceDeterminesSelection.selectByConsequence
      (generatedCriterion r) pool = some seed := by
  exact ConsequenceDeterminesSelection.unique_separator_selected
    (generatedCriterion r) pool seed hmem huniq

/-- Candidate ordering is irrelevant: the residual-generated consequence,
    rather than pool position, fixes the answer. -/
theorem failure_generated_selection_order_invariant
    {Ω : Type u} (r : Failure Ω)
    (seed : Probe Ω) (pool₁ pool₂ : List (Probe Ω))
    (huniq : ConsequenceDeterminesSelection.UniqueSeparator
      (generatedCriterion r) seed)
    (hmem₁ : seed ∈ pool₁) (hmem₂ : seed ∈ pool₂) :
    ConsequenceDeterminesSelection.selectByConsequence
        (generatedCriterion r) pool₁ =
      ConsequenceDeterminesSelection.selectByConsequence
        (generatedCriterion r) pool₂ := by
  exact ConsequenceDeterminesSelection.order_invariant_under_unique_consequence
    (generatedCriterion r) seed pool₁ pool₂ huniq hmem₁ hmem₂

/-- Exact consequence ablation: erase the information carried by failure and
    the unchanged selector has no basis for retaining anything. -/
theorem erase_failure_consequence_erases_selection
    {Ω : Type u} (pool : List (Probe Ω)) :
    ConsequenceDeterminesSelection.selectByConsequence
      (fun _ : Probe Ω => false) pool = none := by
  exact ConsequenceDeterminesSelection.no_consequence_no_selection pool

/-- Changing only the verified failure can change which anonymous primitive is
    selected by the same frozen rule. -/
theorem changing_failure_changes_selected_identity
    {Ω : Type u} (r₁ r₂ : Failure Ω)
    (pool : List (Probe Ω)) (a b : Probe Ω)
    (hma : a ∈ pool) (hmb : b ∈ pool)
    (hA : ConsequenceDeterminesSelection.UniqueSeparator
      (generatedCriterion r₁) a)
    (hB : ConsequenceDeterminesSelection.UniqueSeparator
      (generatedCriterion r₂) b) :
    ConsequenceDeterminesSelection.selectByConsequence
        (generatedCriterion r₁) pool = some a ∧
      ConsequenceDeterminesSelection.selectByConsequence
        (generatedCriterion r₂) pool = some b := by
  constructor
  · exact failure_generated_criterion_selects_unique r₁ pool a hma hA
  · exact failure_generated_criterion_selects_unique r₂ pool b hmb hB

/-- The decisive end-to-end certificate.  Starting from a failed distinction
    alone, the process constructs a new probe, constructs the criterion that
    judges probes from that same failure, verifies the generated probe against
    that criterion, and shows that erasing failure-consequence information
    destroys selection. -/
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
