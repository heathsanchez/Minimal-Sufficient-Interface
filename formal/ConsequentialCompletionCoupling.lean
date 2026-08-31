import RequirementLandscapeCompletion

namespace ConsequentialCompletionCoupling

open GenericVerifiedCompletionKernel
open RequirementLandscapeCompletion

/-- Behavioural equality is defined only by futures that are currently
    reachable.  This is the generic MSI/Nerode side of the kernel. -/
def EquivalentUnder
    {X F : Type}
    (reachable : F → Prop)
    (observe : F → X → Bool)
    (x y : X) : Prop :=
  ∀ f, reachable f → observe f x = observe f y

/-- Capability indices can make futures executable.  No representation or
    quotient classes are supplied: reachability is induced by actual capability
    inhabitation. -/
structure FutureInterface (I F : Type) where
  futureOf : I → F

/-- Futures reachable from the old capability family. -/
def reachableBefore
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F) : F → Prop :=
  fun f => ∃ i, Nonempty (Cap i) ∧ J.futureOf i = f

/-- Futures reachable after the requirement-driven free completion. -/
def reachableAfter
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (L : RequirementLandscape I Cap) : F → Prop :=
  fun f => ∃ i, Nonempty (completeLandscape L i) ∧ J.futureOf i = f

/-- Old futures remain reachable after completion. -/
theorem old_future_retained
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (L : RequirementLandscape I Cap)
    {f : F} :
    reachableBefore (Cap := Cap) J f → reachableAfter J L f := by
  rintro ⟨i, ⟨h⟩, hif⟩
  exact ⟨i, ⟨RequirementLandscapeCompletion.includeOld h⟩, hif⟩

/-- A required absent capability makes its associated future newly reachable. -/
theorem residual_fill_makes_future_reachable
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (L : RequirementLandscape I Cap)
    {i : I}
    (hreq : L.required i)
    (habs : ¬ Nonempty (Cap i)) :
    reachableAfter J L (J.futureOf i) := by
  exact ⟨i, every_required_absence_is_filled L hreq habs, rfl⟩

/-- If the failed index was absent before, its associated future was not
    reachable through that same index.  This is a local reachability negative,
    deliberately not assuming `futureOf` is injective. -/
theorem failed_index_was_locally_unreachable
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    {i : I}
    (habs : ¬ Nonempty (Cap i)) :
    ¬ (Nonempty (Cap i) ∧ J.futureOf i = J.futureOf i) := by
  intro h
  exact habs h.1

/-- Exact future-past coupling theorem.

    If two states were behaviourally identical under every old reachable
    future, and a verifier-required absent capability is freely generated whose
    associated future distinguishes them, then they cease to be behaviourally
    identical under the enlarged reachable future set.

    Thus structural completion can force retroactive refinement of behavioural
    identity without changing the state carrier. -/
theorem generated_future_refines_past_identity
    {X I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (observe : F → X → Bool)
    (L : RequirementLandscape I Cap)
    {i : I} {x y : X}
    (hbefore : EquivalentUnder (reachableBefore (Cap := Cap) J) observe x y)
    (hreq : L.required i)
    (habs : ¬ Nonempty (Cap i))
    (hsep : observe (J.futureOf i) x ≠ observe (J.futureOf i) y) :
    EquivalentUnder (reachableBefore (Cap := Cap) J) observe x y ∧
    ¬ EquivalentUnder (reachableAfter J L) observe x y := by
  constructor
  · exact hbefore
  · intro hafter
    exact hsep (hafter (J.futureOf i)
      (residual_fill_makes_future_reachable J L hreq habs))

/-- Ablation isolates causality.  If the requirement signal is erased and the
    only possible realization of the separating future would have to come from
    an index that is absent in the old capability family, then the generated
    route to that future disappears. -/
theorem erased_requirement_blocks_generated_route
    {I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    {i : I}
    (habs : ¬ Nonempty (Cap i)) :
    ¬ Nonempty
      (completeLandscape
        (erasedLandscape : RequirementLandscape I Cap) i) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact habs ⟨oldh⟩
  | forced hd => exact hd.1

/-- Completion and consequential quotient are therefore not redundant views of
    one operation: completion changes which futures exist; behavioural
    equivalence is recomputed from those futures. -/
theorem completion_can_strictly_refine_consequential_equivalence
    {X I F : Type} {Cap : I → Type}
    (J : FutureInterface I F)
    (observe : F → X → Bool)
    (L : RequirementLandscape I Cap)
    {i : I} {x y : X}
    (hbefore : EquivalentUnder (reachableBefore (Cap := Cap) J) observe x y)
    (hreq : L.required i)
    (habs : ¬ Nonempty (Cap i))
    (hsep : observe (J.futureOf i) x ≠ observe (J.futureOf i) y) :
    ¬ EquivalentUnder (reachableAfter J L) observe x y := by
  exact (generated_future_refines_past_identity J observe L
    hbefore hreq habs hsep).2

/-- Tiny closed witness showing the phase transition is inhabited, not merely
    conditional.  There are two states and one future.  Initially no capability
    exists, so the states are vacuously equivalent.  Requiring the missing
    capability freely creates the future, which separates them. -/
namespace Witness

inductive State where | left | right
inductive Idx where | probe
inductive Fut where | probe

instance : DecidableEq State := by infer_instance

abbrev EmptyCap : Idx → Type := fun _ => Empty

def J : FutureInterface Idx Fut where
  futureOf := fun _ => .probe

def observe : Fut → State → Bool
  | .probe, .left => false
  | .probe, .right => true

def L : RequirementLandscape Idx EmptyCap where
  required := fun _ => True

theorem before_equivalent :
    EquivalentUnder (reachableBefore (Cap := EmptyCap) J)
      observe .left .right := by
  intro f h
  rcases h with ⟨i, hcap, _⟩
  rcases hcap with ⟨hcap⟩
  exact nomatch hcap

theorem capability_absent : ¬ Nonempty (EmptyCap Idx.probe) := by
  intro h
  rcases h with ⟨h⟩
  exact nomatch h

theorem future_separates :
    observe Fut.probe State.left ≠ observe Fut.probe State.right := by
  decide

theorem requirement_present : L.required Idx.probe := trivial

theorem strict_future_past_refinement :
    EquivalentUnder (reachableBefore (Cap := EmptyCap) J)
      observe State.left State.right ∧
    ¬ EquivalentUnder (reachableAfter J L)
      observe State.left State.right := by
  exact generated_future_refines_past_identity J observe L
    before_equivalent requirement_present capability_absent future_separates

end Witness

#check old_future_retained
#check residual_fill_makes_future_reachable
#check generated_future_refines_past_identity
#check completion_can_strictly_refine_consequential_equivalence
#check Witness.strict_future_past_refinement

end ConsequentialCompletionCoupling
