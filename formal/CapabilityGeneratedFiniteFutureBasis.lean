import CapabilityGeneratedFutureInterface
import FiniteExecutableDistinguishingFuture

namespace CapabilityGeneratedFiniteFutureBasis

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture
open CapabilityGeneratedFutureInterface

/-- A finite capability carrier supplies its own complete finite enumeration.
    This is capability structure, not a separately chosen future/question list. -/
structure CertifiedFiniteCapabilityIndex (I : Type) where
  indices : List I
  covers : ∀ i : I, i ∈ indices

/-- Executable semantics remains explicit.  This preserves the previously
    certified boundary: an arbitrary Prop-valued repair is not automatically
    Boolean-decidable. -/
structure ExecutableCapabilitySemantics (I : Type) where
  predict : Repair I → I → Bool
  faithful : ∀ (R : Repair I) (i : I),
    predict R i = true ↔ R i

/-- Under the canonical capability-generated future map, semantic future
    reachability is exactly membership of the corresponding capability index. -/
theorem canonical_repair_reachable_iff
    {I : Type} (R : Repair I) (i : I) :
    RepairReachable (canonicalFutureInterface I).futureOf R i ↔ R i := by
  constructor
  · rintro ⟨j, hj, hji⟩
    cases hji
    exact hj
  · intro hi
    exact ⟨i, hi, rfl⟩

/-- The finite future basis is derived mechanically from the finite capability
    carrier.  No future carrier, naming map, or question list is supplied. -/
def derivedBasis
    {I : Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (E : ExecutableCapabilitySemantics I) :
    CertifiedFiniteFutureInterface I I (canonicalFutureInterface I).futureOf where
  questions := C.indices
  covers := C.covers
  predict := E.predict
  faithful := by
    intro R i
    rw [E.faithful R i]
    exact (canonical_repair_reachable_iff R i).symm

/-- The derived question list is definitionally the capability enumeration. -/
theorem questions_are_capability_indices
    {I : Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (E : ExecutableCapabilitySemantics I) :
    (derivedBasis C E).questions = C.indices := rfl

/-- Every capability-generated future is automatically present in the derived
    executable basis. -/
theorem every_generated_future_is_in_basis
    {I : Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (E : ExecutableCapabilitySemantics I)
    (i : I) :
    i ∈ (derivedBasis C E).questions := by
  exact C.covers i

/-- Bare behavioral inequivalence on the canonical capability-generated future
    interface forces an executable separator using only the capability carrier
    and explicit executable semantics. -/
theorem capability_indexed_search_finds_separator
    {I : Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (E : ExecutableCapabilitySemantics I)
    {R₁ R₂ : Repair I}
    (hneq : ¬ RepairEquivalent (canonicalFutureInterface I).futureOf R₁ R₂) :
    ∃ i,
      firstDistinguishingFuture (derivedBasis C E) R₁ R₂ = some i ∧
      E.predict R₁ i ≠ E.predict R₂ i := by
  exact executable_search_finds_separator (derivedBasis C E) hneq

/-- Thus the question-search layer no longer needs a separately supplied future
    basis: finite capability structure generates the finite basis consumed by
    the existing verified search. -/
theorem no_supplied_question_basis_needed
    {I : Type}
    (C : CertifiedFiniteCapabilityIndex I)
    (E : ExecutableCapabilitySemantics I)
    {R₁ R₂ : Repair I} :
    (¬ RepairEquivalent (canonicalFutureInterface I).futureOf R₁ R₂) →
    ∃ i,
      firstDistinguishingFuture (derivedBasis C E) R₁ R₂ = some i ∧
      E.predict R₁ i ≠ E.predict R₂ i := by
  intro hneq
  exact capability_indexed_search_finds_separator C E hneq

namespace Witness

inductive Idx where
  | alpha
  | beta
  deriving DecidableEq

def C : CertifiedFiniteCapabilityIndex Idx where
  indices := [.alpha, .beta]
  covers := by
    intro i
    cases i <;> simp

noncomputable def E : ExecutableCapabilitySemantics Idx := by
  classical
  exact {
    predict := fun R i => if R i then true else false
    faithful := by
      intro R i
      by_cases h : R i <;> simp [h]
  }

def leftRepair : Repair Idx
  | .alpha => True
  | .beta => False

def rightRepair : Repair Idx
  | .alpha => False
  | .beta => True

theorem inequivalent :
    ¬ RepairEquivalent (canonicalFutureInterface Idx).futureOf
      leftRepair rightRepair := by
  intro h
  have hl : RepairReachable (canonicalFutureInterface Idx).futureOf
      leftRepair Idx.alpha := by
    exact ⟨.alpha, trivial, rfl⟩
  have hr : ¬ RepairReachable (canonicalFutureInterface Idx).futureOf
      rightRepair Idx.alpha := by
    intro hreach
    exact (canonical_repair_reachable_iff rightRepair Idx.alpha).1 hreach
  exact hr ((h Idx.alpha).1 hl)

theorem derived_questions_exactly_indices :
    (derivedBasis C E).questions = [.alpha, .beta] := rfl

theorem search_finds_generated_separator :
    ∃ i,
      firstDistinguishingFuture (derivedBasis C E) leftRepair rightRepair = some i ∧
      E.predict leftRepair i ≠ E.predict rightRepair i := by
  exact capability_indexed_search_finds_separator C E inequivalent

end Witness

#check CertifiedFiniteCapabilityIndex
#check ExecutableCapabilitySemantics
#check canonical_repair_reachable_iff
#check derivedBasis
#check questions_are_capability_indices
#check every_generated_future_is_in_basis
#check capability_indexed_search_finds_separator
#check no_supplied_question_basis_needed
#check Witness.derived_questions_exactly_indices
#check Witness.search_finds_generated_separator

end CapabilityGeneratedFiniteFutureBasis
