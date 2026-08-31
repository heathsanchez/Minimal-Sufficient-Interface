namespace VerifiedResidualInducesCanonicalBehavioralCompletion

universe u

/-- At the quotient level a developmental state is only the set of operational
    profiles currently realizable.  No raw candidate carrier or syntax is
    retained in the theorem. -/
abbrev BehavioralImage (P : Type u) := P → Prop

/-- Operational inclusion is the only order needed for developmental repair. -/
def ImageLe {P : Type u} (I J : BehavioralImage P) : Prop :=
  ∀ p, I p → J p

/-- A verified residual contributes one required operational profile.  A repair
    is admissible iff it preserves every previously realizable consequence and
    realizes that required profile.  There is deliberately no no-extra axiom. -/
def AdmissibleRepair {P : Type u}
    (old : BehavioralImage P) (target : P) (next : BehavioralImage P) : Prop :=
  ImageLe old next ∧ next target

/-- Canonical completion at the operational quotient: retain exactly the old
    image and adjoin the residual-required profile. -/
def complete {P : Type u}
    (old : BehavioralImage P) (target : P) : BehavioralImage P :=
  fun p => old p ∨ p = target

theorem completion_preserves_old {P : Type u}
    (old : BehavioralImage P) (target : P) :
    ImageLe old (complete old target) := by
  intro p hp
  exact Or.inl hp

theorem completion_realizes_target {P : Type u}
    (old : BehavioralImage P) (target : P) :
    complete old target target := by
  exact Or.inr rfl

theorem completion_is_admissible {P : Type u}
    (old : BehavioralImage P) (target : P) :
    AdmissibleRepair old target (complete old target) := by
  exact ⟨completion_preserves_old old target, completion_realizes_target old target⟩

/-- Core theorem: the quotient-level completion lies below every admissible
    repair.  Thus exactness is a theorem of leastness, not a supplied repair
    criterion. -/
theorem completion_is_least {P : Type u}
    (old : BehavioralImage P) (target : P)
    (next : BehavioralImage P)
    (hnext : AdmissibleRepair old target next) :
    ImageLe (complete old target) next := by
  intro p hp
  rcases hp with hold | htarget
  · exact hnext.1 p hold
  · simpa [htarget] using hnext.2

/-- Being least is defined entirely in the behavioral preorder. -/
def IsLeastRepair {P : Type u}
    (old : BehavioralImage P) (target : P) (next : BehavioralImage P) : Prop :=
  AdmissibleRepair old target next ∧
  ∀ other, AdmissibleRepair old target other → ImageLe next other

/-- The canonical operational completion is itself a least repair. -/
theorem canonical_completion_is_least {P : Type u}
    (old : BehavioralImage P) (target : P) :
    IsLeastRepair old target (complete old target) := by
  constructor
  · exact completion_is_admissible old target
  · intro other hother
    exact completion_is_least old target other hother

/-- Any least repair has exactly the same operational image as the canonical
    completion.  Raw presentations may differ; consequence-level development
    is canonical. -/
theorem any_least_repair_equals_canonical {P : Type u}
    (old : BehavioralImage P) (target : P)
    (next : BehavioralImage P)
    (hnext : IsLeastRepair old target next) :
    next = complete old target := by
  funext p
  apply propext
  constructor
  · exact hnext.2 (complete old target) (completion_is_admissible old target) p
  · exact completion_is_least old target next hnext.1 p

/-- Consequently every least repair contains no operational behavior beyond
    what was already realizable or what the residual itself requires. -/
theorem no_unrelated_behavior_follows_from_leastness {P : Type u}
    (old : BehavioralImage P) (target : P)
    (next : BehavioralImage P)
    (hnext : IsLeastRepair old target next) :
    ∀ p, next p ↔ old p ∨ p = target := by
  intro p
  have heq := any_least_repair_equals_canonical old target next hnext
  rw [heq]
  rfl

/-- Main representation-independent theorem.  A verified requirement determines
    a unique least developmental successor in the operational quotient, while
    making no claim that a unique raw syntax realizes that successor.

    Remaining scaffold: the operational profile universe P and the residual's
    target profile are supplied. -/
theorem verified_residual_induces_canonical_behavioral_completion
    {P : Type u} (old : BehavioralImage P) (target : P) :
    IsLeastRepair old target (complete old target) ∧
    (∀ next, IsLeastRepair old target next → next = complete old target) := by
  constructor
  · exact canonical_completion_is_least old target
  · intro next hnext
    exact any_least_repair_equals_canonical old target next hnext

#check completion_preserves_old
#check completion_realizes_target
#check completion_is_least
#check canonical_completion_is_least
#check any_least_repair_equals_canonical
#check no_unrelated_behavior_follows_from_leastness
#check verified_residual_induces_canonical_behavioral_completion

end VerifiedResidualInducesCanonicalBehavioralCompletion
