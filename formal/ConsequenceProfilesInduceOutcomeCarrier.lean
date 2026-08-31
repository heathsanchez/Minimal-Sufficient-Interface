namespace ConsequenceProfilesInduceOutcomeCarrier

/-- A family of downstream verifier contexts observing raw outcomes. -/
structure ObservationFamily (ι β : Type) where
  observe : ι → β → Bool

/-- The full consequence profile of one raw outcome across the currently
    admitted downstream contexts. -/
def Profile {ι β : Type} (F : ObservationFamily ι β) (b : β) : ι → Bool :=
  fun i => F.observe i b

/-- Which consequence profiles are actually realized by some raw outcome. -/
def ProfileImage {ι β : Type} (F : ObservationFamily ι β) : (ι → Bool) → Prop :=
  fun p => ∃ b : β, Profile F b = p

/-- The retained outcome carrier is generated from realized consequence
    profiles.  It contains no raw-outcome field. -/
def InducedOutcomeCarrier {ι β : Type} (F : ObservationFamily ι β) :=
  {p : ι → Bool // ProfileImage F p}

/-- Canonical projection of a raw outcome into the consequence-generated
    operational outcome carrier. -/
def induceOutcome {ι β : Type} (F : ObservationFamily ι β) (b : β) :
    InducedOutcomeCarrier F :=
  ⟨Profile F b, ⟨b, rfl⟩⟩

/-- Every downstream consequence can be recovered directly from an induced
    outcome, without retaining the hidden raw outcome type. -/
def inducedObservation {ι β : Type} {F : ObservationFamily ι β}
    (i : ι) (q : InducedOutcomeCarrier F) : Bool :=
  q.1 i

theorem induced_outcome_sufficient_for_all_consequences {ι β : Type}
    (F : ObservationFamily ι β) (i : ι) (b : β) :
    inducedObservation i (induceOutcome F b) = F.observe i b := by
  rfl

/-- No realized operational outcome is lost by replacing the hidden raw outcome
    domain with its consequence-profile image. -/
theorem induce_outcome_is_surjective {ι β : Type} (F : ObservationFamily ι β) :
    ∀ q : InducedOutcomeCarrier F, ∃ b : β, induceOutcome F b = q := by
  intro q
  rcases q.2 with ⟨b, hb⟩
  refine ⟨b, ?_⟩
  apply Subtype.ext
  exact hb

/-- Operational identity of raw outcomes is exactly equality of their current
    downstream consequence profiles. -/
theorem induced_outcome_eq_iff_profile_eq {ι β : Type}
    (F : ObservationFamily ι β) (a b : β) :
    induceOutcome F a = induceOutcome F b ↔ Profile F a = Profile F b := by
  constructor
  · intro h
    exact congrArg Subtype.val h
  · intro h
    apply Subtype.ext
    exact h

/-- Old consequence family: every context is blind to the distinction between
    the two raw Bool outcomes. -/
def oldFamily : ObservationFamily Bool Bool where
  observe := fun _ _ => false

/-- Refined consequence family: one admitted context exposes the distinction. -/
def refinedFamily : ObservationFamily Bool Bool where
  observe := fun i b => if i then b else false

/-- The old consequence profiles identify false and true. -/
theorem old_consequence_collapses_outcomes :
    induceOutcome oldFamily false = induceOutcome oldFamily true := by
  apply (induced_outcome_eq_iff_profile_eq oldFamily false true).2
  funext i
  cases i <;> rfl

/-- The richer consequence profile splits exactly the raw outcomes that were
    previously operationally identical. -/
theorem new_consequence_splits_old_outcome_class :
    induceOutcome refinedFamily false ≠ induceOutcome refinedFamily true := by
  intro h
  have hp : Profile refinedFamily false = Profile refinedFamily true :=
    (induced_outcome_eq_iff_profile_eq refinedFamily false true).1 h
  have hv := congrFun hp true
  cases hv

/-- Developmental outcome-type genesis: raw outcomes need not be retained as
    ontology.  Their operational carrier is induced by downstream consequence,
    and new consequence can refine that carrier. -/
theorem consequence_profiles_generate_and_refine_outcome_carrier :
    induceOutcome oldFamily false = induceOutcome oldFamily true ∧
    induceOutcome refinedFamily false ≠ induceOutcome refinedFamily true := by
  exact ⟨old_consequence_collapses_outcomes,
    new_consequence_splits_old_outcome_class⟩

#check induced_outcome_sufficient_for_all_consequences
#check induce_outcome_is_surjective
#check induced_outcome_eq_iff_profile_eq
#check old_consequence_collapses_outcomes
#check new_consequence_splits_old_outcome_class
#check consequence_profiles_generate_and_refine_outcome_carrier

end ConsequenceProfilesInduceOutcomeCarrier
