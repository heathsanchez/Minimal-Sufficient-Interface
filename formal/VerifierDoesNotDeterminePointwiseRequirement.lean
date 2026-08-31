import ConsequentialCompletionCoupling

namespace VerifierDoesNotDeterminePointwiseRequirement

/-- A repair proposal is only a set of capability indices to make available. -/
abbrev Repair (I : Type) := I → Prop

/-- A generic verifier judges whole repair proposals.  It does not provide a
    pointwise requirement predicate. -/
structure RepairVerifier (I : Type) where
  accepts : Repair I → Prop

/-- The strongest pointwise requirement derivable from verifier acceptance
    alone: an index is necessary iff every accepted repair contains it. -/
def Necessary {I : Type} (V : RepairVerifier I) (i : I) : Prop :=
  ∀ R, V.accepts R → R i

/-- The induced pointwise repair is the intersection of all accepted repairs. -/
def necessaryRepair {I : Type} (V : RepairVerifier I) : Repair I :=
  fun i => Necessary V i

/-- Purification counterexample: the verifier accepts either of two alternative
    singleton repairs.  There is no pointwise capability present in every
    accepted repair, and the intersection of successful repairs is itself
    rejected. -/
namespace DisjunctiveWitness

inductive Idx where
  | left
  | right

def V : RepairVerifier Idx where
  accepts := fun R => R .left ∨ R .right

def leftRepair : Repair Idx
  | .left => True
  | .right => False

def rightRepair : Repair Idx
  | .left => False
  | .right => True

/-- Both alternative repairs satisfy the exact same verifier. -/
theorem left_accepted : V.accepts leftRepair := by
  exact Or.inl trivial

theorem right_accepted : V.accepts rightRepair := by
  exact Or.inr trivial

/-- The verifier does not force the left capability, because the right-only
    repair succeeds. -/
theorem left_not_necessary : ¬ Necessary V .left := by
  intro h
  have hleft : rightRepair .left := h rightRepair right_accepted
  exact hleft

/-- Nor does it force the right capability. -/
theorem right_not_necessary : ¬ Necessary V .right := by
  intro h
  have hright : leftRepair .right := h leftRepair left_accepted
  exact hright

/-- Hence the pointwise intersection of all accepted repairs contains neither
    possible repair capability. -/
theorem necessary_repair_empty (i : Idx) : ¬ necessaryRepair V i := by
  cases i with
  | left => exact left_not_necessary
  | right => exact right_not_necessary

/-- The decisive negative: the repair consisting of everything individually
    necessary across all successful repairs is not itself successful. -/
theorem intersection_of_successful_repairs_can_fail :
    ¬ V.accepts (necessaryRepair V) := by
  intro h
  rcases h with hleft | hright
  · exact left_not_necessary hleft
  · exact right_not_necessary hright

/-- Neither accepted singleton contains the other.  Thus verifier success has a
    genuine version space, not a hidden unique least repair. -/
theorem accepted_repairs_incomparable :
    (¬ (∀ i, leftRepair i → rightRepair i)) ∧
    (¬ (∀ i, rightRepair i → leftRepair i)) := by
  constructor
  · intro h
    have : rightRepair .left := h .left trivial
    exact this
  · intro h
    have : leftRepair .right := h .right trivial
    exact this

/-- There is no verifier-accepted repair contained in both successful singleton
    repairs.  In particular there is no least accepted repair under inclusion. -/
theorem no_common_accepted_subrepair :
    ¬ ∃ R : Repair Idx,
      V.accepts R ∧
      (∀ i, R i → leftRepair i) ∧
      (∀ i, R i → rightRepair i) := by
  rintro ⟨R, hacc, hL, hR⟩
  rcases hacc with hleft | hright
  · have : rightRepair .left := hR .left hleft
    exact this
  · have : leftRepair .right := hL .right hright
    exact this

end DisjunctiveWitness

/-- Cycle-5 obstruction: a generic verifier contract does not determine a
    pointwise requirement landscape by universal necessity.  Successful repair
    sets can be irreducibly disjunctive, so purification must retain a version
    space (or add extra structure selecting among equivalent/minimal repairs). -/
theorem verifier_acceptance_does_not_force_pointwise_requirement :
    ∃ (I : Type) (V : RepairVerifier I),
      (∃ R, V.accepts R) ∧
      ¬ V.accepts (necessaryRepair V) := by
  refine ⟨DisjunctiveWitness.Idx, DisjunctiveWitness.V, ?_,
    DisjunctiveWitness.intersection_of_successful_repairs_can_fail⟩
  exact ⟨DisjunctiveWitness.leftRepair, DisjunctiveWitness.left_accepted⟩

#check Necessary
#check necessaryRepair
#check DisjunctiveWitness.left_not_necessary
#check DisjunctiveWitness.right_not_necessary
#check DisjunctiveWitness.intersection_of_successful_repairs_can_fail
#check DisjunctiveWitness.accepted_repairs_incomparable
#check DisjunctiveWitness.no_common_accepted_subrepair
#check verifier_acceptance_does_not_force_pointwise_requirement

end VerifierDoesNotDeterminePointwiseRequirement
