import IdentityForcedAsMinimalCompletion

namespace FailureForcesCompositionCompletion

open IdentityForcedAsMinimalCompletion

/-- A verifier-certified demand for transport between selected endpoint pairs. -/
structure CertifiedTransportDemand (S : RawDirectedSubstrate) where
  demanded : S.Obj → S.Obj → Prop

/-- Free completion by exactly two kinds of generators: every old transport,
    and one formal transport at each verifier-certified demanded endpoint pair. -/
inductive CompletedTransportHom
    (S : RawDirectedSubstrate) (D : CertifiedTransportDemand S) :
    S.Obj → S.Obj → Type where
  | old {x y} : S.Hom x y → CompletedTransportHom S D x y
  | forced {x y} : D.demanded x y → CompletedTransportHom S D x y

/-- Completion changes no objects. -/
def completeTransport
    (S : RawDirectedSubstrate) (D : CertifiedTransportDemand S) :
    RawDirectedSubstrate where
  Obj := S.Obj
  Hom := CompletedTransportHom S D

/-- Every old transport survives the completion. -/
def includeOld
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj} (h : S.Hom x y) :
    (completeTransport S D).Hom x y :=
  CompletedTransportHom.old h

/-- Every certified transport demand is satisfied. -/
def forcedTransport
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj} (hxy : D.demanded x y) :
    (completeTransport S D).Hom x y :=
  CompletedTransportHom.forced hxy

def satisfyDemand
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj} (hxy : D.demanded x y) :
    Nonempty ((completeTransport S D).Hom x y) :=
  ⟨forcedTransport hxy⟩

/-- Any target family interpreting the old transports and every certified new
    transport receives a canonical interpretation of the completion. -/
def lift
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y}, D.demanded x y → H x y) :
    ∀ {x y}, CompletedTransportHom S D x y → H x y
  | _, _, .old h => oldMap h
  | _, _, .forced hxy => forcedMap hxy

@[simp] theorem lift_old
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y}, D.demanded x y → H x y)
    {x y : S.Obj} (h : S.Hom x y) :
    lift H oldMap forcedMap (CompletedTransportHom.old h) = oldMap h := rfl

@[simp] theorem lift_forced
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y}, D.demanded x y → H x y)
    {x y : S.Obj} (hxy : D.demanded x y) :
    lift H oldMap forcedMap (CompletedTransportHom.forced hxy) =
      forcedMap hxy := rfl

/-- Initiality/leastness: a map out of the completion is uniquely determined
    by its action on old generators and certified new generators. -/
theorem lift_unique
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y}, D.demanded x y → H x y)
    (f : ∀ {x y}, CompletedTransportHom S D x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y),
      f (CompletedTransportHom.old h) = oldMap h)
    (hforced : ∀ {x y} (hxy : D.demanded x y),
      f (CompletedTransportHom.forced hxy) = forcedMap hxy) :
    ∀ {x y} (h : CompletedTransportHom S D x y),
      f h = lift H oldMap forcedMap h := by
  intro x y h
  cases h with
  | old oldh => exact hold oldh
  | forced hxy => exact hforced hxy

/-- If neither the old substrate nor the certified demand supports an endpoint
    pair, the completion does not invent transport there. -/
