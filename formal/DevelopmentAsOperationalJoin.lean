namespace DevelopmentAsOperationalJoin

universe u

/-- A quotient-level developmental state records only which operational
    consequences/profiles are currently realizable. -/
abbrev Image (P : Type u) := P → Prop

/-- Consequence-image inclusion. -/
def ImageLe {P : Type u} (I J : Image P) : Prop :=
  ∀ p, I p → J p

/-- Operational join of what is already realizable with what the verifier now
    requires. -/
def join {P : Type u} (I R : Image P) : Image P :=
  fun p => I p ∨ R p

theorem left_le_join {P : Type u} (I R : Image P) :
    ImageLe I (join I R) := by
  intro p hp
  exact Or.inl hp

theorem right_le_join {P : Type u} (I R : Image P) :
    ImageLe R (join I R) := by
  intro p hp
  exact Or.inr hp

/-- Any image containing both the old consequences and every newly required
    consequence also contains their operational join. -/
theorem join_least_upper_bound {P : Type u}
    (I R J : Image P) (hI : ImageLe I J) (hR : ImageLe R J) :
    ImageLe (join I R) J := by
  intro p hp
  rcases hp with hOld | hReq
  · exact hI p hOld
  · exact hR p hReq

/-- The developmental successor is exactly the least admissible operational
    extension satisfying preservation plus the verifier-required family. -/
def AdmissibleSuccessor {P : Type u}
    (I R J : Image P) : Prop :=
  ImageLe I J ∧ ImageLe R J

theorem join_is_least_admissible_successor {P : Type u}
    (I R : Image P) :
    AdmissibleSuccessor I R (join I R) ∧
    (∀ J, AdmissibleSuccessor I R J → ImageLe (join I R) J) := by
  constructor
  · exact ⟨left_le_join I R, right_le_join I R⟩
  · intro J hJ
    exact join_least_upper_bound I R J hJ.1 hJ.2

/-- No developmental change occurs exactly when every currently required
    consequence is already realizable. -/
theorem join_eq_left_iff_required_already_realized {P : Type u}
    (I R : Image P) :
    join I R = I ↔ ImageLe R I := by
  constructor
  · intro h p hp
    have hj : join I R p := Or.inr hp
    rw [h] at hj
    exact hj
  · intro h
    funext p
    apply propext
    constructor
    · intro hp
      rcases hp with hOld | hReq
      · exact hOld
      · exact h p hReq
    · intro hp
      exact Or.inl hp

/-- If some verifier-required consequence is genuinely absent, operational
    development is necessarily strict. -/
theorem missing_requirement_forces_strict_growth {P : Type u}
    (I R : Image P) (hmissing : ¬ ImageLe R I) :
    join I R ≠ I := by
  intro hEq
  exact hmissing ((join_eq_left_iff_required_already_realized I R).mp hEq)

/-- A residual extractor can depend on the current operational state.  The
    developmental operator still has the same universal form: join the current
    image with exactly the consequences required by its present residual. -/
def develop {P : Type u}
    (required : Image P → Image P) (I : Image P) : Image P :=
  join I (required I)

/-- Development is inflationary independently of how residual requirements are
    computed. -/
theorem develop_preserves_current {P : Type u}
    (required : Image P → Image P) (I : Image P) :
    ImageLe I (develop required I) := by
  exact left_le_join I (required I)

/-- The exact fixed-point criterion: a state is developmentally closed iff its
    own verifier-required consequences are already contained in it. -/
theorem develop_fixed_iff_residual_closed {P : Type u}
    (required : Image P → Image P) (I : Image P) :
    develop required I = I ↔ ImageLe (required I) I := by
  exact join_eq_left_iff_required_already_realized I (required I)

/-- Conversely, any genuinely unrealized requirement proves non-terminal
    development. -/
theorem residual_not_contained_implies_not_fixed {P : Type u}
    (required : Image P → Image P) (I : Image P)
    (hmissing : ¬ ImageLe (required I) I) :
    develop required I ≠ I := by
  exact missing_requirement_forces_strict_growth I (required I) hmissing

/-- Main theorem exposed by the preceding identity/composition/coherence and
    hypothesis/candidate-genesis experiments: at the operational quotient,
    verifier-guided development is the least upper bound of current consequence
    and residual-required consequence, and terminality is exactly residual
    containment.

    This does NOT determine a unique raw presentation, nor does it manufacture
    the residual extractor. -/
theorem development_is_operational_join_with_exact_fixed_point_criterion
    {P : Type u} (required : Image P → Image P) (I : Image P) :
    (AdmissibleSuccessor I (required I) (develop required I) ∧
      ∀ J, AdmissibleSuccessor I (required I) J → ImageLe (develop required I) J) ∧
    (develop required I = I ↔ ImageLe (required I) I) := by
  constructor
  · exact join_is_least_admissible_successor I (required I)
  · exact develop_fixed_iff_residual_closed required I

#check left_le_join
#check right_le_join
#check join_least_upper_bound
#check join_is_least_admissible_successor
#check join_eq_left_iff_required_already_realized
#check missing_requirement_forces_strict_growth
#check develop_preserves_current
#check develop_fixed_iff_residual_closed
#check residual_not_contained_implies_not_fixed
#check development_is_operational_join_with_exact_fixed_point_criterion

end DevelopmentAsOperationalJoin
