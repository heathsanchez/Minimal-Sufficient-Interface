namespace ConsequenceProfilesInduceContextCarrier

/-- A raw family of observation contexts acting on an operational outcome carrier. -/
structure ContextFamily (ι Ω : Type) where
  observe : ι → Ω → Bool

/-- The operational profile of one raw context over all currently admitted outcomes. -/
def ContextProfile {ι Ω : Type} (F : ContextFamily ι Ω) (i : ι) : Ω → Bool :=
  fun o => F.observe i o

/-- Profiles actually realized by raw contexts. -/
def ContextProfileImage {ι Ω : Type} (F : ContextFamily ι Ω) : (Ω → Bool) → Prop :=
  fun p => ∃ i : ι, ContextProfile F i = p

/-- The retained context carrier is generated entirely from realized consequence
    profiles.  It contains no field for a raw context. -/
def InducedContextCarrier {ι Ω : Type} (F : ContextFamily ι Ω) :=
  {p : Ω → Bool // ContextProfileImage F p}

/-- Canonical projection from a raw context into its consequence-generated role. -/
def induceContext {ι Ω : Type} (F : ContextFamily ι Ω) (i : ι) :
    InducedContextCarrier F :=
  ⟨ContextProfile F i, ⟨i, rfl⟩⟩

/-- The action of every retained context on every current outcome is recovered
    directly from its induced profile. -/
def inducedAction {ι Ω : Type} {F : ContextFamily ι Ω}
    (q : InducedContextCarrier F) (o : Ω) : Bool :=
  q.1 o

theorem induced_context_sufficient_for_all_current_outcomes {ι Ω : Type}
    (F : ContextFamily ι Ω) (i : ι) (o : Ω) :
    inducedAction (induceContext F i) o = F.observe i o := by
  rfl

/-- No realized operational context is lost when raw context syntax is removed. -/
theorem induce_context_is_surjective {ι Ω : Type} (F : ContextFamily ι Ω) :
    ∀ q : InducedContextCarrier F, ∃ i : ι, induceContext F i = q := by
  intro q
  rcases q.2 with ⟨i, hi⟩
  refine ⟨i, ?_⟩
  apply Subtype.ext
  exact hi

/-- Operational context identity is exactly equality of action on all currently
    admitted outcomes. -/
theorem induced_context_eq_iff_profile_eq {ι Ω : Type}
    (F : ContextFamily ι Ω) (i j : ι) :
    induceContext F i = induceContext F j ↔
      ContextProfile F i = ContextProfile F j := by
  constructor
  · intro h
    exact congrArg Subtype.val h
  · intro h
    apply Subtype.ext
    exact h

/-- Before the outcome ontology expands, the two raw contexts are indistinguishable. -/
def oldFamily : ContextFamily Bool Unit where
  observe := fun _ _ => false

/-- After a new outcome becomes available, one context responds differently to it. -/
def refinedFamily : ContextFamily Bool Bool where
  observe := fun i o => if i then o else false

/-- With only the old one-point outcome carrier, false and true contexts collapse. -/
theorem old_outcome_carrier_collapses_contexts :
    induceContext oldFamily false = induceContext oldFamily true := by
  apply (induced_context_eq_iff_profile_eq oldFamily false true).2
  funext o
  cases o
  rfl

/-- Expansion of the operational outcome carrier exposes a distinction between
    contexts that was impossible to express before. -/
theorem new_outcome_splits_old_context_class :
    induceContext refinedFamily false ≠ induceContext refinedFamily true := by
  intro h
  have hp : ContextProfile refinedFamily false = ContextProfile refinedFamily true :=
    (induced_context_eq_iff_profile_eq refinedFamily false true).1 h
  have hv := congrFun hp true
  cases hv

/-- Reciprocal ontology refinement: consequence-generated outcomes can make new
    context distinctions operationally necessary, without retaining raw context syntax. -/
theorem outcome_growth_generates_context_refinement :
    induceContext oldFamily false = induceContext oldFamily true ∧
    induceContext refinedFamily false ≠ induceContext refinedFamily true := by
  exact ⟨old_outcome_carrier_collapses_contexts,
    new_outcome_splits_old_context_class⟩

#check induced_context_sufficient_for_all_current_outcomes
#check induce_context_is_surjective
#check induced_context_eq_iff_profile_eq
#check old_outcome_carrier_collapses_contexts
#check new_outcome_splits_old_context_class
#check outcome_growth_generates_context_refinement

end ConsequenceProfilesInduceContextCarrier
