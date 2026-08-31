import IdentityForcedAsMinimalCompletion

namespace FailureForcesIdentityCompletion

open IdentityForcedAsMinimalCompletion

/-- A verifier-certified continuation failure.  The task asked for transport from
    `start` to `finish`, the verifier certifies that the task returns to the same
    object, and the old substrate cannot realize it.  No identity demand is
    supplied separately. -/
structure FailedContinuation (S : RawDirectedSubstrate) where
  start : S.Obj
  finish : S.Obj
  returns : finish = start
  unrealized : ¬ Nonempty (S.Hom start finish)

/-- The failed continuation itself generates the demand: the unique object at
    which self-transport is now required is its start/return point. -/
def generatedDemand {S : RawDirectedSubstrate}
    (f : FailedContinuation S) : CertifiedIdentityDemand S where
  demanded := fun x => x = f.start

/-- The failed task's start point is certified by the generated demand. -/
theorem start_is_generated_demand
    {S : RawDirectedSubstrate} (f : FailedContinuation S) :
    (generatedDemand f).demanded f.start := rfl

/-- Before repair, the failed closed continuation has no self-transport. -/
theorem failure_exposes_missing_self_transport
    {S : RawDirectedSubstrate} (f : FailedContinuation S) :
    ¬ Nonempty (S.Hom f.start f.start) := by
  intro h
  apply f.unrealized
  rw [f.returns]
  exact h

/-- Failure alone, through `generatedDemand`, forces a new self-transport in the
    free completion.  There is no `CertifiedIdentityDemand` argument here. -/
theorem failure_forces_self_transport
    {S : RawDirectedSubstrate} (f : FailedContinuation S) :
    Nonempty ((complete S (generatedDemand f)).Hom f.start f.start) := by
  exact satisfyDemand (start_is_generated_demand f)

/-- The forced transport is genuinely new: it did not exist in the old
    substrate and does exist after consequence-generated completion. -/
theorem failure_forces_genuinely_new_transport
    {S : RawDirectedSubstrate} (f : FailedContinuation S) :
    (¬ Nonempty (S.Hom f.start f.start)) ∧
      Nonempty ((complete S (generatedDemand f)).Hom f.start f.start) := by
  exact ⟨failure_exposes_missing_self_transport f,
    failure_forces_self_transport f⟩

/-- The generated repair is exact: it creates no transport between distinct
    endpoints that was absent before. -/
theorem failure_repair_adds_no_unrelated_transport
    {S : RawDirectedSubstrate} (f : FailedContinuation S)
    {x y : S.Obj} (hne : x ≠ y)
    (holdNone : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty ((complete S (generatedDemand f)).Hom x y) := by
  exact no_new_transport_between_distinct hne holdNone

/-- Nor can this failure manufacture self-transport at a different object. -/
theorem failure_repair_adds_no_other_self_transport
    {S : RawDirectedSubstrate} (f : FailedContinuation S)
    {x : S.Obj} (hx : x ≠ f.start)
    (holdNone : ¬ Nonempty (S.Hom x x)) :
    ¬ Nonempty ((complete S (generatedDemand f)).Hom x x) := by
  apply no_uncertified_self_transport_from_nothing
  · intro h
    exact hx h
  · exact holdNone

/-- Ablation: if the failure-to-demand link is erased, the same empty old
    self-transport remains empty after completion. -/
def erasedDemand {S : RawDirectedSubstrate} : CertifiedIdentityDemand S where
  demanded := fun _ => False

theorem erasing_failure_signal_erases_identity_genesis
    {S : RawDirectedSubstrate} (f : FailedContinuation S) :
    ¬ Nonempty ((complete S erasedDemand).Hom f.start f.start) := by
  apply no_uncertified_self_transport_from_nothing
  · simp [erasedDemand]
  · exact failure_exposes_missing_self_transport f

/-- Initiality survives the whole failure-generated path: any interpretation of
    the old transports plus the single generator forced by the failure receives
    the canonical lift, uniquely on every completed transport. -/
theorem failure_generated_lift_unique
    {S : RawDirectedSubstrate} (f : FailedContinuation S)
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, (generatedDemand f).demanded x → H x x)
    (g : ∀ {x y}, CompletedHom S (generatedDemand f) x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y),
      g (CompletedHom.old h) = oldMap h)
    (hid : ∀ {x} (hx : (generatedDemand f).demanded x),
      g (CompletedHom.forcedId hx) = idMap hx) :
    ∀ {x y} (h : CompletedHom S (generatedDemand f) x y),
      g h = lift H oldMap idMap h := by
  exact lift_unique H oldMap idMap g hold hid

/-- End-to-end criterion.  A verifier-certified failed closed continuation,
    with no separately supplied identity predicate, determines a least/free
    repair that creates exactly the required new self-transport; erasing the
    failure signal prevents that genesis. -/
theorem verified_failure_forces_identity_as_minimal_completion
    {S : RawDirectedSubstrate} (f : FailedContinuation S) :
    ((¬ Nonempty (S.Hom f.start f.start)) ∧
      Nonempty ((complete S (generatedDemand f)).Hom f.start f.start)) ∧
    (¬ Nonempty ((complete S erasedDemand).Hom f.start f.start)) := by
  exact ⟨failure_forces_genuinely_new_transport f,
    erasing_failure_signal_erases_identity_genesis f⟩

#check start_is_generated_demand
#check failure_exposes_missing_self_transport
#check failure_forces_self_transport
#check failure_forces_genuinely_new_transport
#check failure_repair_adds_no_unrelated_transport
#check failure_repair_adds_no_other_self_transport
#check erasing_failure_signal_erases_identity_genesis
#check failure_generated_lift_unique
#check verified_failure_forces_identity_as_minimal_completion

end FailureForcesIdentityCompletion
