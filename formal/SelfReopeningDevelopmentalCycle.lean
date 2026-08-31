import ConsequentialCompletionCoupling
import RecursiveFiniteVersionSpaceResolution

namespace SelfReopeningDevelopmentalCycle

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open GenericVerifiedCompletionKernel
open RequirementLandscapeCompletion
open ConsequentialCompletionCoupling
open FiniteExecutableDistinguishingFuture
open ExecutablePairSelectionFromFiniteVersionSpace
open RecursiveFiniteVersionSpaceResolution

/-- Cycle 13 couples the two independently certified halves of the purified
    kernel.  A free completion can make a previously unavailable future
    executable; if that future separates two live repair candidates, then old
    consequential identity reopens, while the same autonomous finite resolver
    reconverges without a supplied pair, question, or iteration bound. -/
theorem completion_reopens_and_autonomous_resolution_reconverges
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (L : RequirementLandscape I Cap)
    (B : CertifiedFiniteFutureInterface I F J.futureOf)
    (truth : F → Bool)
    {i : I} {R₁ R₂ : Repair I}
    (hbefore : EquivalentUnder (reachableBefore (Cap := Cap) J)
      (fun f R => B.predict R f) R₁ R₂)
    (hreq : L.required i)
    (habs : ¬ Nonempty (Cap i))
    (hsep : B.predict R₁ (J.futureOf i) ≠ B.predict R₂ (J.futureOf i)) :
    EquivalentUnder (reachableBefore (Cap := Cap) J)
      (fun f R => B.predict R f) R₁ R₂ ∧
    reachableAfter J L (J.futureOf i) ∧
    ¬ EquivalentUnder (reachableAfter J L)
      (fun f R => B.predict R f) R₁ R₂ ∧
    firstUnresolvedPair B (resolve B truth [R₁, R₂]) = none := by
  refine ⟨hbefore, residual_fill_makes_future_reachable J L hreq habs, ?_, ?_⟩
  · exact completion_can_strictly_refine_consequential_equivalence
      J (fun f R => B.predict R f) L hbefore hreq habs hsep
  · exact recursive_finite_resolution_terminates_at_confluence
      B truth [R₁, R₂]

/-- The terminal candidates after reopening and recursive diagnosis lie in one
    future-behavioural class. -/
theorem completion_reopens_then_survivors_are_consequentially_equivalent
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (L : RequirementLandscape I Cap)
    (B : CertifiedFiniteFutureInterface I F J.futureOf)
    (truth : F → Bool)
    {i : I} {R₁ R₂ : Repair I}
    (hbefore : EquivalentUnder (reachableBefore (Cap := Cap) J)
      (fun f R => B.predict R f) R₁ R₂)
    (hreq : L.required i)
    (habs : ¬ Nonempty (Cap i))
    (hsep : B.predict R₁ (J.futureOf i) ≠ B.predict R₂ (J.futureOf i)) :
    (¬ EquivalentUnder (reachableAfter J L)
      (fun f R => B.predict R f) R₁ R₂) ∧
    (∀ A, A ∈ resolve B truth [R₁, R₂] →
      ∀ C, C ∈ resolve B truth [R₁, R₂] →
        RepairEquivalent J.futureOf A C) := by
  constructor
  · exact completion_can_strictly_refine_consequential_equivalence
      J (fun f R => B.predict R f) L hbefore hreq habs hsep
  · intro A hA C hC
    exact recursive_survivors_are_consequentially_equivalent
      B truth [R₁, R₂] A hA C hC

namespace Witness

inductive Idx where | probe deriving DecidableEq
inductive Fut where | probe deriving DecidableEq

abbrev EmptyCap : Idx → Type := fun _ => Empty

def J : FutureInterface Idx Fut where
  futureOf := fun _ => .probe

def L : RequirementLandscape Idx EmptyCap where
  required := fun _ => True

def positiveRepair : Repair Idx := fun _ => True

def negativeRepair : Repair Idx := fun _ => False

noncomputable def basis : CertifiedFiniteFutureInterface Idx Fut J.futureOf := by
  classical
  refine {
    questions := [.probe]
    covers := ?_
    predict := fun R _ => if R .probe then true else false
    faithful := ?_
  }
  · intro f
    cases f
    simp
  · intro R f
    cases f
    constructor
    · intro h
      by_cases hr : R .probe
      · exact ⟨.probe, hr, rfl⟩
      · simp [hr] at h
    · rintro ⟨i, hi, hif⟩
      cases i
      simpa [hi]

