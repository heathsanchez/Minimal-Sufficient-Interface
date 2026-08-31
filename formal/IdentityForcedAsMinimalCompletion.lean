import Std

namespace IdentityForcedAsMinimalCompletion

structure RawDirectedSubstrate where
  Obj : Type
  Hom : Obj → Obj → Type

structure CertifiedIdentityDemand (S : RawDirectedSubstrate) where
  demanded : S.Obj → Prop

def CompletedHom (S : RawDirectedSubstrate) (D : CertifiedIdentityDemand S)
    (x y : S.Obj) : Type :=
  Sum (S.Hom x y) (PLift (x = y ∧ D.demanded x))

def complete (S : RawDirectedSubstrate) (D : CertifiedIdentityDemand S) : RawDirectedSubstrate where
  Obj := S.Obj
  Hom := CompletedHom S D

def includeOld {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x y : S.Obj} (h : S.Hom x y) : (complete S D).Hom x y :=
  Sum.inl h

def forcedIdentity {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x : S.Obj} (hx : D.demanded x) : (complete S D).Hom x x :=
  Sum.inr ⟨⟨rfl, hx⟩⟩

def satisfyDemand {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x : S.Obj} (hx : D.demanded x) : Nonempty ((complete S D).Hom x x) :=
  ⟨forcedIdentity hx⟩

def lift
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    {x y : S.Obj} : CompletedHom S D x y → H x y
  | Sum.inl h => oldMap h
  | Sum.inr newh => by
      rcases newh with ⟨hxy, hx⟩
      cases hxy
      exact idMap hx

@[simp] theorem lift_old
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    {x y : S.Obj} (h : S.Hom x y) :
    lift H oldMap idMap (Sum.inl h) = oldMap h := rfl

@[simp] theorem lift_forcedIdentity
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    {x : S.Obj} (hx : D.demanded x) :
    lift H oldMap idMap (forcedIdentity hx) = idMap hx := by
  unfold forcedIdentity lift
  apply congrArg idMap
  exact Subsingleton.elim _ _

theorem lift_unique
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    (H : S.Obj → S.Obj → Type)
    (oldMap : ∀ {x y}, S.Hom x y → H x y)
    (idMap : ∀ {x}, D.demanded x → H x x)
    (f : ∀ {x y}, CompletedHom S D x y → H x y)
    (hold : ∀ {x y} (h : S.Hom x y), f (Sum.inl h) = oldMap h)
    (hid : ∀ {x} (hx : D.demanded x), f (forcedIdentity hx) = idMap hx) :
    ∀ {x y} (h : CompletedHom S D x y), f h = lift H oldMap idMap h := by
  intro x y h
  cases h with
  | inl oldh => exact hold oldh
  | inr newh =>
      rcases newh with ⟨hxy, hx⟩
      cases hxy
      calc
        f (Sum.inr ⟨⟨rfl, hx⟩⟩) = idMap hx := by
          simpa [forcedIdentity] using hid hx
        _ = lift H oldMap idMap (Sum.inr ⟨⟨rfl, hx⟩⟩) := by
          symm
          exact lift_forcedIdentity H oldMap idMap hx

theorem no_new_transport_between_distinct
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x y : S.Obj} (hne : x ≠ y)
    (holdNone : ¬ Nonempty (S.Hom x y)) :
    ¬ Nonempty ((complete S D).Hom x y) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | inl oldh => exact holdNone ⟨oldh⟩
  | inr newh => exact hne newh.down.1

theorem no_uncertified_self_transport_from_nothing
    {S : RawDirectedSubstrate} {D : CertifiedIdentityDemand S}
    {x : S.Obj}
    (hnot : ¬ D.demanded x)
    (holdNone : ¬ Nonempty (S.Hom x x)) :
    ¬ Nonempty ((complete S D).Hom x x) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | inl oldh => exact holdNone ⟨oldh⟩
  | inr newh => exact hnot newh.down.2

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
#check lift_unique
#check no_new_transport_between_distinct
#check no_uncertified_self_transport_from_nothing
#check demanded_identity_is_genuinely_adjoined
#check identity_as_minimal_forced_completion

end IdentityForcedAsMinimalCompletion
