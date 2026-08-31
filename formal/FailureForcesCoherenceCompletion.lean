import FailureForcesCompositionCompletion

namespace FailureForcesCoherenceCompletion

/-- A substrate in which objects, arrows, identities and binary composition
    already exist, while equations/laws between parallel composites are tracked
    separately as explicit evidence. -/
structure RawCompositionalSubstrate where
  Obj : Type
  Hom : Obj → Obj → Type
  id : (x : Obj) → Hom x x
  comp : {x y z : Obj} → Hom x y → Hom y z → Hom x z
  Law : {x y : Obj} → Hom x y → Hom x y → Type

/-- A verifier-certified demand for one law between two already-existing
    parallel composites. -/
structure CertifiedLawDemand (S : RawCompositionalSubstrate) where
  demanded : {x y : S.Obj} → S.Hom x y → S.Hom x y → Prop

/-- Free law completion: retain every old law witness and add one formal witness
    exactly where the verifier-certified demand says a law is required.  No
    objects, arrows, identities or composites are changed. -/
inductive CompletedLaw
    (S : RawCompositionalSubstrate) (D : CertifiedLawDemand S) :
    {x y : S.Obj} → S.Hom x y → S.Hom x y → Type where
  | old {x y p q} : S.Law p q → CompletedLaw S D p q
  | forced {x y p q} : D.demanded p q → CompletedLaw S D p q

/-- Completion changes only the law layer. -/
def completeLaws
    (S : RawCompositionalSubstrate) (D : CertifiedLawDemand S) :
    RawCompositionalSubstrate where
  Obj := S.Obj
  Hom := S.Hom
  id := S.id
  comp := S.comp
  Law := CompletedLaw S D

/-- Every old law survives completion. -/
def includeOldLaw
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    {x y : S.Obj} {p q : S.Hom x y} (h : S.Law p q) :
    (completeLaws S D).Law p q :=
  CompletedLaw.old h

/-- Every certified law demand is satisfied. -/
def forcedLaw
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    {x y : S.Obj} {p q : S.Hom x y} (h : D.demanded p q) :
    (completeLaws S D).Law p q :=
  CompletedLaw.forced h

/-- Any target law family interpreting old law witnesses and certified new law
    witnesses receives a canonical interpretation of the completion. -/
def liftLaw
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    (L : {x y : S.Obj} → S.Hom x y → S.Hom x y → Type)
    (oldMap : ∀ {x y} {p q : S.Hom x y}, S.Law p q → L p q)
    (forcedMap : ∀ {x y} {p q : S.Hom x y}, D.demanded p q → L p q) :
    ∀ {x y} {p q : S.Hom x y}, CompletedLaw S D p q → L p q
  | _, _, _, _, .old h => oldMap h
  | _, _, _, _, .forced h => forcedMap h

/-- Initiality/leastness at the law layer. -/
theorem liftLaw_unique
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    (L : {x y : S.Obj} → S.Hom x y → S.Hom x y → Type)
    (oldMap : ∀ {x y} {p q : S.Hom x y}, S.Law p q → L p q)
    (forcedMap : ∀ {x y} {p q : S.Hom x y}, D.demanded p q → L p q)
    (f : ∀ {x y} {p q : S.Hom x y}, CompletedLaw S D p q → L p q)
    (hold : ∀ {x y} {p q : S.Hom x y} (h : S.Law p q),
      f (CompletedLaw.old h) = oldMap h)
    (hforced : ∀ {x y} {p q : S.Hom x y} (h : D.demanded p q),
      f (CompletedLaw.forced h) = forcedMap h) :
    ∀ {x y} {p q : S.Hom x y} (h : CompletedLaw S D p q),
      f h = liftLaw L oldMap forcedMap h := by
  intro x y p q h
  cases h with
  | old oldh => exact hold oldh
  | forced newh => exact hforced newh

/-- Outside both the old law relation and the certified demand, completion does
    not manufacture an unrelated equation. -/
