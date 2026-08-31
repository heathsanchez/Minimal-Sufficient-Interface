import Std

namespace IdentityForcedAsMinimalCompletion

/-- Rock-bottom substrate: objects and raw directed transport only. -/
structure RawDirectedSubstrate where
  Obj : Type
  Hom : Obj → Obj → Type

/-- A verifier-certified requirement that selected objects must support self-transport. -/
structure CertifiedIdentityDemand (S : RawDirectedSubstrate) where
  demanded : S.Obj → Prop

/-- Free completion by exactly two kinds of generators: every old transport, and one
    formal self-transport constructor at each certified demanded object. -/
inductive CompletedHom (S : RawDirectedSubstrate) (D : CertifiedIdentityDemand S) :
    S.Obj → S.Obj → Type where
  | old {x y} : S.Hom x y → CompletedHom S D x y
  | forcedId {x} : D.demanded x → CompletedHom S D x x

/-- Completion changes no objects. -/
def complete (S : RawDirectedSubstrate) (D : CertifiedIdentityDemand S) : RawDirectedSubstrate where
  Obj := S.Obj
  Hom := CompletedHom S D

/-- Every old capability is retained. -/
def includeOld {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x y : S.Obj} (h : S.Hom x y) : (complete S D).Hom x y :=
  CompletedHom.old h

/-- A certified demand generates a self-transport. -/
def forcedIdentity {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x : S.Obj} (hx : D.demanded x) : (complete S D).Hom x x :=
  CompletedHom.forcedId hx

/-- Every certified identity demand is satisfied after completion. -/
def satisfyDemand {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x : S.Obj} (hx : D.demanded x) : Nonempty ((complete S D).Hom x x) :=
  ⟨forcedIdentity hx⟩

/-- Any target family that interprets the old transports and the demanded identities
    receives a canonical interpretation of every generated completed transport. -/
def lift
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x) :
    ∀ {x y}, CompletedHom S D x y → H x y
  | _, _, .old h => oldMap h
  | _, _, .forcedId hx => idMap hx

@[simp] theorem lift_old
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    {x y : S.Obj} (h : S.Hom x y) :
    lift H oldMap idMap (CompletedHom.old h) = oldMap h := rfl

@[simp] theorem lift_forcedId
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    {x : S.Obj} (hx : D.demanded x) :
    lift H oldMap idMap (CompletedHom.forcedId hx) = idMap hx := rfl

/-- Initiality/leastness: a map out of the completion is uniquely determined by its
    action on the old generators and certified identity generators. -/
theorem lift_unique
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    (f : ∀ {x y}, CompletedHom S D x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y), f (CompletedHom.old h) = oldMap h)
    (hid : ∀ {x} (hx : D.demanded x), f (CompletedHom.forcedId hx) = idMap hx) :
    ∀ {x y} (h : CompletedHom S D x y), f h = lift H oldMap idMap h := by
  intro x y h
  cases h with
  | old oldh => exact hold oldh
  | forcedId hx => exact hid hx

/-- Completion invents no transport between distinct endpoints. -/
theorem no_new_transport_between_distinct
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x y : S.Obj} (hne : x ≠ y)
    (holdNone : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty ((complete S D).Hom x y) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact holdNone ⟨oldh⟩
  | forcedId hx => exact hne rfl

/-- At an uncertified point, completion adds no self-transport. -/
theorem no_uncertified_self_transport_from_nothing
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x : S.Obj}
    (hnot : ¬ D.demanded x)
    (holdNone : ¬ Nonempty (S.Hom x x)) :
    ¬ Nonempty ((complete S D).Hom x x) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact holdNone ⟨oldh⟩
  | forcedId hx => exact hnot hx

/-- Concrete witness that the required identity is genuinely new, not merely recovered. -/
def emptySelf : RawDirectedSubstrate where
  Obj := Unit
  Hom := fun _ _ => Empty

def demandUnit : CertifiedIdentityDemand emptySelf where
  demanded := fun _ => True

theorem demanded_identity_is_genuinely_adjoined :
    (¬ Nonempty (emptySelf.Hom () ())) ∧
    Nonempty ((complete emptySelf demandUnit).Hom () ()) := by
  constructor
  · intro h
    rcases h with ⟨h⟩
    exact Empty.elim h
  · exact satisfyDemand (D := demandUnit) trivial

/-- Core criterion: the certified demand is met and the extension creates no unrelated
    directed transport. -/
theorem identity_as_minimal_forced_completion :
    (∀ (S : RawDirectedSubstrate) (D : CertifiedIdentityDemand S)
        (x : S.Obj), D.demanded x → Nonempty ((complete S D).Hom x x)) ∧
    (∀ (S : RawDirectedSubstrate) (D : CertifiedIdentityDemand S)
        (x y : S.Obj), x ≠ y → ¬ Nonempty (S.Hom x y) →
          ¬ Nonempty ((complete S D).Hom x y)) := by
  constructor
  · intro S D x hx
    exact satisfyDemand hx
  · intro S D x y hne holdNone
    exact no_new_transport_between_distinct hne holdNone

#check includeOld
#check forcedIdentity
#check satisfyDemand
#check lift_old
#check lift_forcedId
#check lift_unique
#check no_new_transport_between_distinct
#check no_uncertified_self_transport_from_nothing
#check demanded_identity_is_genuinely_adjoined
#check identity_as_minimal_forced_completion

end IdentityForcedAsMinimalCompletion