theorem no_new_transport_outside_demand
    {S : RawDirectedSubstrate} {D : CertifiedTransportDemand S}
    {x y : S.Obj}
    (hnot : ¬ D.demanded x y)
    (holdNone : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty ((completeTransport S D).Hom x y) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact holdNone ⟨oldh⟩
  | forced hxy => exact hnot hxy

/-- A verifier-certified compositional failure: two consecutive transports are
    present, but the transport required to realize their composite is absent. -/
structure FailedComposition (S : RawDirectedSubstrate) where
  source : S.Obj
  middle : S.Obj
  target : S.Obj
  first : S.Hom source middle
  second : S.Hom middle target
  unrealized : ¬ Nonempty (S.Hom source target)

/-- The failure itself generates exactly the missing endpoint demand. -/
def generatedCompositeDemand
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    CertifiedTransportDemand S where
  demanded := fun x y => x = f.source ∧ y = f.target

/-- Ablation: erase the verifier-certified failure signal. -/
def erasedDemand (S : RawDirectedSubstrate) : CertifiedTransportDemand S where
  demanded := fun _ _ => False

theorem composite_is_generated_demand
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    (generatedCompositeDemand f).demanded f.source f.target := by
  exact ⟨rfl, rfl⟩

theorem failure_exposes_missing_composite
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    ¬ Nonempty (S.Hom f.source f.target) :=
  f.unrealized

theorem failure_forces_composite
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    Nonempty
      ((completeTransport S (generatedCompositeDemand f)).Hom
        f.source f.target) :=
  satisfyDemand (composite_is_generated_demand f)

theorem failure_forces_genuinely_new_composite
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    (¬ Nonempty (S.Hom f.source f.target)) ∧
    Nonempty
      ((completeTransport S (generatedCompositeDemand f)).Hom
        f.source f.target) := by
  exact ⟨f.unrealized, failure_forces_composite f⟩

/-- The two transports whose composition failed remain available after repair. -/
theorem failed_composition_inputs_are_retained
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    Nonempty
      ((completeTransport S (generatedCompositeDemand f)).Hom
        f.source f.middle) ∧
    Nonempty
      ((completeTransport S (generatedCompositeDemand f)).Hom
        f.middle f.target) := by
  exact ⟨⟨includeOld f.first⟩, ⟨includeOld f.second⟩⟩

/-- The local repair adds no unrelated missing endpoint transport. -/
theorem failure_repair_adds_no_unrelated_transport
    {S : RawDirectedSubstrate} (f : FailedComposition S)
    {x y : S.Obj}
    (hunrelated : x ≠ f.source ∨ y ≠ f.target)
    (holdNone : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty
      ((completeTransport S (generatedCompositeDemand f)).Hom x y) := by
  apply no_new_transport_outside_demand ?_ holdNone
  intro hxy
  rcases hxy with ⟨hx, hy⟩
  rcases hunrelated with hsource | htarget
  · exact hsource hx
  · exact htarget hy

/-- Removing the certified failure signal removes the generated composite. -/
theorem erasing_failure_signal_erases_composite
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    ¬ Nonempty
      ((completeTransport S (erasedDemand S)).Hom
        f.source f.target) := by
  apply no_new_transport_outside_demand ?_ f.unrealized
  intro h
  exact h

/-- Failure-relative universal property: any interpretation of the old
    transports and the one demanded composite uniquely interprets the repair. -/
theorem failure_generated_lift_unique
    {S : RawDirectedSubstrate} (f : FailedComposition S)
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (forcedMap : ∀ {x y},
      (generatedCompositeDemand f).demanded x y → H x y)
    (g : ∀ {x y},
      CompletedTransportHom S (generatedCompositeDemand f) x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y),
      g (CompletedTransportHom.old h) = oldMap h)
    (hforced : ∀ {x y}
      (hxy : (generatedCompositeDemand f).demanded x y),
      g (CompletedTransportHom.forced hxy) = forcedMap hxy) :
    ∀ {x y}
      (h : CompletedTransportHom S (generatedCompositeDemand f) x y),
      g h = lift H oldMap forcedMap h := by
  exact lift_unique H oldMap forcedMap g hold hforced

/-- Core certificate: a verifier-certified failed composition forces exactly a
    genuinely new composite transport, while deleting the failure signal
    prevents it. -/
theorem verified_failure_forces_composite_as_minimal_completion
    {S : RawDirectedSubstrate} (f : FailedComposition S) :
    ((¬ Nonempty (S.Hom f.source f.target)) ∧
      Nonempty
        ((completeTransport S (generatedCompositeDemand f)).Hom
          f.source f.target)) ∧
    (¬ Nonempty
      ((completeTransport S (erasedDemand S)).Hom
        f.source f.target)) := by
  exact ⟨failure_forces_genuinely_new_composite f,
    erasing_failure_signal_erases_composite f⟩

#check composite_is_generated_demand
#check failure_exposes_missing_composite
#check failure_forces_composite
#check failure_forces_genuinely_new_composite
#check failed_composition_inputs_are_retained
#check failure_repair_adds_no_unrelated_transport
#check erasing_failure_signal_erases_composite
#check failure_generated_lift_unique
#check verified_failure_forces_composite_as_minimal_completion

end FailureForcesCompositionCompletion
