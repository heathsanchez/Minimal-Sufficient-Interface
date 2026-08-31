import FailureForcesCompositionCompletion

namespace FailureForcesCoherenceCompletion

/-- A substrate in which objects, arrows, identities and binary composition
    already exist.  Equations/laws between parallel arrows are a separate,
    proposition-valued layer. -/
structure RawCompositionalSubstrate where
  Obj : Type
  Hom : Obj → Obj → Type
  id : (x : Obj) → Hom x x
  comp : {x y z : Obj} → Hom x y → Hom y z → Hom x z
  Law : {x y : Obj} → Hom x y → Hom x y → Prop

/-- A verifier-certified demand for laws between already-existing parallel
    arrows. -/
structure CertifiedLawDemand (S : RawCompositionalSubstrate) where
  demanded : {x y : S.Obj} → S.Hom x y → S.Hom x y → Prop

/-- The least logical law completion: an equation is available exactly when it
    was already available or is verifier-certified as demanded. -/
def completedLaw
    (S : RawCompositionalSubstrate) (D : CertifiedLawDemand S)
    {x y : S.Obj} (p q : S.Hom x y) : Prop :=
  S.Law p q ∨ D.demanded p q

/-- Completion changes only the law layer.  Objects, arrows, identities and
    composition remain definitionally unchanged. -/
def completeLaws
    (S : RawCompositionalSubstrate) (D : CertifiedLawDemand S) :
    RawCompositionalSubstrate where
  Obj := S.Obj
  Hom := S.Hom
  id := S.id
  comp := S.comp
  Law := completedLaw S D

/-- Every old law survives completion. -/
theorem includeOldLaw
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    {x y : S.Obj} {p q : S.Hom x y} (h : S.Law p q) :
    (completeLaws S D).Law p q := by
  exact Or.inl h

/-- Every certified law demand is satisfied. -/
theorem forcedLaw
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    {x y : S.Obj} {p q : S.Hom x y} (h : D.demanded p q) :
    (completeLaws S D).Law p q := by
  exact Or.inr h

/-- Leastness/universal property: any law predicate containing all old laws and
    all certified demands necessarily contains the completed law predicate. -/
theorem completedLaw_least
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    (R : {x y : S.Obj} → S.Hom x y → S.Hom x y → Prop)
    (hold : ∀ {x y} {p q : S.Hom x y}, S.Law p q → R p q)
    (hforced : ∀ {x y} {p q : S.Hom x y}, D.demanded p q → R p q) :
    ∀ {x y} {p q : S.Hom x y},
      (completeLaws S D).Law p q → R p q := by
  intro x y p q h
  rcases h with holdLaw | forcedDemand
  · exact hold holdLaw
  · exact hforced forcedDemand

/-- Outside both the old law relation and the certified demand, completion does
    not manufacture an unrelated equation. -/
theorem no_new_law_outside_demand
    {S : RawCompositionalSubstrate} {D : CertifiedLawDemand S}
    {x y : S.Obj} {p q : S.Hom x y}
    (hnot : ¬ D.demanded p q)
    (holdNone : ¬ S.Law p q) :
    ¬ (completeLaws S D).Law p q := by
  intro h
  rcases h with oldh | newh
  · exact holdNone oldh
  · exact hnot newh

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
    ¬ S.Law (S.comp (S.comp f g) h) (S.comp f (S.comp g h))

/-- The residual generates exactly the missing associativity-instance demand.
    HEq is used only to compare the selected arrows across the dependent
    endpoint indices of the general demand family. -/
def generatedAssociativityDemand
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    CertifiedLawDemand S where
  demanded := fun p q =>
    HEq p (S.comp (S.comp r.f r.g) r.h) ∧
    HEq q (S.comp r.f (S.comp r.g r.h))

/-- Ablation removes the certified coherence residual. -/
def erasedLawDemand (S : RawCompositionalSubstrate) : CertifiedLawDemand S where
  demanded := fun _ _ => False

theorem associativity_instance_is_generated_demand
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    (generatedAssociativityDemand r).demanded
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) := by
  exact ⟨HEq.rfl, HEq.rfl⟩

theorem failure_exposes_missing_associativity_law
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    ¬ S.Law (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) :=
  r.unrealized

theorem failure_forces_associativity_instance
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    (completeLaws S (generatedAssociativityDemand r)).Law
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) := by
  exact forcedLaw (associativity_instance_is_generated_demand r)

/-- The repair is genuinely law-level: object and arrow carriers are
    definitionally unchanged, while the previously absent associativity witness
    becomes present. -/
theorem failure_forces_genuinely_new_law_without_new_arrows
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    ((completeLaws S (generatedAssociativityDemand r)).Obj = S.Obj) ∧
    ((completeLaws S (generatedAssociativityDemand r)).Hom = S.Hom) ∧
    (¬ S.Law (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h))) ∧
    (completeLaws S (generatedAssociativityDemand r)).Law
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) := by
  exact ⟨rfl, rfl, r.unrealized, failure_forces_associativity_instance r⟩

/-- Erasing the residual blocks exactly the law genesis. -/
theorem erasing_failure_signal_erases_associativity_instance
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    ¬ (completeLaws S (erasedLawDemand S)).Law
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) := by
  apply no_new_law_outside_demand
  · intro h
    exact h
  · exact r.unrealized

/-- Failure-relative universal property specialized to the generated demand. -/
theorem failure_generated_law_completion_is_least
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S)
    (R : {x y : S.Obj} → S.Hom x y → S.Hom x y → Prop)
    (hold : ∀ {x y} {p q : S.Hom x y}, S.Law p q → R p q)
    (hforced : ∀ {x y} {p q : S.Hom x y},
      (generatedAssociativityDemand r).demanded p q → R p q) :
    ∀ {x y} {p q : S.Hom x y},
      (completeLaws S (generatedAssociativityDemand r)).Law p q → R p q := by
  exact completedLaw_least R hold hforced

/-- Core certificate: composition already exists; verified failure forces one
    least/free coherence law between the two existing bracketings; deleting the
    failure signal prevents the law from appearing. -/
theorem verified_failure_forces_associativity_as_minimal_law_completion
    {S : RawCompositionalSubstrate} (r : FailedAssociativity S) :
    (¬ S.Law (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h))) ∧
    (completeLaws S (generatedAssociativityDemand r)).Law
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h)) ∧
    (¬ (completeLaws S (erasedLawDemand S)).Law
      (S.comp (S.comp r.f r.g) r.h)
      (S.comp r.f (S.comp r.g r.h))) := by
  exact ⟨r.unrealized,
    failure_forces_associativity_instance r,
    erasing_failure_signal_erases_associativity_instance r⟩

#check associativity_instance_is_generated_demand
#check failure_exposes_missing_associativity_law
#check failure_forces_associativity_instance
#check failure_forces_genuinely_new_law_without_new_arrows
#check erasing_failure_signal_erases_associativity_instance
#check completedLaw_least
#check failure_generated_law_completion_is_least
#check verified_failure_forces_associativity_as_minimal_law_completion

end FailureForcesCoherenceCompletion
