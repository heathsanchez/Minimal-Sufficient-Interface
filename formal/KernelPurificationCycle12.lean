import KernelPurificationCycle11

namespace KernelPurificationCycle12

open KernelPurificationCycle9
open KernelPurificationCycle10
open KernelPurificationCycle11
open VerifiedConsequenceGenesis

universe u v w

/-- The old representation is always recoverable from its canonical
    consequence refinement. -/
theorem old_representation_factors_through_refinement
    {X : Type u} {R : Type v}
    (q : X → R) (c : X → Prop) :
    FactorsThrough (RefineWith q c) q := by
  refine ⟨Prod.fst, ?_⟩
  intro x
  rfl

/-- Factorization composes. -/
theorem factorsThrough_trans
    {X : Type u} {A : Type v} {B : Type w} {Y : Type}
    (q : X → A) (r : X → B) (c : X → Y)
    (hqr : FactorsThrough r q)
    (hcq : FactorsThrough q c) :
    FactorsThrough r c := by
  rcases hqr with ⟨qbar, hq⟩
  rcases hcq with ⟨cbar, hc⟩
  refine ⟨fun b => cbar (qbar b), ?_⟩
  intro x
  calc
    c x = cbar (q x) := hc x
    _ = cbar (qbar (r x)) := by rw [hq x]

/-- Every old consequence that was computable from q remains computable after
    the canonical refinement. -/
theorem old_language_survives_refinement
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop)
    (hfactor : LanguageFactorsThrough L q) :
    LanguageFactorsThrough L (RefineWith q c) := by
  intro i
  exact factorsThrough_trans q (RefineWith q c) (L.observe i)
    (old_representation_factors_through_refinement q c) (hfactor i)

/-- The representation repair forced by a directed interaction failure. -/
def repairedRepresentation
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {R : Type w}
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S) :
    S.Obj → R × Prop :=
  RefineWith q (failureConsequence r)

/-- Before repair the failure-generated consequence is unavailable through q;
    after the least one-coordinate refinement it is available. -/
theorem failure_generated_consequence_restored_by_least_refinement
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {R : Type w}
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S)
    (hcollapse : q r.left = q r.right) :
    (¬ FactorsThrough q (failureConsequence r)) ∧
    FactorsThrough (repairedRepresentation q r) (failureConsequence r) := by
  constructor
  · exact interaction_failure_forces_nonfactorization q r hcollapse
  · exact consequence_factors_through_refinement q (failureConsequence r)

/-- The repair strictly separates the verifier-certified failed interaction
    while preserving every distinction already encoded by q. -/
theorem failure_repair_is_strict_and_conservative
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {R : Type w}
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S)
    (hcollapse : q r.left = q r.right) :
    repairedRepresentation q r r.left ≠ repairedRepresentation q r r.right ∧
    (∀ x y : S.Obj,
      repairedRepresentation q r x = repairedRepresentation q r y →
      q x = q y) := by
  constructor
  · apply refinement_separates_witness q (failureConsequence r) hcollapse
    intro heq
    have hsep := failure_consequence_separates r
    exact hsep.2 (Eq.mp heq hsep.1)
  · exact refinement_preserves_old_representation q (failureConsequence r)

/-- Any alternative representation that preserves q and makes the
    failure-generated consequence available is at least as informative as the
    canonical repair. -/
theorem failure_repair_is_least_sufficient
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {R : Type w} {T : Type v}
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S)
    (alt : S.Obj → T)
    (hq : FactorsThrough alt q)
    (hc : FactorsThrough alt (failureConsequence r)) :
    FactorsThrough alt (repairedRepresentation q r) := by
  exact canonical_refinement_is_least_sufficient
    q (failureConsequence r) alt hq hc

/-- The same event that forces the representation repair also generates the
    new consequence-language coordinates: no separate language-expansion
    trigger is required. -/
theorem same_failure_repairs_representation_and_extends_language
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {I : Type v} {R : Type w}
    (L : ConsequenceLanguage S.Obj I)
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S)
    (hfactor : LanguageFactorsThrough L q)
    (hcollapse : q r.left = q r.right) :
    FactorsThrough (repairedRepresentation q r) (failureConsequence r) ∧
    LanguageFactorsThrough L (repairedRepresentation q r) ∧
    Nonempty (ResidualIndex q (failureConsequence r)) ∧
    Nonempty (Sum I (ResidualIndex q (failureConsequence r))) := by
  constructor
  · exact consequence_factors_through_refinement q (failureConsequence r)
  constructor
  · exact old_language_survives_refinement L q (failureConsequence r) hfactor
  constructor
  · exact failure_generated_nonfactor_support_nonempty q r hcollapse
  · exact ⟨Sum.inr (interactionSupportWitness q r hcollapse)⟩

/-- After repair, the exact original factorization obstruction is closed: the
    consequence generated by the failed interaction now factors through the
    repaired representation.  Reapplying this same obligation therefore yields
    no factorization residual of that consequence. -/
theorem repaired_state_closes_triggering_obligation
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {R : Type w}
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S) :
    FactorsThrough (repairedRepresentation q r) (failureConsequence r) := by
  exact consequence_factors_through_refinement q (failureConsequence r)

/-- Cycle-12 capstone: one verifier-visible interaction failure causes an
    end-to-end developmental turn.  It generates its own consequence; that
    consequence certifies the current representation is too coarse; the
    canonical least refinement restores factorization without forgetting old
    information; and the same failure generates the enlarged consequence
    language. -/
theorem one_failure_closes_one_full_developmental_turn
    {S : ReachabilityGeneratesConsequence.DirectedSubstrate}
    {I : Type v} {R : Type w}
    (L : ConsequenceLanguage S.Obj I)
    (q : S.Obj → R)
    (r : ReachabilityGeneratesConsequence.DirectedFailure S)
    (hfactor : LanguageFactorsThrough L q)
    (hcollapse : q r.left = q r.right) :
    (failureConsequence r r.left ∧ ¬ failureConsequence r r.right) ∧
    (¬ FactorsThrough q (failureConsequence r)) ∧
    FactorsThrough (repairedRepresentation q r) (failureConsequence r) ∧
    LanguageFactorsThrough L (repairedRepresentation q r) ∧
    repairedRepresentation q r r.left ≠ repairedRepresentation q r r.right ∧
    (∀ (T : Type) (alt : S.Obj → T),
      FactorsThrough alt q →
      FactorsThrough alt (failureConsequence r) →
      FactorsThrough alt (repairedRepresentation q r)) := by
  constructor
  · exact failure_consequence_separates r
  constructor
  · exact interaction_failure_forces_nonfactorization q r hcollapse
  constructor
  · exact consequence_factors_through_refinement q (failureConsequence r)
  constructor
  · exact old_language_survives_refinement L q (failureConsequence r) hfactor
  constructor
  · exact (failure_repair_is_strict_and_conservative q r hcollapse).1
  · intro T alt hq hc
    exact canonical_refinement_is_least_sufficient
      q (failureConsequence r) alt hq hc

#check old_representation_factors_through_refinement
#check old_language_survives_refinement
#check failure_generated_consequence_restored_by_least_refinement
#check failure_repair_is_strict_and_conservative
#check failure_repair_is_least_sufficient
#check same_failure_repairs_representation_and_extends_language
#check repaired_state_closes_triggering_obligation
#check one_failure_closes_one_full_developmental_turn

end KernelPurificationCycle12