theorem no_new_law_outside_demand
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    {x y : S.Obj} {p q : S.Hom x y}
    (hnot : ¬ D.demanded p q)
    (holdNone : ¬ Nonempty (S.Law p q)) :
    ¬ Nonempty ((completeLaws S D).Law p q) := by
  intro h
  rcases h with ⟨h⟩
  cases h with
  | old oldh => exact holdNone ⟨oldh⟩
  | forced newh => exact hnot newh

/-- A verifier-certified coherence failure can exist only after composition is
    already available: both bracketed threefold composites are existing arrows,
    but the current law layer cannot identify them. -/
structure FailedAssociativity (S : RawCompositionalSubstrate) where
  a : S.Obj
  b : S.Obj
  c : S.Obj
  d : S.Obj
  f : S.Hom a b
  g : S.Hom b c
  h : S.Hom c d
  unrealized :
    ¬ Nonempty
      (S.Law (S.comp (S.comp f g) h) (S.comp f (S.comp g h)))

/-- The residual generates exactly the missing associativity-instance demand. -/
def generatedAssociativityDemand
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    CertifiedLawDemand S where
  demanded := fun p q =>
    p = S.comp (S.comp r.f r.g) r.h ∧
    q = S.comp r.f (S.comp r.g r.h)

/-- Ablation removes the certified coherence residual. -/
def erasedLawDemand (S : RawCompositionalSubstrate) : CertifiedLawDemand S where
  demanded := fun _ _ => False

theorem associativity_instance_is_generated_demand
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    (generatedAssociativityDemand r).demanded
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) := by
  exact ⟨rfl, rfl⟩

theorem failure_exposes_missing_associativity_law
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    ¬ Nonempty
      (S.Law (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h))) :=
  r.unrealized

theorem failure_forces_associativity_instance
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    Nonempty
      ((completeLaws S (generatedAssociativityDemand r)).Law
        (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h))) := by
  exact ⟨forcedLaw (associativity_instance_is_generated_demand r)⟩

/-- The repair is genuinely law-level: object and arrow carriers are definitionally
    unchanged, while the previously absent associativity witness becomes present. -/
theorem failure_forces_genuinely_new_law_without_new_arrows
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    ((completeLaws S (generatedAssociativityDemand r)).Obj = S.Obj) ∧
    ((completeLaws S (generatedAssociativityDemand r)).Hom = S.Hom) ∧
    (¬ Nonempty
      (S.Law (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h)))) ∧
    Nonempty
      ((completeLaws S (generatedAssociativityDemand r)).Law
        (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h))) := by
  exact ⟨rfl, rfl, r.unrealized, failure_forces_associativity_instance r⟩

/-- Erasing the residual blocks exactly the law genesis. -/
theorem erasing_failure_signal_erases_associativity_instance
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    ¬ Nonempty
      ((completeLaws S (erasedLawDemand S)).Law
        (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h))) := by
  apply no_new_law_outside_demand
  · intro h
    exact h
  · exact r.unrealized

/-- Core certificate: composition already exists; verified failure forces one
    least/free coherence witness between the two existing bracketings; deleting
    the failure signal prevents the law from appearing. -/
theorem verified_failure_forces_associativity_as_minimal_law_completion
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    (¬ Nonempty
      (S.Law (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h)))) ∧
    Nonempty
      ((completeLaws S (generatedAssociativityDemand r)).Law
        (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h))) ∧
    (¬ Nonempty
      ((completeLaws S (erasedLawDemand S)).Law
        (S.comp (S.comp r.f r.g) r.h)
        (S.comp r.f (S.comp r.g r.h)))) := by
  exact ⟨r.unrealized,
    failure_forces_associativity_instance r,
    erasing_failure_signal_erases_associativity_instance r⟩

#check associativity_instance_is_generated_demand
#check failure_exposes_missing_associativity_law
#check failure_forces_associativity_instance
#check failure_forces_genuinely_new_law_without_new_arrows
#check erasing_failure_signal_erases_associativity_instance
#check liftLaw_unique
#check verified_failure_forces_associativity_as_minimal_law_completion

end FailureForcesCoherenceCompletion