noncomputable def observe : Fut → Repair Idx → Bool :=
  fun f R => basis.predict R f

def truth : Fut → Bool := fun _ => true

theorem capability_absent : ¬ Nonempty (EmptyCap Idx.probe) := by
  intro h
  rcases h with ⟨h⟩
  exact nomatch h

theorem requirement_present : L.required Idx.probe := trivial

/-- Before completion no future is executable, so the two candidates are
    consequentially identical relative to the actually reachable interface. -/
theorem old_stage_confluent :
    EquivalentUnder (reachableBefore (Cap := EmptyCap) J)
      observe positiveRepair negativeRepair := by
  intro f hreach
  rcases hreach with ⟨i, ⟨hcap⟩, _⟩
  exact nomatch hcap

/-- The freely generated capability makes the previously unavailable probe
    future executable. -/
theorem completion_promotes_probe :
    reachableAfter J L Fut.probe := by
  exact residual_fill_makes_future_reachable J L
    requirement_present capability_absent

/-- The promoted future exposes a distinction that was literally unobservable
    at the old stage. -/
theorem promoted_probe_separates :
    observe Fut.probe positiveRepair ≠ observe Fut.probe negativeRepair := by
  classical
  simp [observe, basis, positiveRepair, negativeRepair]

theorem completion_reopens_old_confluence :
    ¬ EquivalentUnder (reachableAfter J L)
      observe positiveRepair negativeRepair := by
  exact completion_can_strictly_refine_consequential_equivalence
    J observe L old_stage_confluent requirement_present capability_absent
    promoted_probe_separates

/-- Ablating the requirement removes the generated route to the probe. -/
theorem ablation_blocks_promotion :
    ¬ Nonempty
      (completeLandscape
        (erasedLandscape : RequirementLandscape Idx EmptyCap) Idx.probe) := by
  exact erased_requirement_blocks_generated_route J capability_absent

/-- The expanded certified interface now autonomously finds the distinction. -/
theorem expanded_interface_has_unresolved_pair :
    ∃ A C f,
      firstUnresolvedPair basis [positiveRepair, negativeRepair] = some (A, C, f) := by
  have hneq : ¬ RepairEquivalent J.futureOf positiveRepair negativeRepair := by
    intro h
    have hp : RepairReachable J.futureOf positiveRepair Fut.probe :=
      ⟨.probe, trivial, rfl⟩
    have hn : ¬ RepairReachable J.futureOf negativeRepair Fut.probe := by
      rintro ⟨i, hi, _⟩
      exact hi
    exact hn ((h Fut.probe).1 hp)
  rcases multiclasse_ambiguity_forces_pair_selection
      basis [positiveRepair, negativeRepair]
      ⟨positiveRepair, by simp, negativeRepair, by simp, hneq⟩ with
    ⟨A, C, f, hscan, _, _, _⟩
  exact ⟨A, C, f, hscan⟩

/-- After the completion-induced reopening, the same generic resolver reaches
    consequential confluence again. -/
theorem autonomous_reconvergence :
    firstUnresolvedPair basis
      (resolve basis truth [positiveRepair, negativeRepair]) = none := by
  exact recursive_finite_resolution_terminates_at_confluence
    basis truth [positiveRepair, negativeRepair]

/-- The self-reopening cycle is inhabited end-to-end on an unchanged repair
    carrier: old confluence, generated future, reopened distinction, autonomous
    diagnostic reconvergence. -/
theorem self_reopening_developmental_cycle :
    EquivalentUnder (reachableBefore (Cap := EmptyCap) J)
        observe positiveRepair negativeRepair ∧
    reachableAfter J L Fut.probe ∧
    ¬ EquivalentUnder (reachableAfter J L)
        observe positiveRepair negativeRepair ∧
    firstUnresolvedPair basis
        (resolve basis truth [positiveRepair, negativeRepair]) = none := by
  exact completion_reopens_and_autonomous_resolution_reconverges
    J L basis truth old_stage_confluent requirement_present capability_absent
    promoted_probe_separates

end Witness

#check completion_reopens_and_autonomous_resolution_reconverges
#check completion_reopens_then_survivors_are_consequentially_equivalent
#check Witness.old_stage_confluent
#check Witness.completion_promotes_probe
#check Witness.promoted_probe_separates
#check Witness.completion_reopens_old_confluence
#check Witness.ablation_blocks_promotion
#check Witness.expanded_interface_has_unresolved_pair
#check Witness.autonomous_reconvergence
#check Witness.self_reopening_developmental_cycle

end SelfReopeningDevelopmentalCycle
